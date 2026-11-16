import sys
from pathlib import Path
from datetime import datetime, timezone

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database.mongo import get_db, ping
from app.core.security import hash_password


def seed_demo_users():
    if not ping():
        print("Error: Could not connect to MongoDB Atlas. Check your connection string.")
        sys.exit(1)

    db = get_db()
    users_to_seed = [
        {
            "name": "Platform Admin",
            "email": "admin@verifyflow.com",
            "password": "VerifyDemo#2026!x",
            "role": "admin",
        },
        {
            "name": "Lead Reviewer",
            "email": "reviewer@verifyflow.com",
            "password": "VerifyDemo#2026!x",
            "role": "reviewer",
        },
        {
            "name": "Compliance Auditor",
            "email": "auditor@verifyflow.com",
            "password": "VerifyDemo#2026!x",
            "role": "auditor",
        },
        {
            "name": "Sample Applicant",
            "email": "applicant@verifyflow.com",
            "password": "VerifyDemo#2026!x",
            "role": "applicant",
        },
    ]

    print("Seeding demo users...")
    for u in users_to_seed:
        existing = db.users.find_one({"email": u["email"]})
        hashed = hash_password(u["password"])
        now = datetime.now(timezone.utc)
        if existing:
            db.users.update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "name": u["name"],
                        "password_hash": hashed,
                        "role": u["role"],
                        "is_active": True,
                        "updated_at": now,
                    }
                },
            )
            print(f"Updated existing user: {u['email']} -> role: {u['role']}")
        else:
            doc = {
                "name": u["name"],
                "email": u["email"],
                "password_hash": hashed,
                "role": u["role"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            res = db.users.insert_one(doc)
            print(f"Created user: {u['email']} (ID: {res.inserted_id}) -> role: {u['role']}")

    print("\nSeed completed successfully!")
    print("Demo Passwords: VerifyDemo#2026!x")


if __name__ == "__main__":
    seed_demo_users()

