import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO
from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.security import get_current_user
from app.database.mongo import get_db, get_gridfs
from app.services.audit_service import record_audit_event
from app.services.verification_service import process_document_sync

router = APIRouter(prefix="/api/documents", tags=["Documents"])


def serialize_doc(doc: dict) -> dict:
    d = doc.copy()
    d["id"] = str(d["_id"])
    if "owner_id" in d and isinstance(d["owner_id"], ObjectId):
        d["owner_id"] = str(d["owner_id"])
    if "_id" in d:
        del d["_id"]
    return d


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("academic_certificate"),
    candidate_name: str = Form(""),
    registration_number: str = Form(""),
    issue_date: str = Form(""),
    current_user: dict = Depends(get_current_user),
):
    # Only applicants (or users uploading as applicant) upload documents
    file_bytes = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024

    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.max_upload_mb} MB",
        )

    # Validate PDF magic bytes: '%PDF' -> b'%PDF'
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid file format. Only valid PDF files are accepted.",
        )

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    db = get_db()
    grid_fs = get_gridfs()

    # Store file in GridFS
    file_id = grid_fs.put(
        file_bytes,
        filename=file.filename or "uploaded_document.pdf",
        content_type="application/pdf",
    )

    submitted_metadata = {
        "candidate_name": candidate_name.strip(),
        "registration_number": registration_number.strip(),
        "issue_date": issue_date.strip(),
    }

    # Create document record
    doc_data = {
        "owner_id": ObjectId(current_user["id"]),
        "owner_name": current_user.get("name", ""),
        "owner_email": current_user.get("email", ""),
        "document_type": document_type,
        "status": "SUBMITTED",
        "current_revision": 1,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    doc_res = db.documents.insert_one(doc_data)
    document_id = doc_res.inserted_id

    # Create revision 1
    rev_data = {
        "document_id": document_id,
        "revision_number": 1,
        "filename": file.filename or "document.pdf",
        "file_id": file_id,
        "sha256": sha256_hash,
        "mime_type": "application/pdf",
        "file_size": len(file_bytes),
        "submitted_metadata": submitted_metadata,
        "previous_revision_id": None,
        "uploaded_at": datetime.now(timezone.utc),
    }
    db.document_revisions.insert_one(rev_data)

    # Audit event
    record_audit_event(
        db=db,
        actor_id=current_user["id"],
        action="DOCUMENT_SUBMITTED",
        entity_type="document",
        entity_id=document_id,
        details={
            "filename": file.filename,
            "sha256": sha256_hash,
            "revision_number": 1,
            "document_type": document_type,
        },
    )

    # Trigger processing synchronously for instant demo results
    process_document_sync(db, grid_fs, document_id, 1)

    # Return fresh state
    updated_doc = db.documents.find_one({"_id": document_id})
    return serialize_doc(updated_doc)


@router.get("")
@router.get("/")
def list_documents(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user_role = current_user.get("role", "applicant")

    query = {}
    if user_role == "applicant":
        query = {"owner_id": ObjectId(current_user["id"])}

    docs = list(db.documents.find(query).sort("created_at", -1))
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
            sd["file_size"] = rev.get("file_size")
            sd["submitted_metadata"] = rev.get("submitted_metadata", {})
        results.append(sd)
    return results


@router.get("/{document_id}")
def get_document_details(document_id: str, current_user: dict = Depends(get_current_user)):
    db = get_db()
    try:
        doc = db.documents.find_one({"_id": ObjectId(document_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Security check: applicant can only view their own document
    if current_user.get("role") == "applicant" and str(doc["owner_id"]) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied to this document")

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

    # Fetch extraction & verification results
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

    # Revisions history list
    all_revs = list(db.document_revisions.find({"document_id": doc["_id"]}).sort("revision_number", 1))
    sd["all_revisions"] = [
        {
            "revision_number": r["revision_number"],
            "filename": r["filename"],
            "sha256": r["sha256"],
            "uploaded_at": r["uploaded_at"],
        }
        for r in all_revs
    ]

    return sd


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    revision: int | None = None,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    grid_fs = get_gridfs()

    try:
        doc = db.documents.find_one({"_id": ObjectId(document_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Security check: applicant can only download their own document
    if current_user.get("role") == "applicant" and str(doc["owner_id"]) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied to this document file")

    target_rev = revision if revision is not None else doc.get("current_revision", 1)
    rev = db.document_revisions.find_one({
        "document_id": doc["_id"],
        "revision_number": target_rev,
    })
    if not rev:
        raise HTTPException(status_code=404, detail="Revision file not found")

    try:
        grid_file = grid_fs.get(rev["file_id"])
    except Exception:
        raise HTTPException(status_code=404, detail="File chunk not found in storage")

    return StreamingResponse(
        BytesIO(grid_file.read()),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{rev.get("filename", "document.pdf")}"',
            "X-SHA256": rev.get("sha256", ""),
        },
    )


@router.post("/{document_id}/revisions", status_code=status.HTTP_201_CREATED)
async def upload_revision(
    document_id: str,
    file: UploadFile = File(...),
    candidate_name: str = Form(""),
    registration_number: str = Form(""),
    issue_date: str = Form(""),
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    grid_fs = get_gridfs()

    try:
        doc = db.documents.find_one({"_id": ObjectId(document_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Only document owner or authorized admin can submit revision
    if current_user.get("role") == "applicant" and str(doc["owner_id"]) != current_user["id"]:
        raise HTTPException(status_code=403, detail="Cannot upload revision for another user's document")

    file_bytes = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024

    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.max_upload_mb} MB",
        )

    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid file format. Only valid PDF files are accepted.",
        )

    sha256_hash = hashlib.sha256(file_bytes).hexdigest()
    file_id = grid_fs.put(
        file_bytes,
        filename=file.filename or "revised_document.pdf",
        content_type="application/pdf",
    )

    old_rev_num = doc.get("current_revision", 1)
    new_rev_num = old_rev_num + 1

    old_rev = db.document_revisions.find_one({
        "document_id": doc["_id"],
        "revision_number": old_rev_num,
    })

    submitted_metadata = {
        "candidate_name": candidate_name.strip(),
        "registration_number": registration_number.strip(),
        "issue_date": issue_date.strip(),
    }

    new_rev_doc = {
        "document_id": doc["_id"],
        "revision_number": new_rev_num,
        "filename": file.filename or "revised_document.pdf",
        "file_id": file_id,
        "sha256": sha256_hash,
        "mime_type": "application/pdf",
        "file_size": len(file_bytes),
        "submitted_metadata": submitted_metadata,
        "previous_revision_id": old_rev["_id"] if old_rev else None,
        "uploaded_at": datetime.now(timezone.utc),
    }
    db.document_revisions.insert_one(new_rev_doc)

    db.documents.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "current_revision": new_rev_num,
                "status": "SUBMITTED",
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    record_audit_event(
        db=db,
        actor_id=current_user["id"],
        action="REVISION_SUBMITTED",
        entity_type="document",
        entity_id=doc["_id"],
        details={
            "revision_number": new_rev_num,
            "filename": file.filename,
            "sha256": sha256_hash,
        },
    )

    process_document_sync(db, grid_fs, doc["_id"], new_rev_num)

    updated_doc = db.documents.find_one({"_id": doc["_id"]})
    return serialize_doc(updated_doc)


@router.post("/{document_id}/reprocess")
def reprocess_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = get_db()
    grid_fs = get_gridfs()

    try:
        doc = db.documents.find_one({"_id": ObjectId(document_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    cur_rev = doc.get("current_revision", 1)
    process_document_sync(db, grid_fs, doc["_id"], cur_rev)

    updated_doc = db.documents.find_one({"_id": doc["_id"]})
    return serialize_doc(updated_doc)

