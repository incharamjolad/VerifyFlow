# VerifyFlow — System Specification & Architecture Blueprint

## 1. System Overview & Problem Statement
**VerifyFlow** is an intelligent document verification, authenticity assessment, and digital trust management platform. It automates repetitive document inspection tasks, extracts structured fields using OCR, performs SHA-256 fingerprint duplicate detection, detects anomalies and inconsistencies against submitted metadata, maintains a tamper-evident cryptographic hash-chained audit log, and assists human reviewers in making verified decisions.

### Core Philosophy
- VerifyFlow provides evidence and risk indicators; it does **not** claim an algorithm can conclusively prove a document is genuine.
- Final decisions (`APPROVED`, `REJECTED`, `CORRECTION_REQUESTED`) are strictly made by human verification officers based on extracted evidence and anomaly findings.
- Automated processing errors transition to `PROCESSING_FAILED` and **never** directly to `REJECTED`.
- Exact file duplicate detection (`DUP_001`) and text similarity detection (`DUP_002`) are review flags, never automated accusations of fraud.
- Re-uploads are modeled as immutable, sequentially numbered **Revisions** (`document_revisions`). Previous versions and evidence records are never overwritten.

---

## 2. Target Users & Role-Permission Matrix

### User Roles
- **Applicant (`applicant`)**: Default role assigned upon registration. Uploads documents, tracks application status, submits revisions upon correction requests. Cannot review or approve documents.
- **Verification Officer / Reviewer (`reviewer`)**: Views reviewer queue, inspects split-screen document preview and extracted fields, examines per-rule findings, records review decisions (`APPROVED`, `REJECTED`, `CORRECTION_REQUESTED`) with remarks.
- **Administrator (`admin`)**: Manages users and role assignments, configures verification rules and thresholds (`rule_configuration`), monitors background processing jobs, retries failed jobs.
- **Auditor (`auditor`)**: Inspects immutable-style tamper-evident audit logs, runs hash-chain cryptographic verification, views audit timelines. Read-only access to verification records.

### Role-Permission Matrix Table
| Capability / Endpoint | Applicant | Reviewer | Auditor | Administrator |
| :--- | :---: | :---: | :---: | :---: |
| Register account (`POST /api/auth/register`) | Public | Public | Public | Public |
| Authenticate / Login (`POST /api/auth/login`) | Yes | Yes | Yes | Yes |
| View own profile (`GET /api/auth/me`) | Yes | Yes | Yes | Yes |
| Upload new document (`POST /api/documents/upload`) | Yes | No | No | No |
| View own document list / status (`GET /api/documents`) | Yes (Own) | Yes (All) | Yes (All) | Yes (All) |
| Download own document file (`GET /api/documents/{id}/download`) | Yes (Own) | Yes (All) | Yes (All) | Yes (All) |
| Submit revision (`POST /api/documents/{id}/revisions`) | Yes (Own) | No | No | No |
| View revision list & download revisions | Yes (Own) | Yes (All) | Yes (All) | Yes (All) |
| Reprocess document (`POST /api/documents/{id}/reprocess`) | Yes (Own) | Yes | No | Yes |
| View Reviewer Queue (`GET /api/reviews`) | No | Yes | Yes (Read) | Yes |
| Inspect Review Workspace (`GET /api/reviews/{id}`) | No | Yes | Yes (Read) | Yes |
| Submit Review Decision (`POST /api/reviews/{id}/decision`) | No | Yes | No | Yes |
| View Audit Logs (`GET /api/audit`) | No | No | Yes | Yes |
| Verify Audit Hash Chain (`POST /api/audit/verify`) | No | No | Yes | Yes |
| View Platform Analytics (`GET /api/analytics/*`) | No | Yes | Yes | Yes |
| Receive Notifications (`GET /api/notifications`) | Yes (Own) | Yes (Own) | Yes (Own) | Yes (Own) |
| Manage User Roles & Status (`PATCH /api/admin/users/*`) | No | No | No | Yes |
| Configure Verification Rules (`PUT /api/admin/rules/*`) | No | No | No | Yes |
| Monitor & Retry Processing Jobs (`/api/admin/jobs/*`) | No | No | No | Yes |

---

## 3. Technology Stack & Process Architecture
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React, React Router v6, Recharts, Axios.
- **Backend API**: Python 3.11+, FastAPI, Pydantic v2, PyMongo.
- **Database & Storage**: MongoDB Atlas for metadata collections; MongoDB GridFS (`fs.files`, `fs.chunks`) for multi-revision binary file storage.
- **OCR Engine**: PyMuPDF (`fitz`) for digital text extraction and PDF page rendering; Tesseract OCR via `pytesseract` for scanned images.
- **Security & Cryptography**: `argon2-cffi` for password hashing, `python-jose` for JWT access tokens, `hashlib` (SHA-256) for document fingerprints and tamper-evident audit chains.
- **Process & Container Model**:
  - **No separate worker container**: Document processing runs as an in-process background worker thread inside the FastAPI backend instance, polling the `processing_jobs` collection.
  - **Exactly Two Images**: `backend` and `frontend`.
- **Infrastructure**: Docker, Docker Compose, Kubernetes / Minikube, Jenkins CI/CD pipeline.

---

## 4. Environment Variables Specification
Backend environment variables strictly adhere to the following exact names (defined in `.env.example`):
- `MONGODB_URI`: MongoDB connection string (`mongodb+srv://...` or `mongodb://localhost:27017/`)
- `MONGODB_DB`: Database name (e.g. `verifyflow`)
- `JWT_SECRET`: Secret key used for signing JWT tokens
- `JWT_ALGORITHM`: Algorithm for JWT tokens (`HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiration duration in minutes (e.g. `60`)
- `CORS_ORIGINS`: Comma-separated list of allowed origins (e.g. `http://localhost:5173`)
- `MAX_UPLOAD_MB`: Maximum allowable file upload size in megabytes (e.g. `10`)

> **Security Rule**: Never read, print, copy, commit, or modify `backend/.env`. Use `backend/.env.example` for reference only.

---

## 5. MongoDB Database Schema, Revisions & Indexes

### Collections

#### 1. `users`
- `_id`: ObjectId
- `name`: str
- `email`: str
- `password_hash`: str (Argon2)
- `role`: str (`applicant` by default; updated only by admin to `reviewer`, `admin`, `auditor`)
- `is_active`: bool (default `True`)
- `created_at`: datetime / ISO string
- `updated_at`: datetime / ISO string

#### 2. `documents`
- `_id`: ObjectId
- `owner_id`: ObjectId (reference to `users`)
- `document_type`: str (`academic_certificate`, `identity_card`, `employment_record`, `income_proof`, etc.)
- `status`: str (`SUBMITTED`, `PROCESSING`, `PROCESSING_FAILED`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `CORRECTION_REQUESTED`)
- `current_revision`: int (starts at 1, increments on revision submission)
- `created_at`: datetime / ISO string
- `updated_at`: datetime / ISO string

#### 3. `document_revisions`
- `_id`: ObjectId
- `document_id`: ObjectId (reference to `documents`)
- `revision_number`: int (1, 2, 3...)
- `filename`: str
- `file_id`: ObjectId (reference to GridFS `fs.files`)
- `sha256`: str (SHA-256 hash of revision file)
- `mime_type`: str (`application/pdf`, `image/jpeg`, `image/png`)
- `file_size`: int (bytes)
- `submitted_metadata`: dict (e.g. `candidate_name`, `institution`, `document_number`, `issue_date`)
- `previous_revision_id`: ObjectId | None
- `uploaded_at`: datetime / ISO string

#### 4. `extractions`
- `_id`: ObjectId
- `document_id`: ObjectId (reference to `documents`)
- `revision_number`: int
- `extracted_text`: str (raw OCR / digital PDF text)
- `fields`: dict (parsed structured fields: `candidate_name`, `institution`, `issue_date`, `document_number`, etc.)
- `confidence`: float (0.0 to 1.0)
- `created_at`: datetime / ISO string

#### 5. `verification_results`
- `_id`: ObjectId
- `document_id`: ObjectId (reference to `documents`)
- `revision_number`: int
- `rule_results`: list[dict]
  - `rule_id`: str (e.g. `DUP_001`, `DUP_002`, `DATE_001`, `NAME_001`, `FIELD_001`, `FORMAT_001`, `OCR_001`)
  - `status`: str (`PASS`, `WARNING`, `FAIL`)
  - `severity`: str (`low`, `medium`, `high`)
  - `explanation`: str (neutral, non-accusatory explanation)
  - `evidence`: str (matched value, diff summary, or duplicate reference)
- `risk_score`: int (0 to 100; **strictly a secondary queue-sorting and prioritization value**)
- `risk_level`: str (`low`, `medium`, `high`)
- `rule_version`: str
- `evaluated_at`: datetime / ISO string

#### 6. `reviews`
- `_id`: ObjectId
- `document_id`: ObjectId (reference to `documents`)
- `revision_number`: int
- `reviewer_id`: ObjectId (reference to `users`)
- `decision`: str (`APPROVED`, `REJECTED`, `CORRECTION_REQUESTED`)
- `remarks`: str (mandatory rationale)
- `reviewed_at`: datetime / ISO string

#### 7. `audit_logs`
- `_id`: ObjectId
- `sequence`: int (sequential integer from atomic counter, starting at 1)
- `actor_id`: ObjectId | str (reference to `users` or `"system"`)
- `action`: str (`DOCUMENT_SUBMITTED`, `PROCESSING_STARTED`, `PROCESSING_FAILED`, `OCR_EXTRACTED`, `VERIFICATION_EVALUATED`, `DOCUMENT_APPROVED`, `DOCUMENT_REJECTED`, `CORRECTION_REQUESTED`, `REVISION_SUBMITTED`, `ROLE_CHANGED`, `RULE_UPDATED`, `USER_STATUS_CHANGED`, `JOB_RETRIED`)
- `entity_type`: str (`document`, `user`, `rule`, `job`, `system`)
- `entity_id`: str
- `details`: dict (strictly JSON-safe key-values before hashing)
- `previous_hash`: str (SHA-256 hex string of entry with `sequence - 1`; `"0"*64` for genesis `sequence=1`)
- `event_hash`: str (SHA-256 of canonical JSON representation)
- `timestamp`: str (fixed ISO-8601 UTC string with millisecond precision, e.g. `2026-11-16T08:15:30.123Z`)

#### 8. `counters`
- `_id`: str (e.g. `"audit_sequence"`)
- `seq`: int (atomically incremented via `$inc`)

#### 9. `processing_jobs`
- `_id`: ObjectId
- `document_id`: ObjectId (reference to `documents`)
- `revision_number`: int
- `job_type`: str (`OCR_AND_VERIFICATION`)
- `status`: str (`PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`)
- `attempts`: int
- `max_attempts`: int (default 3)
- `error`: str | None
- `created_at`: datetime / ISO string
- `updated_at`: datetime / ISO string

#### 10. `verification_rules`
- `_id`: ObjectId
- `rule_id`: str (`DUP_001`, `DUP_002`, `DATE_001`, `NAME_001`, `FIELD_001`, `FORMAT_001`, `OCR_001`)
- `rule_name`: str
- `category`: str (`duplicate`, `date_consistency`, `name_match`, `field_presence`, `ocr_quality`, `format`)
- `severity`: str (`low`, `medium`, `high`)
- `enabled`: bool
- `rule_configuration`: dict (e.g. `{"similarity_threshold": 0.85}`, `{"min_ocr_confidence": 0.50}`, `{"default_field_severity": "medium"}`)
- `version`: str
- `updated_at`: datetime / ISO string

#### 11. `notifications`
- `_id`: ObjectId
- `user_id`: ObjectId (reference to `users`)
- `title`: str
- `message`: str
- `type`: str (`CORRECTION_REQUESTED`, `DECISION_MADE`, `PROCESSING_FAILED`, `SECURITY_ALERT`, `SYSTEM_NOTICE`)
- `entity_id`: ObjectId | str | None (e.g. `document_id`)
- `is_read`: bool (default `False`)
- `created_at`: datetime / ISO string

---

### Explicit Index List
| Collection | Fields | Options | Purpose |
| :--- | :--- | :--- | :--- |
| `users` | `{"email": 1}` | `unique=True` | Unique login and registration lookup |
| `documents` | `{"owner_id": 1}` | - | Filter user documents |
| `documents` | `{"status": 1}` | - | Review queue and status filtering |
| `document_revisions` | `{"document_id": 1, "revision_number": 1}` | `unique=True` | Fast revision retrieval and uniqueness |
| `document_revisions` | `{"sha256": 1}` | - | SHA-256 exact duplicate search (`DUP_001`) |
| `extractions` | `{"document_id": 1, "revision_number": 1}` | - | Revision OCR extractions lookup |
| `verification_results` | `{"document_id": 1, "revision_number": 1}` | - | Verification findings lookup |
| `reviews` | `{"document_id": 1, "revision_number": 1}` | - | Decision history per revision |
| `reviews` | `{"reviewer_id": 1}` | - | Reviewer workload analytics |
| `audit_logs` | `{"sequence": 1}` | `unique=True` | Deterministic chain ordering & verification |
| `audit_logs` | `{"entity_id": 1}` | - | Entity-specific audit history lookup |
| `audit_logs` | `{"timestamp": 1}` | - | Timeline filtering |
| `counters` | `{"_id": 1}` | (Default) | Atomic sequence incrementing |
| `processing_jobs` | `{"status": 1, "created_at": 1}` | - | Worker queue polling |
| `processing_jobs` | `{"document_id": 1, "revision_number": 1}` | - | Job status checking |
| `verification_rules` | `{"rule_id": 1}` | `unique=True` | Unique rule identifier |
| `notifications` | `{"user_id": 1, "is_read": 1}` | - | Unread notifications lookup |

---

## 6. Document Lifecycle & Verification State Machine

```
              ┌──────────────────────────┐
              │        SUBMITTED         │
              └─────────────┬────────────┘
                            │ (In-process worker picks up job)
                            ▼
              ┌──────────────────────────┐
              │        PROCESSING        │◄─────────────────────────────┐
              └──────┬────────────┬──────┘                              │
                     │            │                                     │
   (Processing error)│            │ (OCR & Rules complete)              │
                     ▼            ▼                                     │
      ┌───────────────────┐  ┌───────────────────┐                      │
      │ PROCESSING_FAILED │  │   UNDER_REVIEW    │                      │
      └─────────┬─────────┘  └──────┬──────┬─────┘                      │
                │                   │      │                            │
   (Reprocess)  │                   │      │                            │
                └───────────────────┤      │                            │
                                    │      │                            │
         ┌──────────────────────────┴┐     │                            │
         ▼                           ▼     ▼                            │
    ┌──────────┐               ┌──────────┐ ┌──────────────────────┐    │
    │ APPROVED │               │ REJECTED │ │ CORRECTION_REQUESTED │    │
    └──────────┘               └──────────┘ └──────────┬───────────┘    │
                                                       │                │
                                     (Applicant submits│                │
                                       revised doc)    ▼                │
                                            ┌──────────────────────┐    │
                                            │ SUBMITTED (Rev N+1)  ├────┘
                                            └──────────────────────┘
```

### Transition Invariants
1. `SUBMITTED` -> `PROCESSING`: Occurs when the in-backend worker thread begins OCR and rule evaluation.
2. `PROCESSING` -> `PROCESSING_FAILED`: Occurs if an unhandled technical exception, corrupted file, or extraction timeout occurs.
3. `PROCESSING_FAILED` -> `PROCESSING`: Occurs when `POST /api/documents/{id}/reprocess` is invoked.
4. **CRITICAL INVARIANT**: `PROCESSING_FAILED` must **NEVER** transition to `REJECTED`. Processing failures are infrastructure/file errors, not reviewer rejections. Only an authorized reviewer can issue a `REJECTED` decision from `UNDER_REVIEW`.
5. `PROCESSING` -> `UNDER_REVIEW`: Occurs when OCR extraction and all verification rules have executed.
6. `UNDER_REVIEW` -> `APPROVED` | `REJECTED` | `CORRECTION_REQUESTED`: Occurs upon submission of a formal reviewer decision.
7. `CORRECTION_REQUESTED` -> `SUBMITTED`: When the applicant uploads a revised document via `POST /api/documents/{id}/revisions`, a new revision (`revision_number = N + 1`) is created with status `SUBMITTED`, preserving all previous revision records.

---

## 7. Verification Rules & Anomaly Detection Specifications

### File Failure Handling vs. Verification Rules
- **Upload Failures**: Files exceeding `MAX_UPLOAD_MB` (HTTP 413) or with prohibited MIME types (HTTP 415) are rejected immediately at the API boundary.
- **Corrupted / Unreadable Files**: If an uploaded file cannot be parsed or rendered by PyMuPDF/PIL in the worker, the job fails and the document status transitions to `PROCESSING_FAILED`. This is **not** a verification `FAIL`.
- **`FORMAT_001`**: Reserved solely for non-fatal layout/structure verification findings (e.g., orientation mismatch, non-standard layout) that do not prevent text extraction.

### Rules Matrix
| Rule ID | Rule Name | Category | Logic & Policy | Evaluated Status |
| :--- | :--- | :--- | :--- | :--- |
| `DUP_001` | Exact File Duplicate | Duplicate | Compares revision SHA-256 against all other document revisions in database. | **WARNING** (never FAIL). Neutral wording: "Identical file found in existing submission (ID: ...); review needed." Flags for human inspection. |
| `DUP_002` | Text Similarity Match | Duplicate | Computes token-level / n-gram Jaccard or Cosine similarity on normalized OCR text against existing corpus. Threshold defined in `rule_configuration.similarity_threshold` (default 0.85). | **WARNING** if similarity >= threshold; **PASS** otherwise. |
| `DATE_001` | Date Consistency | Date | Compares applicant-submitted issue date against extracted dates. Flags impossible dates (future dates) or mismatches. | **FAIL** for future dates; **WARNING** for mismatch; **PASS** if matched. |
| `NAME_001` | Candidate Name Match | Name | Compares applicant-submitted name against extracted candidate name using normalized token containment and Levenshtein distance. | **WARNING** if similarity < 0.80 or missing; **PASS** if matched. |
| `FIELD_001` | Required Fields Presence | Field | Verifies that all fields required by `document_type` (configured in `rule_configuration.required_fields`) are present in extracted data. | **WARNING** by default (severity configurable via `rule_configuration`); **PASS** if all present. |
| `FORMAT_001` | Non-fatal Format Anomaly | Format | Flags document layout anomalies or unexpected aspect ratios that do not block processing. | **WARNING** if anomaly detected; **PASS** otherwise. |
| `OCR_001` | OCR Quality & Confidence | OCR Quality | Checks mean OCR word confidence score against `rule_configuration.min_ocr_confidence` (default 0.50). | **WARNING** if confidence < threshold; **PASS** otherwise. |

### Risk Prioritization Score
- `risk_score` is an integer from `0` to `100`, computed as a weighted sum of rule severities and findings (e.g. `FAIL` = 25 pts, `WARNING` = 10 pts, scaled).
- **Explicit Role**: The risk score is strictly a secondary queue-sorting value used to order the reviewer queue so officers inspect higher-risk submissions first. It is never an automated verdict.

---

## 8. Tamper-Evident Cryptographic Audit Hash Chain

### Atomic Sequencing & Append Serialization
- To prevent clock drift, timestamp collisions, and concurrent race conditions:
  1. The backend obtains an atomic sequence number via `counters.find_one_and_update({"_id": "audit_sequence"}, {"$inc": {"seq": 1}}, upsert=True)`.
  2. The preceding audit log entry is queried by `sequence - 1`.
  3. If `sequence == 1`, `previous_hash = "0" * 64`. Otherwise, `previous_hash` equals the preceding entry's `event_hash`.
  4. Append operations are executed sequentially.

### JSON-Safe Canonicalization
Before hashing, all fields in `details` and the top-level payload must be converted to JSON-safe primitives (strings, numbers, booleans, lists, dictionaries). Objects like `ObjectId` must be stringified, and timestamps formatted as fixed ISO-8601 strings.

```python
canonical_dict = {
    "action": action,
    "actor_id": str(actor_id),
    "details": sanitize_for_json(details),  # Strictly JSON-safe primitives
    "entity_id": str(entity_id),
    "entity_type": entity_type,
    "previous_hash": previous_hash,
    "sequence": sequence,  # Integer counter
    "timestamp": timestamp,  # Fixed ISO-8601 string: YYYY-MM-DDTHH:MM:SS.sssZ
}
canonical_json = json.dumps(
    canonical_dict, sort_keys=True, separators=(",", ":")
)
event_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
```

### Verification Algorithm (`POST /api/audit/verify`)
- The verification endpoint queries `audit_logs` ordered by `sequence` ascending (not by timestamp).
- Iterates sequentially through records, verifying:
  1. `entry.sequence == expected_sequence`
  2. `entry.previous_hash == expected_previous_hash`
  3. `sha256(canonical_json(entry)) == entry.event_hash`
- If any discrepancy is detected, reports the exact broken sequence number and record ID.

---

## 9. Final Reconciled REST API Contract

### A. Authentication & User Profile (`/api/auth`)
- `POST /api/auth/register`: Register new account.
  - Body: `{ "email": str, "password": str, "name": str }`
  - Invariant: Always assigns `role="applicant"`. Ignores any client-supplied role.
- `POST /api/auth/login`: Authenticate with credentials.
  - Body: `{ "email": str, "password": str }`
  - Response: `{ "access_token": str, "token_type": "bearer" }`
- `GET /api/auth/me`: Retrieve authenticated user profile and role.

### B. Document Management & Revisions (`/api/documents`)
- `POST /api/documents/upload`: Submit initial document (Revision 1).
  - Form Data: `file: UploadFile`, `document_type: str`, `submitted_metadata: JSON string`
  - Validates size <= `MAX_UPLOAD_MB` and MIME type; rejects invalid uploads immediately.
- `GET /api/documents`: List documents with pagination and status filters.
  - Scope: Applicants see own documents; reviewers and admins see all.
- `GET /api/documents/{id}`: Retrieve document metadata and current revision details.
- `GET /api/documents/{id}/download`: Authorized stream download of current revision file from GridFS.
- `POST /api/documents/{id}/revisions`: Submit a new revision in response to `CORRECTION_REQUESTED`.
  - Form Data: `file: UploadFile`, `submitted_metadata: JSON string`
  - Advances `current_revision` to `N + 1`, stores new file in GridFS, resets status to `SUBMITTED`, enqueues processing job.
- `GET /api/documents/{id}/revisions`: List all revisions for document `{id}`.
- `GET /api/documents/{id}/revisions/{rev_num}/download`: Download specific revision binary file.
- `GET /api/documents/{id}/history`: Retrieve full chronological lifecycle history, revision transitions, and reviews.
- `GET /api/documents/{id}/results`: Retrieve OCR extracted text, structured fields, and per-rule verification findings for current revision.
- `POST /api/documents/{id}/reprocess`: Re-trigger OCR extraction and verification.
  - Permitted from: `PROCESSING_FAILED` or manually by authorized roles.
  - Invariant: Transitions status back to `PROCESSING` (never directly to `REJECTED`).

### C. Review Queue & Decisions (`/api/reviews`)
- `GET /api/reviews`: Reviewer queue.
  - **Design Choices**:
    - Fetches documents in `UNDER_REVIEW` status.
    - Sorted primarily by secondary `risk_score` descending (highest anomaly density first) and secondarily by `uploaded_at` ascending.
    - Supports query filters: `document_type`, `min_risk_score`, `page`, `limit`.
- `GET /api/reviews/{id}`: Detailed review workspace data for document `{id}` (metadata, file stream URL, extracted fields, per-rule findings, past review history).
- `POST /api/reviews/{id}/decision`: Submit reviewer decision.
  - Body: `{ "decision": "APPROVED" | "REJECTED" | "CORRECTION_REQUESTED", "remarks": str }`
  - Constraints: Reviewers cannot review their own submissions. Remarks are mandatory.

### D. Audit Trail (`/api/audit`)
- `GET /api/audit`: List audit logs with pagination and filters (`sequence`, `actor_id`, `action`).
- `GET /api/audit/{id}`: Retrieve audit logs relating to a specific entity ID.
- `POST /api/audit/verify`: Cryptographically verify the integrity of the audit hash chain in `sequence` order.

### E. Notifications (`/api/notifications`)
- `GET /api/notifications`: Retrieve current user notifications.
- `PATCH /api/notifications/{id}/read`: Mark notification as read.
- `POST /api/notifications/read-all`: Mark all notifications for current user as read.

### F. Analytics (`/api/analytics`)
- **Design Choices**:
  - Restricted to `reviewer`, `admin`, and `auditor` roles (`applicant` cannot access aggregate tenant/platform metrics).
- `GET /api/analytics/overview`: Key performance indicators (total submissions, pending reviews, approval rate, flagged rate, average turnaround time).
- `GET /api/analytics/trends`: Time-series trends of submissions, anomaly categories distribution, and document type breakdown.

### G. Administration (`/api/admin`)
- `GET /api/admin/users`: List users with search, role filters, and pagination.
- `PATCH /api/admin/users/{id}/role`: Update user role (`applicant`, `reviewer`, `admin`, `auditor`). Audited with `ROLE_CHANGED`.
- `PATCH /api/admin/users/{id}/status`: Activate or deactivate user. Audited with `USER_STATUS_CHANGED`.
- `GET /api/admin/rules`: List all verification rules and configurations.
- `PUT /api/admin/rules/{id}`: Update rule configuration (enabled status, severity, `rule_configuration` parameters). Audited with `RULE_UPDATED`.
- `GET /api/admin/jobs`: List background processing jobs and errors.
- `POST /api/admin/jobs/{id}/retry`: Manually retry a failed background processing job. Audited with `JOB_RETRIED`.

### H. System Health
- `GET /health`: Liveness probe (`{"status": "ok"}`).
- `GET /ready`: Readiness probe verifying MongoDB connectivity (`{"status": "ready", "database": "up"}`).

---

## 10. Frontend Design System & Apple/Linear Aesthetic

### Design Tokens
- **Background**: Single warm off-white (`#F9F9FB`) across all views.
- **Card Surfaces**: Crisp white (`#FFFFFF`) with subtle border (`border-slate-200/80` or `#E2E8F0`).
- **Primary Text**: Near-black (`#111827`).
- **Secondary Text**: Cool grey (`#64748B`).
- **Accent**: Indigo (`#4F46E5`, hover `#4338CA`).
- **Border Radius**: 10–14px (`rounded-xl` or `rounded-2xl`).
- **Typography**: Inter (clean, high legibility, tight tracking).
- **Spacing**: 8-point system (8px, 16px, 24px, 32px).
- **Icons**: Lucide React (stroke width 1.5–1.75px).

### UI Layout Principles
- High density, clean typography, calm aesthetic.
- No flashy rainbow gradients, no distracting bouncing animations, no oversized decorative cards.
- Document inspection workspace provides high-resolution document viewing side-by-side with structured extracted field cards (no bounding box overlays).

---

## 11. Conflicts Identified Between Existing Files and Specification

| Area | Existing Scaffold / Build Guide File | Specification Requirement | Resolution in Specification |
| :--- | :--- | :--- | :--- |
| **Worker Process** | Build Guide mentioned a separate worker container (`worker-deployment.yaml`, worker service). | User requirement #7: No separate worker container. Processing runs as an in-process background thread inside the backend. Only two images exist: `backend` and `frontend`. | In-process background worker thread specified; `docker-compose.yml` and `k8s/` remain 2 services only. |
| **Revision Route** | Earlier draft suggested `POST /api/documents/{id}/revise`. | Standardized RESTful design: `POST /api/documents/{id}/revisions`. | Updated endpoint to `POST /api/documents/{id}/revisions`. |
| **Audit Verification** | Generic designs iterate by `timestamp`. | Requirement #1: Verification must use integer `sequence` order (atomic counter), not timestamp, to eliminate clock skew / collision bugs. | Added `sequence` field, `counters` collection, and sequence-based verification. |
| **Duplicate Rule** | Earlier guides treated duplicates as `FAIL`. | Requirement #2: `DUP_001` is strictly `WARNING` (neutral review flag, never `FAIL`). | Updated `DUP_001` to `WARNING` with neutral wording. |
| **Upload vs. Rule Failures** | Earlier specs mixed corrupted files into verification rule results. | Requirement #4: Corrupt files/upload failures become `PROCESSING_FAILED` or are rejected at upload. They are not verification `FAIL`s. | `FORMAT_001` is reserved strictly for non-fatal format quirks. |
| **Phase Numbering** | `README.md` stated "Phase 0-1 scaffold". | Roadmap specifies: Phase 0 is architecture/scaffold; Phase 1 is Backend + Atlas and is **NOT started**. | Updated roadmap and phase numbering explicitly. |
| **Registration Role** | Generic starter auth allowed specifying `role`. | Requirement: Registration always creates `role="applicant"`. No role selector on login. | Removed role parameter from register; role selection removed. |

---

## 12. Development Roadmap & Phase Status

- **Phase 0: Architecture & Baseline Scaffold** *(COMPLETE)*
  - Specification, architecture docs, initial folder layout, starter FastAPI health endpoints, starter React app.
- **Phase 1: Backend + Atlas** *(NOT STARTED)*
  - Complete backend folder structure, PyMongo connection to MongoDB Atlas, verified configuration, database collections and indexes creation, health & ready probes verification.
- **Phase 2: Frontend** *(PENDING)*
  - React + Vite + Tailwind CSS dashboard with warm off-white `#F9F9FB` theme, Inter font, Apple/Linear layout, navigation for all core views.
- **Phase 3: Auth + Upload** *(PENDING)*
  - User registration (`role="applicant"`), login with JWT, Argon2 hashing, GridFS upload, multi-revision creation, metadata persistence.
- **Phase 4: OCR + Verification** *(PENDING)*
  - In-backend background worker thread, PyMuPDF and Tesseract OCR, DUP/DATE/NAME/FIELD/FORMAT/OCR rule engine, per-rule findings, `PROCESSING_FAILED` handling.
- **Phase 5: Review + Audit** *(PENDING)*
  - Reviewer queue sorted by secondary risk score, decision workflow, atomic sequence counter, tamper-evident audit hash chain, chain verification endpoint.
- **Phase 6: Integration** *(PENDING)*
  - Real API hookup across all frontend views, removal of mock data, notifications, real MongoDB analytics dashboard.
- **Phase 7: Testing + Security** *(PENDING)*
  - Comprehensive Pytest suite covering Auth, RBAC, File Uploads, OCR, Rules, Decisions, and Audit verification.
- **Phase 8: Docker** *(PENDING)*
  - Production Dockerfiles for `backend` and `frontend`, `docker-compose.yml` multi-container verification.
- **Phase 9: Kubernetes** *(PENDING)*
  - Minikube manifests: Namespace, ConfigMap, Secrets, Deployments, Services, and Probes (2 deployments: backend and frontend).
- **Phase 10: Jenkins** *(PENDING)*
  - Automated Jenkinsfile pipeline for testing, building, image publishing, and Kubernetes deployment.
