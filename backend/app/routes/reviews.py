from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Literal

from app.core.security import get_current_user, require_roles
from app.database.mongo import get_db
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])


class DecisionRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED", "CORRECTION_REQUESTED"]
    remarks: str = ""


def serialize_doc(doc: dict) -> dict:
    d = doc.copy()
    d["id"] = str(d["_id"])
    if "owner_id" in d and isinstance(d["owner_id"], ObjectId):
        d["owner_id"] = str(d["owner_id"])
    if "_id" in d:
        del d["_id"]
    return d


@router.get("/queue")
@router.get("")
def get_review_queue(
    current_user: dict = Depends(require_roles("reviewer", "admin", "auditor")),
):
    db = get_db()
    docs = list(
        db.documents.find({"status": "UNDER_REVIEW"}).sort(
            [("risk_score", -1), ("created_at", 1)]
        )
    )

    results = []
    for d in docs:
        sd = serialize_doc(d)
        rev = db.document_revisions.find_one({
            "document_id": d["_id"],
            "revision_number": d.get("current_revision", 1),
        })
        if rev:
            sd["filename"] = rev.get("filename")
            sd["sha256"] = rev.get("sha256")
            sd["submitted_metadata"] = rev.get("submitted_metadata", {})
        results.append(sd)

    return results


@router.get("/{document_id}")
def get_review_workspace(
    document_id: str,
    current_user: dict = Depends(require_roles("reviewer", "admin", "auditor")),
):
    db = get_db()
    try:
        doc = db.documents.find_one({"_id": ObjectId(document_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    sd = serialize_doc(doc)
    cur_rev_num = doc.get("current_revision", 1)

    rev = db.document_revisions.find_one({
        "document_id": doc["_id"],
        "revision_number": cur_rev_num,
    })
    if rev:
        sd["revision"] = {
            "revision_number": rev["revision_number"],
            "filename": rev["filename"],
            "sha256": rev["sha256"],
            "file_size": rev["file_size"],
            "submitted_metadata": rev.get("submitted_metadata", {}),
            "uploaded_at": rev.get("uploaded_at"),
        }

    ext = db.extractions.find_one({"document_id": doc["_id"], "revision_number": cur_rev_num})
    if ext:
        sd["extractions"] = {
            "extracted_text": ext.get("extracted_text", ""),
            "fields": ext.get("fields", {}),
            "confidence": ext.get("confidence", 0),
        }

    ver = db.verification_results.find_one({"document_id": doc["_id"], "revision_number": cur_rev_num})
    if ver:
        sd["verification_results"] = {
            "rule_results": ver.get("rule_results", []),
            "risk_score": ver.get("risk_score", 0),
            "risk_level": ver.get("risk_level", "low"),
        }

    # Previous review history
    reviews = list(db.reviews.find({"document_id": doc["_id"]}).sort("reviewed_at", -1))
    for r in reviews:
        r["id"] = str(r["_id"])
        del r["_id"]
        r["reviewer_id"] = str(r["reviewer_id"])
        r["document_id"] = str(r["document_id"])
    sd["review_history"] = reviews

    return sd


@router.post("/{document_id}/decision")
def submit_decision(
    document_id: str,
    req: DecisionRequest,
    current_user: dict = Depends(require_roles("reviewer", "admin")),
):
    db = get_db()
    try:
        doc = db.documents.find_one({"_id": ObjectId(document_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Prevent reviewer from approving their own document
    if str(doc.get("owner_id")) == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviewers cannot make verification decisions on their own documents",
        )

    # Remarks are mandatory for REJECTED and CORRECTION_REQUESTED
    if req.decision in ("REJECTED", "CORRECTION_REQUESTED") and not req.remarks.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Remarks are required when submitting decision: {req.decision}",
        )

    cur_rev = doc.get("current_revision", 1)

    review_doc = {
        "document_id": doc["_id"],
        "revision_number": cur_rev,
        "reviewer_id": ObjectId(current_user["id"]),
        "reviewer_name": current_user.get("name", "Reviewer"),
        "decision": req.decision,
        "remarks": req.remarks.strip(),
        "reviewed_at": datetime.now(timezone.utc),
    }
    db.reviews.insert_one(review_doc)

    # Update document status
    db.documents.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "status": req.decision,
                "updated_at": datetime.now(timezone.utc),
                "latest_reviewer_remarks": req.remarks.strip(),
            }
        },
    )

    action_map = {
        "APPROVED": "DOCUMENT_APPROVED",
        "REJECTED": "DOCUMENT_REJECTED",
        "CORRECTION_REQUESTED": "CORRECTION_REQUESTED",
    }

    record_audit_event(
        db=db,
        actor_id=current_user["id"],
        action=action_map[req.decision],
        entity_type="document",
        entity_id=doc["_id"],
        details={
            "decision": req.decision,
            "remarks": req.remarks.strip(),
            "revision_number": cur_rev,
        },
    )

    # Create notification for document owner
    db.notifications.insert_one({
        "user_id": doc["owner_id"],
        "title": f"Document {req.decision.replace('_', ' ').title()}",
        "message": f"Your document '{doc.get('document_type', 'document')}' was {req.decision.lower().replace('_', ' ')}. Remarks: {req.remarks.strip() or 'None'}",
        "type": req.decision,
        "entity_id": doc["_id"],
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
    })

    return {
        "document_id": str(doc["_id"]),
        "status": req.decision,
        "decision": req.decision,
        "remarks": req.remarks.strip(),
    }

