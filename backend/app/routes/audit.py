from fastapi import APIRouter, Depends, Query
from app.core.security import require_roles
from app.database.mongo import get_db
from app.services.audit_service import verify_chain

router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("")
@router.get("/")
def get_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    sort_order: int = Query(-1, description="-1 for newest first, 1 for oldest first"),
    current_user: dict = Depends(require_roles("auditor", "admin", "reviewer")),
):
    db = get_db()
    logs = list(db.audit_logs.find().sort("sequence", sort_order).limit(limit))
    for log in logs:
        log["id"] = str(log["_id"])
        del log["_id"]
        if "created_at" in log:
            log["created_at"] = log["created_at"].isoformat()
    return logs


@router.get("/verify")
def run_audit_verification(
    current_user: dict = Depends(require_roles("auditor", "admin", "reviewer")),
):
    db = get_db()
    return verify_chain(db)

