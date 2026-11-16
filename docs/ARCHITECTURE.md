# VerifyFlow — Architecture Blueprint & Phase 0 Baseline

## 1. Executive Summary & Phase Status
**VerifyFlow** is an intelligent document authenticity assessment, verification, and digital audit platform. It extracts structured data from uploaded documents, detects duplicates, evaluates rule-based anomalies, supports human-in-the-loop review, and guarantees tamper-evident event provenance via a cryptographic audit hash chain.

### Phased Roadmap & Current Status
- **Phase 0: Architecture & Baseline Scaffold** — **COMPLETE**.
  - System specification, architecture docs, initial folder layout, starter FastAPI health endpoints, starter React app.
- **Phase 1: Backend + Atlas** — **NOT STARTED**.
  - Complete backend folder structure, PyMongo connection to MongoDB Atlas, verified configuration, database collections and indexes creation, health & ready probes verification.
- **Phase 2: Frontend** — **PENDING**.
  - React + Vite + Tailwind CSS dashboard with warm off-white (`#F9F9FB`) theme, Inter font, Apple/Linear layout, navigation for all core views.
- **Phase 3: Auth + Upload** — **PENDING**.
  - User registration (`role="applicant"`), login with JWT, Argon2 hashing, GridFS upload, multi-revision creation, metadata persistence.
- **Phase 4: OCR + Verification** — **PENDING**.
  - In-backend background worker thread, PyMuPDF and Tesseract OCR, DUP/DATE/NAME/FIELD/FORMAT/OCR rule engine, per-rule findings, `PROCESSING_FAILED` handling.
- **Phase 5: Review + Audit** — **PENDING**.
  - Reviewer queue sorted by secondary risk score, decision workflow, atomic sequence counter, tamper-evident audit hash chain, chain verification endpoint.
- **Phase 6: Integration** — **PENDING**.
  - Real API hookup across all frontend views, removal of mock data, notifications, real MongoDB analytics dashboard.
- **Phase 7: Testing + Security** — **PENDING**.
  - Comprehensive Pytest suite covering Auth, RBAC, File Uploads, OCR, Rules, Decisions, and Audit verification.
- **Phase 8: Docker** — **PENDING**.
  - Production Dockerfiles for `backend` and `frontend`, `docker-compose.yml` multi-container verification (exactly two images).
- **Phase 9: Kubernetes** — **PENDING**.
  - Minikube manifests: Namespace, ConfigMap, Secrets, Deployments, Services, and Probes (2 deployments: backend and frontend).
- **Phase 10: Jenkins** — **PENDING**.
  - Automated Jenkinsfile pipeline for testing, building, image publishing, and Kubernetes deployment.

---

## 2. High-Level Component Topology (Two-Container Model)

```
                       ┌─────────────────────────────────────────┐
                       │          React + Vite Frontend          │
                       │    (Apple / Linear Minimalist SaaS)     │
                       │     Warm off-white background #F9F9FB   │
                       └────────────────────┬────────────────────┘
                                            │ HTTP / REST
                                            ▼
                       ┌─────────────────────────────────────────┐
                       │           FastAPI Gateway API           │
                       │   (Auth, Document APIs, Review Queue)   │
                       │ ┌─────────────────────────────────────┐ │
                       │ │    In-Process Background Worker     │ │
                       │ │    Thread (Polls processing_jobs)   │ │
                       │ └─────────────────────────────────────┘ │
                       └───────────┬─────────────────┬───────────┘
                                   │                 │
                      PyMongo Read │                 │ PyMongo / GridFS
                                   ▼                 ▼
                       ┌─────────────────────────────────────────┐
                       │              MongoDB Atlas              │
                       │ (users, documents, revisions, audit_logs│
                       │  counters, extractions, rules, reviews) │
                       │                    +                    │
                       │             MongoDB GridFS              │
                       │   (fs.files, fs.chunks by revision)     │
                       └─────────────────────────────────────────┘
```

### Process & Container Invariant
- **No Separate Worker Container**: Processing runs as an asynchronous background thread/task inside the backend application process. This simplifies deployment, eliminates distributed worker synchronization overhead for small/medium clusters, and keeps the container footprint strictly to **two container images**: `backend` and `frontend`.
- **Worker Concurrency**: The background thread polls `processing_jobs` with an atomic check (`find_one_and_update` with `status: "PENDING"` -> `status: "IN_PROGRESS"`).

---

## 3. Document Lifecycle State Machine

```
              ┌──────────────────────────┐
              │        SUBMITTED         │
              └─────────────┬────────────┘
                            │ (In-process worker begins OCR & Rules)
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

### Lifecycle Invariants
1. `SUBMITTED` -> `PROCESSING`: When in-process worker thread begins job.
2. `PROCESSING` -> `PROCESSING_FAILED`: Occurs upon corrupt file or extraction crash.
3. `PROCESSING_FAILED` -> `PROCESSING`: Occurs upon reprocess trigger (`POST /api/documents/{id}/reprocess`).
4. **STRICT INVARIANT**: `PROCESSING_FAILED` must **NEVER** transition directly to `REJECTED`. Processing failures are technical/file issues, not reviewer decisions. Only a human reviewer can reject a document from `UNDER_REVIEW`.
5. `PROCESSING` -> `UNDER_REVIEW`: Occurs when OCR extraction and all verification rules have executed.
6. `UNDER_REVIEW` -> `APPROVED` | `REJECTED` | `CORRECTION_REQUESTED`: Occurs upon submission of a formal reviewer decision.
7. `CORRECTION_REQUESTED` -> `SUBMITTED`: When the applicant submits a revised file via `POST /api/documents/{id}/revisions`, a new revision (`revision_number = N + 1`) is created with status `SUBMITTED`, preserving all previous revision history.

---

## 4. Multi-Revision Architecture
- Every document consists of a parent document record in `documents` tracking `current_revision` (starts at 1).
- Each revision is preserved in `document_revisions` with its own:
  - `revision_number`: integer (1, 2, 3...)
  - `file_id`: GridFS ObjectId pointing to its specific file chunks.
  - `sha256`: Unique cryptographic hash of that specific revision's content.
  - `submitted_metadata`: User inputs associated with this revision.
  - `previous_revision_id`: Reference linking to the previous revision.
- Downstream artifacts (`extractions`, `verification_results`, `reviews`, `processing_jobs`) store `revision_number`.
- Historical revisions are immutable and never overwritten.

---

## 5. Verification Rules Engine & Findings Model

### File Failure Handling vs. Verification Rules
- Corrupt files, files exceeding `MAX_UPLOAD_MB`, or invalid MIME types are either rejected immediately at upload (HTTP 400/413/415) or transition to `PROCESSING_FAILED`. They are **not** a verification `FAIL`.
- `FORMAT_001` is reserved strictly for non-fatal layout/structure verification findings that do not prevent text extraction.
- `DUP_001` evaluates to **`WARNING`** (never `FAIL`). Evidence/explanation: "Identical file found in existing submission (ID: ...); review needed." Flags for human inspection.
- `FIELD_001` evaluates to **`WARNING`** by default (severity configurable via `rule_configuration`).

### Verification Result Structure
```json
{
  "document_id": "ObjectId",
  "revision_number": 1,
  "rule_results": [
    {
      "rule_id": "DUP_001",
      "category": "duplicate",
      "status": "WARNING",
      "severity": "medium",
      "explanation": "Identical file found in existing submission (ID: 66a1...); review needed.",
      "evidence": "SHA-256 match with document 66a1..."
    },
    {
      "rule_id": "FIELD_001",
      "category": "field_presence",
      "status": "WARNING",
      "severity": "medium",
      "explanation": "Field 'certificate_number' was not detected in extracted text.",
      "evidence": "Missing certificate_number in OCR output"
    }
  ],
  "risk_score": 20,
  "risk_level": "low",
  "rule_version": "1.0",
  "evaluated_at": "2026-11-16T08:15:30.123Z"
}
```
- The `risk_score` (0–100) serves strictly as a secondary queue-sorting and prioritization value, ordering documents with more anomalies to the top of the reviewer queue.

---

## 6. Cryptographic Audit Hash Chain

### Deterministic Atomic Sequencing
- Each audit record is assigned a monotonic integer `sequence` (1, 2, 3...) via an atomic MongoDB counter (`counters` collection with `$inc`).
- The previous hash of entry with `sequence` $k$ is the `event_hash` of entry with `sequence` $k - 1$. Genesis ($k=1$) uses `"0"*64`.
- All fields in `details` must strictly contain JSON-safe values before canonical serialization.

```python
canonical_dict = {
    "action": action,
    "actor_id": str(actor_id),
    "details": sanitize_for_json(details),  # Strictly JSON-safe primitives
    "entity_id": str(entity_id),
    "entity_type": entity_type,
    "previous_hash": previous_hash,
    "sequence": sequence,  # Monotonic integer counter
    "timestamp": timestamp,  # Fixed ISO-8601 string: YYYY-MM-DDTHH:MM:SS.sssZ
}
canonical_json = json.dumps(
    canonical_dict, sort_keys=True, separators=(",", ":")
)
event_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
```

### Audited Actions
Audit logs record the following actions:
- `DOCUMENT_SUBMITTED`, `PROCESSING_STARTED`, `PROCESSING_FAILED`
- `OCR_EXTRACTED`, `VERIFICATION_EVALUATED`
- `DOCUMENT_APPROVED`, `DOCUMENT_REJECTED`, `CORRECTION_REQUESTED`
- `REVISION_SUBMITTED`
- `ROLE_CHANGED`, `USER_STATUS_CHANGED`
- `RULE_UPDATED`, `JOB_RETRIED`

### Verification
- `POST /api/audit/verify` iterates strictly in **`sequence` order** (ascending), recalculating each hash and verifying `entry.previous_hash == prev_entry.event_hash`.

---

## 7. Role-Permission Matrix Table

| Action / Resource | Applicant | Reviewer | Auditor | Administrator |
| :--- | :---: | :---: | :---: | :---: |
| Register account (`POST /api/auth/register`) | Public | Public | Public | Public |
| Login (`POST /api/auth/login`) | Yes | Yes | Yes | Yes |
| View own profile (`GET /api/auth/me`) | Yes | Yes | Yes | Yes |
| Upload initial document (`POST /api/documents/upload`) | Yes | No | No | No |
| Upload revision (`POST /api/documents/{id}/revisions`) | Yes (Own) | No | No | No |
| View document list (`GET /api/documents`) | Yes (Own) | Yes (All) | Yes (All) | Yes (All) |
| Download document / revision file | Yes (Own) | Yes (All) | Yes (All) | Yes (All) |
| Reprocess document (`POST /api/documents/{id}/reprocess`) | Yes (Own) | Yes | No | Yes |
| View Reviewer Queue (`GET /api/reviews`) | No | Yes | Yes (Read) | Yes |
| View Review Workspace (`GET /api/reviews/{id}`) | No | Yes | Yes (Read) | Yes |
| Submit Review Decision (`POST /api/reviews/{id}/decision`) | No | Yes | No | Yes |
| View Audit Logs (`GET /api/audit`) | No | No | Yes | Yes |
| Verify Audit Chain (`POST /api/audit/verify`) | No | No | Yes | Yes |
| View Analytics Overview/Trends (`/api/analytics/*`) | No | Yes | Yes | Yes |
| Receive Notifications (`GET /api/notifications`) | Yes (Own) | Yes (Own) | Yes (Own) | Yes (Own) |
| Manage User Roles & Status (`PATCH /api/admin/users/*`) | No | No | No | Yes |
| Configure Rules (`PUT /api/admin/rules/*`) | No | No | No | Yes |
| Monitor / Retry Jobs (`/api/admin/jobs/*`) | No | No | No | Yes |

---

## 8. Database Collections & Explicit Index List

| Collection | Key Fields | Indexes | Index Purpose |
| :--- | :--- | :--- | :--- |
| `users` | `_id`, `name`, `email`, `password_hash`, `role`, `is_active` | `{"email": 1}` (`unique=True`) | Authentication and unique email lookup |
| `documents` | `_id`, `owner_id`, `document_type`, `status`, `current_revision` | `{"owner_id": 1}`<br>`{"status": 1}` | Owner filtering<br>Status/queue filtering |
| `document_revisions` | `_id`, `document_id`, `revision_number`, `file_id`, `sha256` | `{"document_id": 1, "revision_number": 1}` (`unique=True`)<br>`{"sha256": 1}` | Revision uniqueness<br>SHA-256 duplicate search |
| `extractions` | `_id`, `document_id`, `revision_number`, `extracted_text`, `fields` | `{"document_id": 1, "revision_number": 1}` | OCR lookup per revision |
| `verification_results` | `_id`, `document_id`, `revision_number`, `rule_results`, `risk_score` | `{"document_id": 1, "revision_number": 1}` | Findings lookup per revision |
| `reviews` | `_id`, `document_id`, `revision_number`, `reviewer_id`, `decision` | `{"document_id": 1, "revision_number": 1}`<br>`{"reviewer_id": 1}` | Review per revision<br>Reviewer history |
| `audit_logs` | `_id`, `sequence`, `actor_id`, `action`, `previous_hash`, `event_hash` | `{"sequence": 1}` (`unique=True`)<br>`{"entity_id": 1}`<br>`{"timestamp": 1}` | Deterministic chain verification<br>Entity audit trail<br>Timeline queries |
| `counters` | `_id`, `seq` | `{"_id": 1}` | Atomic counter primary key |
| `processing_jobs` | `_id`, `document_id`, `revision_number`, `status`, `attempts` | `{"status": 1, "created_at": 1}`<br>`{"document_id": 1, "revision_number": 1}` | Worker queue polling<br>Job status check |
| `verification_rules` | `_id`, `rule_id`, `severity`, `enabled`, `rule_configuration` | `{"rule_id": 1}` (`unique=True`) | Unique rule identifier |
| `notifications` | `_id`, `user_id`, `title`, `is_read`, `created_at` | `{"user_id": 1, "is_read": 1}` | Unread user notifications |

---

## 9. Conflicts Identified Between Existing Files and Specification

| Area | Existing Scaffold / Build Guide File | Specification Requirement | Resolution in Specification |
| :--- | :--- | :--- | :--- |
| **Worker Process** | Build Guide mentioned a separate worker container (`worker-deployment.yaml`, worker service). | User requirement: No separate worker container. Processing runs as an in-process background thread inside the backend. Only two images exist: `backend` and `frontend`. | In-process background worker thread specified; `docker-compose.yml` and `k8s/` remain 2 services only. |
| **Revision Route** | Earlier draft suggested `POST /api/documents/{id}/revise`. | Standardized RESTful design: `POST /api/documents/{id}/revisions`. | Updated endpoint to `POST /api/documents/{id}/revisions`. |
| **Audit Verification** | Generic designs iterate by `timestamp`. | Requirement: Verification must use integer `sequence` order (atomic counter), not timestamp, to eliminate clock skew / collision bugs. | Added `sequence` field, `counters` collection, and sequence-based verification. |
| **Duplicate Rule** | Earlier guides treated duplicates as `FAIL`. | Requirement: `DUP_001` is strictly `WARNING` (neutral review flag, never `FAIL`). | Updated `DUP_001` to `WARNING` with neutral wording. |
| **Upload vs. Rule Failures** | Earlier specs mixed corrupted files into verification rule results. | Requirement: Corrupt files/upload failures become `PROCESSING_FAILED` or are rejected at upload. They are not verification `FAIL`s. | `FORMAT_001` is reserved strictly for non-fatal format quirks. |
| **Phase Numbering** | `README.md` stated "Phase 0-1 scaffold". | Roadmap specifies: Phase 0 is architecture/scaffold; Phase 1 is Backend + Atlas and is **NOT started**. | Updated roadmap and phase numbering explicitly. |
| **Registration Role** | Generic starter auth allowed specifying `role`. | Requirement: Registration always creates `role="applicant"`. No role selector on login. | Removed role parameter from register; role selection removed. |

---

## 10. Final Reconciled REST API Contract

### Endpoints List & Architectural Decisions

#### 1. Authentication (`/api/auth`)
- `POST /api/auth/register`: `{ email, password, name }` -> `role="applicant"` always.
- `POST /api/auth/login`: `{ email, password }` -> returns `{ access_token, token_type }`.
- `GET /api/auth/me`: Authenticated profile and role.

#### 2. Documents & Revisions (`/api/documents`)
- `POST /api/documents/upload`: Upload initial file (Revision 1). Size/MIME validated.
- `GET /api/documents`: List documents (applicants see own; reviewers/admins see all).
- `GET /api/documents/{id}`: Document metadata and current revision.
- `GET /api/documents/{id}/download`: Stream download current revision from GridFS.
- `POST /api/documents/{id}/revisions`: Submit revision in response to correction request.
- `GET /api/documents/{id}/revisions`: List all revisions for document.
- `GET /api/documents/{id}/revisions/{rev_num}/download`: Download specific revision file.
- `GET /api/documents/{id}/history`: Chronological lifecycle history and reviews.
- `GET /api/documents/{id}/results`: Extracted fields and per-rule findings.
- `POST /api/documents/{id}/reprocess`: Reprocess from `PROCESSING_FAILED` to `PROCESSING`.

#### 3. Review Queue & Decisions (`/api/reviews`)
- `GET /api/reviews`:
  - **Design Choices**:
    - Returns documents in `UNDER_REVIEW`.
    - Sorted primarily by secondary `risk_score` descending (highest anomaly density first), secondarily by `uploaded_at` ascending.
    - Query parameters: `document_type`, `min_risk_score`, `page`, `limit`.
- `GET /api/reviews/{id}`: Full review workspace data for document `{id}`.
- `POST /api/reviews/{id}/decision`: `{ decision: "APPROVED" | "REJECTED" | "CORRECTION_REQUESTED", remarks }`.

#### 4. Audit Trail (`/api/audit`)
- `GET /api/audit`: Query audit logs.
- `GET /api/audit/{id}`: Query logs for entity ID.
- `POST /api/audit/verify`: Verify hash chain in monotonic `sequence` order.

#### 5. Notifications (`/api/notifications`)
- `GET /api/notifications`: User notifications.
- `PATCH /api/notifications/{id}/read`: Mark as read.
- `POST /api/notifications/read-all`: Mark all as read.

#### 6. Analytics (`/api/analytics`)
- **Design Choices**:
  - Accessible only to `reviewer`, `admin`, and `auditor` roles (`applicant` cannot access aggregate tenant/platform metrics).
- `GET /api/analytics/overview`: Aggregate KPIs (totals, approval rates, average turnaround).
- `GET /api/analytics/trends`: Time-series trends of submissions and anomaly frequencies.

#### 7. Administration (`/api/admin`)
- `GET /api/admin/users`: List users.
- `PATCH /api/admin/users/{id}/role`: Change role (`ROLE_CHANGED`).
- `PATCH /api/admin/users/{id}/status`: Change active status (`USER_STATUS_CHANGED`).
- `GET /api/admin/rules`: List verification rules.
- `PUT /api/admin/rules/{id}`: Configure rule settings (`RULE_UPDATED`).
- `GET /api/admin/jobs`: List background processing jobs.
- `POST /api/admin/jobs/{id}/retry`: Retry failed job (`JOB_RETRIED`).

#### 8. Health Probes
- `GET /health`: Liveness probe (`{"status": "ok"}`).
- `GET /ready`: Readiness probe verifying MongoDB connectivity (`{"status": "ready", "database": "up"}`).

---

## 11. Frontend Design Tokens
- **Background**: Single warm off-white (`#F9F9FB`) across all application screens.
- **Card Surfaces**: Pure white (`#FFFFFF`) with subtle border (`border-slate-200/80` or `#E2E8F0`).
- **Typography**: Inter. Near-black primary text (`#111827`), cool grey secondary text (`#64748B`).
- **Accent**: Indigo (`#4F46E5`, hover `#4338CA`).
- **Icons**: Lucide React.
- **Document Viewing**: High-resolution document viewer displayed side-by-side with structured extracted field cards (no bounding box overlays).
