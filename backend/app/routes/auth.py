from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.database.mongo import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest):
    db = get_db()
    clean_email = req.email.strip().lower()

    if db.users.find_one({"email": clean_email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    user_doc = {
        "name": req.name.strip(),
        "email": clean_email,
        "password_hash": hash_password(req.password),
        "role": "applicant",  # Always applicant
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    res = db.users.insert_one(user_doc)
    user_id = str(res.inserted_id)

    record_audit_event(
        db=db,
        actor_id=user_id,
        action="USER_REGISTERED",
        entity_type="user",
        entity_id=user_id,
        details={"name": req.name, "email": clean_email, "role": "applicant"},
    )

    return {
        "id": user_id,
        "name": user_doc["name"],
        "email": user_doc["email"],
        "role": "applicant",
    }


@router.post("/login")
def login(req: LoginRequest):
    db = get_db()
    clean_email = (req.email or req.username or "").strip().lower()
    if not clean_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username is required",
        )
    user = db.users.find_one({"email": clean_email})

    if not user or not verify_password(req.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    token = create_access_token(
        data={
            "sub": str(user["_id"]),
            "email": user["email"],
            "role": user.get("role", "applicant"),
            "name": user.get("name", ""),
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user["name"],
            "role": user.get("role", "applicant"),
        },
    }


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "name": current_user.get("name", ""),
        "email": current_user.get("email", ""),
        "role": current_user.get("role", "applicant"),
        "is_active": current_user.get("is_active", True),
    }
