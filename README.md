# VerifyFlow
Intelligent Document Verification and Review Platform (React, FastAPI, MongoDB Atlas/GridFS, OCR, SHA-256 duplicate detection, human review, hash-chained audit log, Docker, Kubernetes/Minikube, Jenkins).

**Status:** Phase 0-1 scaffold. Backend has `/health` and `/ready`; frontend is a placeholder; Docker, k8s and Jenkins files are starter versions. Remaining phases are built with Antigravity following the guide PDF.

## Run backend (Windows PowerShell)
```powershell
cd "D:\INCHARA\Devops project\Verifyflow\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then edit with your values
uvicorn app.main:app --reload
pytest -q
```
## Run frontend
```powershell
cd "D:\INCHARA\Devops project\Verifyflow\frontend"
npm install
npm run dev
```
## Docker
```powershell
cd "D:\INCHARA\Devops project\Verifyflow"
docker compose up --build
```

> Project location: `D:\INCHARA\Devops project\Verifyflow`. The path contains a space, so always wrap it in double quotes in PowerShell.
