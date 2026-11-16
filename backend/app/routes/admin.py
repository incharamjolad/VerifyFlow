from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Literal

from app.core.security import require_roles
from app.database.mongo import get_db
from app.services.audit_service import record_audit_event

router = APIRouter(tags=["Admin & Analytics"])


class UpdateRoleRequest(BaseModel):
    role: Literal["applicant", "reviewer", "admin", "auditor"]


@router.get("/api/admin/users")
def list_users(current_user: dict = Depends(require_roles("admin"))):
    db = get_db()
    users = list(db.users.find().sort("created_at", -1))
    results = []
    for u in users:
        results.append({
            "id": str(u["_id"]),
            "name": u.get("name", ""),
            "email": u.get("email", ""),
            "role": u.get("role", "applicant"),
            "is_active": u.get("is_active", True),
            "created_at": u.get("created_at").isoformat() if u.get("created_at") else None,
        })
    return results


@router.patch("/api/admin/users/{user_id}/role")
def update_user_role(
    user_id: str,
    req: UpdateRoleRequest,
    current_user: dict = Depends(require_roles("admin")),
):
    db = get_db()
    try:
        target = db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = target.get("role", "applicant")
    db.users.update_one(
        {"_id": target["_id"]},
        {"$set": {"role": req.role, "updated_at": datetime.now(timezone.utc)}},
    )

    record_audit_event(
        db=db,
        actor_id=current_user["id"],
        action="ROLE_CHANGED",
        entity_type="user",
        entity_id=target["_id"],
        details={"old_role": old_role, "new_role": req.role},
    )

    return {
        "id": str(target["_id"]),
        "email": target.get("email"),
        "role": req.role,
        "message": f"Role updated from {old_role} to {req.role}",
    }


@router.get("/api/analytics/overview")
def get_analytics_overview(
    current_user: dict = Depends(require_roles("admin", "reviewer", "auditor")),
):
    db = get_db()
    total_docs = db.documents.count_documents({})
    under_review = db.documents.count_documents({"status": "UNDER_REVIEW"})
    approved = db.documents.count_documents({"status": "APPROVED"})
    rejected = db.documents.count_documents({"status": "REJECTED"})
    correction_requested = db.documents.count_documents({"status": "CORRECTION_REQUESTED"})
    processing_failed = db.documents.count_documents({"status": "PROCESSING_FAILED"})
    total_users = db.users.count_documents({})
    total_audits = db.audit_logs.count_documents({})

    return {
        "total_documents": total_docs,
        "under_review": under_review,
        "approved": approved,
        "rejected": rejected,
        "correction_requested": correction_requested,
        "processing_failed": processing_failed,
        "total_users": total_users,
        "total_audit_events": total_audits,
    }

