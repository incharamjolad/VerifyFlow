# VerifyFlow
Intelligent Document Verification and Review Platform (React, FastAPI, MongoDB Atlas/GridFS, OCR, SHA-256 duplicate detection, human review, hash-chained audit log, Docker, Kubernetes/Minikube, Jenkins).

## Demo Credentials (Seeded)
All demo accounts use password: `VerifyDemo#2026!x`

| Role | Email | Capabilities |
| :--- | :--- | :--- |
| **Admin** | `admin@verifyflow.com` | User role management, system analytics, review & audit access |
| **Reviewer** | `reviewer@verifyflow.com` | Review queue, split-screen PDF preview, approve/reject/corrections |
| **Auditor** | `auditor@verifyflow.com` | Read-only audit ledger, cryptographic hash-chain verification |
| **Applicant** | `applicant@verifyflow.com` | PDF upload, document history, correction revision resubmission |

---

## Run Locally (Windows PowerShell)

### 1. Seed Database (Optional / First Run)
```powershell
cd "d:\INCHARA\Devops project\Verifyflow\VerifyFlow-repo (1)\Verifyflow\backend"
.\.venv\Scripts\Activate.ps1
python seed.py
```

### 2. Run Backend (Port 8000)
```powershell
cd "d:\INCHARA\Devops project\Verifyflow\VerifyFlow-repo (1)\Verifyflow\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Run Frontend (Port 5173 with /api proxy to 8000)
```powershell
cd "d:\INCHARA\Devops project\Verifyflow\VerifyFlow-repo (1)\Verifyflow\frontend"
npm run dev
```

### 4. Run Pytest Suite
```powershell
cd "d:\INCHARA\Devops project\Verifyflow\VerifyFlow-repo (1)\Verifyflow\backend"
.\.venv\Scripts\Activate.ps1
pytest tests -v
```
