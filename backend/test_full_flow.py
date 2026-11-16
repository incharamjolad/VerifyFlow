import io
import time
import sys
from pathlib import Path
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app

client = TestClient(app)

SAMPLE_PDF_1 = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
    b"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 85 >>\nstream\n"
    b"BT\n/F1 12 Tf\n100 700 Td\n(Name: Test User Reg: REG-9999 Date: 2024-06-01) Tj\nET\n"
    b"endstream\nendobj\n"
    b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
    b"0000000115 00000 n \n0000000266 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\n"
    b"startxref\n403\n%%EOF\n"
)

SAMPLE_PDF_REVISED = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
    b"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 95 >>\nstream\n"
    b"BT\n/F1 12 Tf\n100 700 Td\n(Name: Test User Reg: REG-9999 Date: 2024-06-01 [Revised]) Tj\nET\n"
    b"endstream\nendobj\n"
    b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
    b"0000000115 00000 n \n0000000266 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\n"
    b"startxref\n413\n%%EOF\n"
)

def run_flow():
    ts = int(time.time())
    applicant_email = f"flow_{ts}@verifyflow.com"
    pwd = "VerifyDemo#2026!x"

    # 1. Register Applicant
    reg = client.post("/api/auth/register", json={"name": "Flow User", "email": applicant_email, "password": pwd})
    print(f"1. POST /api/auth/register: {reg.status_code}")
    assert reg.status_code == 201

    login_app = client.post("/api/auth/login", json={"email": applicant_email, "password": pwd})
    print(f"   POST /api/auth/login (applicant): {login_app.status_code}")
    assert login_app.status_code == 200
    token_app = login_app.json()["access_token"]
    headers_app = {"Authorization": f"Bearer {token_app}"}

    # 2. Upload text PDF
    up1 = client.post(
        "/api/documents/upload",
        headers=headers_app,
        files={"file": ("certificate.pdf", io.BytesIO(SAMPLE_PDF_1), "application/pdf")},
        data={"document_type": "academic_certificate", "candidate_name": "Test User", "registration_number": "REG-9999", "issue_date": "2024-06-01"},
    )
    print(f"2. POST /api/documents/upload: {up1.status_code}")
    assert up1.status_code == 201
    doc_id = up1.json()["id"]

    get_doc = client.get(f"/api/documents/{doc_id}", headers=headers_app)
    print(f"   GET /api/documents/{{id}} (status={get_doc.json().get('status')}): {get_doc.status_code}")
    assert get_doc.status_code == 200
    assert get_doc.json()["status"] == "UNDER_REVIEW"

    # 3. Upload same PDF again -> duplicate flagged
    up2 = client.post(
        "/api/documents/upload",
        headers=headers_app,
        files={"file": ("certificate_dup.pdf", io.BytesIO(SAMPLE_PDF_1), "application/pdf")},
        data={"document_type": "academic_certificate"},
    )
    print(f"3. POST /api/documents/upload (duplicate): {up2.status_code}")
    assert up2.status_code == 201
    dup_id = up2.json()["id"]

    get_dup = client.get(f"/api/documents/{dup_id}", headers=headers_app)
    print(f"   GET /api/documents/{{dup_id}} (duplicate check): {get_dup.status_code}")
    assert get_dup.status_code == 200
    rule_results = get_dup.json().get("verification_results", {}).get("rule_results", [])
    dup_rule = next((r for r in rule_results if r["rule_id"] == "DUP_001"), None)
    assert dup_rule is not None and dup_rule["status"] == "WARNING"
    print(f"   DUP_001 result: {dup_rule['status']} - {dup_rule['explanation']}")

    # 4. Reviewer login & request correction
    login_rev = client.post("/api/auth/login", json={"email": "reviewer@verifyflow.com", "password": pwd})
    print(f"4. POST /api/auth/login (reviewer): {login_rev.status_code}")
    assert login_rev.status_code == 200
    token_rev = login_rev.json()["access_token"]
    headers_rev = {"Authorization": f"Bearer {token_rev}"}

    dec1 = client.post(
        f"/api/reviews/{doc_id}/decision",
        headers=headers_rev,
        json={"decision": "CORRECTION_REQUESTED", "remarks": "Please provide clearer resolution certificate with seal."},
    )
    print(f"   POST /api/reviews/{{id}}/decision (CORRECTION_REQUESTED): {dec1.status_code}")
    assert dec1.status_code == 200

    # 5. Applicant uploads revision
    rev_up = client.post(
        f"/api/documents/{doc_id}/revisions",
        headers=headers_app,
        files={"file": ("certificate_v2.pdf", io.BytesIO(SAMPLE_PDF_REVISED), "application/pdf")},
        data={"candidate_name": "Test User", "registration_number": "REG-9999", "issue_date": "2024-06-01"},
    )
    print(f"5. POST /api/documents/{{id}}/revisions: {rev_up.status_code}")
    assert rev_up.status_code == 201

    # 6. Reviewer approves
    dec2 = client.post(
        f"/api/reviews/{doc_id}/decision",
        headers=headers_rev,
        json={"decision": "APPROVED", "remarks": "Revision verified and meets criteria."},
    )
    print(f"6. POST /api/reviews/{{id}}/decision (APPROVED): {dec2.status_code}")
    assert dec2.status_code == 200

    # 7. Auditor audit verify
    login_aud = client.post("/api/auth/login", json={"email": "auditor@verifyflow.com", "password": pwd})
    print(f"7. POST /api/auth/login (auditor): {login_aud.status_code}")
    assert login_aud.status_code == 200
    token_aud = login_aud.json()["access_token"]
    headers_aud = {"Authorization": f"Bearer {token_aud}"}

    audit_verify = client.get("/api/audit/verify", headers=headers_aud)
    print(f"   GET /api/audit/verify (valid={audit_verify.json().get('valid')}): {audit_verify.status_code}")
    assert audit_verify.status_code == 200
    assert audit_verify.json()["valid"] is True

    # 8. Admin analytics overview
    login_adm = client.post("/api/auth/login", json={"email": "admin@verifyflow.com", "password": pwd})
    print(f"8. POST /api/auth/login (admin): {login_adm.status_code}")
    assert login_adm.status_code == 200
    token_adm = login_adm.json()["access_token"]
    headers_adm = {"Authorization": f"Bearer {token_adm}"}

    analytics = client.get("/api/analytics/overview", headers=headers_adm)
    print(f"   GET /api/analytics/overview: {analytics.status_code}")
    assert analytics.status_code == 200
    print(f"   Real counts: {analytics.json()}")

if __name__ == "__main__":
    run_flow()

