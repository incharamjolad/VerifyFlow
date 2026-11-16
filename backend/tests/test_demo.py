import io
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import mongo
from app.services.audit_service import compute_event_hash, sanitize_for_json

client = TestClient(app)

SAMPLE_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
    b"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 85 >>\nstream\n"
    b"BT\n/F1 12 Tf\n100 700 Td\n(Name: Alice Smith Reg: CERT-1001 Date: 2024-05-10) Tj\nET\n"
    b"endstream\nendobj\n"
    b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
    b"0000000115 00000 n \n0000000266 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\n"
    b"startxref\n403\n%%EOF\n"
)


@pytest.fixture(scope="module")
def tokens():
    # Login with seeded demo accounts
    resp_app = client.post("/api/auth/login", json={"email": "applicant@verifyflow.com", "password": "VerifyDemo#2026!x"})
    resp_rev = client.post("/api/auth/login", json={"email": "reviewer@verifyflow.com", "password": "VerifyDemo#2026!x"})
    resp_adm = client.post("/api/auth/login", json={"email": "admin@verifyflow.com", "password": "VerifyDemo#2026!x"})
    resp_aud = client.post("/api/auth/login", json={"email": "auditor@verifyflow.com", "password": "VerifyDemo#2026!x"})

    return {
        "applicant": resp_app.json()["access_token"],
        "reviewer": resp_rev.json()["access_token"],
        "admin": resp_adm.json()["access_token"],
        "auditor": resp_aud.json()["access_token"],
    }


def test_auth_register_and_login():
    email = f"new_{uuid.uuid4().hex[:8]}@verifyflow.com"
    # Registration always creates role=applicant
    reg_resp = client.post(
        "/api/auth/register",
        json={"name": "New Person", "email": email, "password": "VerifyDemo#2026!x"},
    )
    assert reg_resp.status_code == 201

    login_resp = client.post(
        "/api/auth/login",
        json={"email": email, "password": "VerifyDemo#2026!x"},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert data["user"]["role"] == "applicant"


def test_role_restrictions(tokens):
    headers_app = {"Authorization": f"Bearer {tokens['applicant']}"}
    headers_rev = {"Authorization": f"Bearer {tokens['reviewer']}"}

    # Applicant CANNOT access review queue
    r1 = client.get("/api/reviews/queue", headers=headers_app)
    assert r1.status_code == 403

    # Applicant CANNOT access admin user management
    r2 = client.get("/api/admin/users", headers=headers_app)
    assert r2.status_code == 403

    # Reviewer CAN access review queue
    r3 = client.get("/api/reviews/queue", headers=headers_rev)
    assert r3.status_code == 200


def test_applicant_a_cannot_read_applicant_b_document(tokens):
    # Register Applicant B
    b_email = f"applicant_b_{uuid.uuid4().hex[:8]}@verifyflow.com"
    reg_b = client.post("/api/auth/register", json={"name": "Applicant B", "email": b_email, "password": "VerifyDemo#2026!x"})
    assert reg_b.status_code == 201
    login_b = client.post("/api/auth/login", json={"email": b_email, "password": "VerifyDemo#2026!x"}).json()
    headers_b = {"Authorization": f"Bearer {login_b['access_token']}"}
    headers_a = {"Authorization": f"Bearer {tokens['applicant']}"}

    # Applicant B uploads a document
    upload_resp = client.post(
        "/api/documents/upload",
        headers=headers_b,
        files={"file": ("b_doc.pdf", io.BytesIO(SAMPLE_PDF), "application/pdf")},
        data={"document_type": "academic_certificate"},
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # Applicant A attempts to access Applicant B's document details -> 403
    r_detail = client.get(f"/api/documents/{doc_id}", headers=headers_a)
    assert r_detail.status_code == 403

    # Applicant A attempts to download Applicant B's file -> 403
    r_down = client.get(f"/api/documents/{doc_id}/download", headers=headers_a)
    assert r_down.status_code == 403


def test_renamed_exe_rejected_by_magic_bytes(tokens):
    headers = {"Authorization": f"Bearer {tokens['applicant']}"}
    fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00ThisIsAnExecutableNotAPDF"

    resp = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("malicious.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        data={"document_type": "identity_card"},
    )
    assert resp.status_code == 415
    assert "Invalid file format" in resp.json()["detail"]


def test_duplicate_file_gets_warning(tokens):
    headers = {"Authorization": f"Bearer {tokens['applicant']}"}

    # First upload
    r1 = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("original.pdf", io.BytesIO(SAMPLE_PDF), "application/pdf")},
        data={"document_type": "academic_certificate"},
    )
    assert r1.status_code == 201
    doc1_id = r1.json()["id"]

    # Duplicate upload
    r2 = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("duplicate.pdf", io.BytesIO(SAMPLE_PDF), "application/pdf")},
        data={"document_type": "academic_certificate"},
    )
    assert r2.status_code == 201
    doc2_id = r2.json()["id"]

    # Fetch results for doc2
    doc2_details = client.get(f"/api/documents/{doc2_id}", headers=headers).json()
    rule_results = doc2_details.get("verification_results", {}).get("rule_results", [])
    dup_rule = next((r for r in rule_results if r["rule_id"] == "DUP_001"), None)

    assert dup_rule is not None
    assert dup_rule["status"] == "WARNING"
    assert "review needed" in dup_rule["explanation"].lower()


def test_audit_chain_tamper_detection(tokens):
    headers_aud = {"Authorization": f"Bearer {tokens['auditor']}"}
    db = mongo.get_db()

    # Verify chain is initially valid
    r_verify = client.get("/api/audit/verify", headers=headers_aud)
    assert r_verify.status_code == 200
    assert r_verify.json()["valid"] is True

    # Intentionally tamper with one audit log record
    first_log = db.audit_logs.find_one()
    assert first_log is not None
    orig_hash = first_log["event_hash"]

    try:
        db.audit_logs.update_one(
            {"_id": first_log["_id"]},
            {"$set": {"event_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"}},
        )

        # Verification must now fail
        tamper_verify = client.get("/api/audit/verify", headers=headers_aud)
        assert tamper_verify.status_code == 200
        res = tamper_verify.json()
        assert res["valid"] is False
        assert res["broken_at_sequence"] == first_log["sequence"]

    finally:
        # Restore original hash
        db.audit_logs.update_one(
            {"_id": first_log["_id"]},
            {"$set": {"event_hash": orig_hash}},
        )

    # Verification must be valid again
    final_verify = client.get("/api/audit/verify", headers=headers_aud)
    assert final_verify.json()["valid"] is True

