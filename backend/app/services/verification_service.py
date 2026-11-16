import re
import fitz  # PyMuPDF
from datetime import datetime, timezone
from bson import ObjectId
from app.services.audit_service import record_audit_event

try:
    import pytesseract
    from PIL import Image
    import io
    HAS_TESSERACT = True
except Exception:
    HAS_TESSERACT = False


def extract_text_from_pdf_bytes(file_bytes: bytes) -> tuple[str, float]:
    """Extracts text using PyMuPDF; falls back to Tesseract OCR if page is image-only."""
    text_content = []
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = len(doc)
    
    for page_num in range(total_pages):
        page = doc[page_num]
        txt = page.get_text()
        if txt.strip():
            text_content.append(txt)
        elif HAS_TESSERACT:
            # Fallback to OCR for scanned/image pages
            try:
                pix = page.get_pixmap()
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = pytesseract.image_to_string(img)
                if ocr_text.strip():
                    text_content.append(ocr_text)
            except Exception:
                pass

    full_text = "\n".join(text_content).strip()
    doc.close()
    
    confidence = 0.95 if full_text else 0.0
    return full_text, confidence


def parse_structured_fields(raw_text: str, submitted_metadata: dict) -> dict:
    fields = {}

    # 1. Candidate Name
    name_match = re.search(
        r"(?:Name|Candidate|Student|Holder|Issued To)[:\s]+([A-Za-z\s]{3,40})",
        raw_text,
        re.IGNORECASE,
    )
    if name_match:
        fields["candidate_name"] = name_match.group(1).strip()
    elif submitted_metadata.get("candidate_name"):
        # Check if submitted name appears anywhere in the text
        sub_name = submitted_metadata["candidate_name"].strip()
        if sub_name.lower() in raw_text.lower():
            fields["candidate_name"] = sub_name

    # 2. Registration / Certificate Number
    reg_match = re.search(
        r"(?:Reg(?:istration)?\s*(?:No|Num|Number|#)?|Cert(?:ificate)?\s*(?:No|#)?|ID)[:.\s]*([A-Z0-9-]{4,25})",
        raw_text,
        re.IGNORECASE,
    )
    if reg_match:
        fields["registration_number"] = reg_match.group(1).strip()
    elif submitted_metadata.get("registration_number"):
        sub_reg = submitted_metadata["registration_number"].strip()
        if sub_reg.lower() in raw_text.lower():
            fields["registration_number"] = sub_reg

    # 3. Issue Date
    date_match = re.search(
        r"\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b",
        raw_text,
    )
    if date_match:
        fields["issue_date"] = date_match.group(1).strip()
    elif submitted_metadata.get("issue_date"):
        fields["issue_date"] = submitted_metadata["issue_date"].strip()

    return fields


def evaluate_verification_rules(
    db,
    document_id: ObjectId | str,
    revision_sha256: str,
    extracted_fields: dict,
    submitted_metadata: dict,
    raw_text: str,
) -> tuple[list[dict], int, str]:
    rule_results = []
    total_penalty = 0

    # DUP_001: Exact duplicate by SHA-256 (WARNING, neutral wording)
    dup_match = db.document_revisions.find_one({
        "sha256": revision_sha256,
        "document_id": {"$ne": ObjectId(document_id)},
    })
    if dup_match:
        rule_results.append({
            "rule_id": "DUP_001",
            "rule_name": "Exact File Duplicate",
            "category": "duplicate",
            "status": "WARNING",
            "severity": "medium",
            "explanation": f"Identical file found in existing submission (Document ID: {dup_match['document_id']}); review needed.",
            "evidence": f"Matched SHA-256 hash: {revision_sha256}",
        })
        total_penalty += 20
    else:
        rule_results.append({
            "rule_id": "DUP_001",
            "rule_name": "Exact File Duplicate",
            "category": "duplicate",
            "status": "PASS",
            "severity": "low",
            "explanation": "No identical file hash detected in repository.",
            "evidence": f"Unique SHA-256 hash: {revision_sha256}",
        })

    # FIELD_001: Required fields check
    name_found = bool(extracted_fields.get("candidate_name"))
    if not name_found:
        rule_results.append({
            "rule_id": "FIELD_001",
            "rule_name": "Candidate Name Detected",
            "category": "field_presence",
            "status": "WARNING",
            "severity": "medium",
            "explanation": "Candidate name could not be automatically verified in extracted text.",
            "evidence": "Candidate name pattern not matched in OCR text",
        })
        total_penalty += 15
    else:
        rule_results.append({
            "rule_id": "FIELD_001",
            "rule_name": "Candidate Name Detected",
            "category": "field_presence",
            "status": "PASS",
            "severity": "low",
            "explanation": f"Candidate name detected: {extracted_fields['candidate_name']}",
            "evidence": extracted_fields["candidate_name"],
        })

    # FIELD_002: Registration Number check
    reg_found = bool(extracted_fields.get("registration_number"))
    if not reg_found:
        rule_results.append({
            "rule_id": "FIELD_002",
            "rule_name": "Registration Number Detected",
            "category": "field_presence",
            "status": "WARNING",
            "severity": "medium",
            "explanation": "Registration or Certificate number was not clearly detected.",
            "evidence": "No registration identifier matched in document",
        })
        total_penalty += 15
    else:
        rule_results.append({
            "rule_id": "FIELD_002",
            "rule_name": "Registration Number Detected",
            "category": "field_presence",
            "status": "PASS",
            "severity": "low",
            "explanation": f"Registration number detected: {extracted_fields['registration_number']}",
            "evidence": extracted_fields["registration_number"],
        })

    # DATE_001: Date consistency
    extracted_date = extracted_fields.get("issue_date")
    submitted_date = submitted_metadata.get("issue_date")

    date_flagged = False
    if extracted_date:
        try:
            # Check for future date
            clean_date = extracted_date.replace("/", "-")
            parsed_dt = datetime.strptime(clean_date[:10], "%Y-%m-%d")
            if parsed_dt.date() > datetime.now(timezone.utc).date():
                rule_results.append({
                    "rule_id": "DATE_001",
                    "rule_name": "Date Consistency",
                    "category": "date_consistency",
                    "status": "FAIL",
                    "severity": "high",
                    "explanation": f"Issue date '{extracted_date}' is in the future.",
                    "evidence": f"Detected date: {extracted_date}",
                })
                total_penalty += 35
                date_flagged = True
        except Exception:
            pass

    if not date_flagged:
        if submitted_date and extracted_date and submitted_date.strip() != extracted_date.strip():
            rule_results.append({
                "rule_id": "DATE_001",
                "rule_name": "Date Consistency",
                "category": "date_consistency",
                "status": "WARNING",
                "severity": "medium",
                "explanation": f"Extracted date ({extracted_date}) differs from applicant-submitted date ({submitted_date}).",
                "evidence": f"Submitted: {submitted_date} | Extracted: {extracted_date}",
            })
            total_penalty += 15
        elif not extracted_date and not submitted_date:
            rule_results.append({
                "rule_id": "DATE_001",
                "rule_name": "Date Consistency",
                "category": "date_consistency",
                "status": "WARNING",
                "severity": "low",
                "explanation": "No issue date detected or submitted.",
                "evidence": "Date absent",
            })
            total_penalty += 10
        else:
            rule_results.append({
                "rule_id": "DATE_001",
                "rule_name": "Date Consistency",
                "category": "date_consistency",
                "status": "PASS",
                "severity": "low",
                "explanation": "Date consistency verified.",
                "evidence": extracted_date or submitted_date,
            })

    risk_score = min(100, total_penalty)
    if risk_score >= 40:
        risk_level = "high"
    elif risk_score >= 20:
        risk_level = "medium"
    else:
        risk_level = "low"

    return rule_results, risk_score, risk_level


def process_document_sync(db, grid_fs, document_id: str | ObjectId, revision_number: int):
    """Processes document text extraction and verification rules; updates MongoDB."""
    doc_id = ObjectId(document_id)
    doc = db.documents.find_one({"_id": doc_id})
    if not doc:
        return

    # Update to PROCESSING
    db.documents.update_one(
        {"_id": doc_id},
        {"$set": {"status": "PROCESSING", "updated_at": datetime.now(timezone.utc)}},
    )

    try:
        rev = db.document_revisions.find_one({
            "document_id": doc_id,
            "revision_number": revision_number,
        })
        if not rev:
            raise ValueError(f"Revision {revision_number} not found for document {doc_id}")

        file_id = rev["file_id"]
        grid_out = grid_fs.get(file_id)
        file_bytes = grid_out.read()

        # 1. OCR / Text Extraction
        raw_text, confidence = extract_text_from_pdf_bytes(file_bytes)
        submitted_metadata = rev.get("submitted_metadata", {})
        extracted_fields = parse_structured_fields(raw_text, submitted_metadata)

        # Save extractions
        extraction_doc = {
            "document_id": doc_id,
            "revision_number": revision_number,
            "extracted_text": raw_text,
            "fields": extracted_fields,
            "confidence": confidence,
            "created_at": datetime.now(timezone.utc),
        }
        db.extractions.replace_one(
            {"document_id": doc_id, "revision_number": revision_number},
            extraction_doc,
            upsert=True,
        )

        # 2. Rule Evaluation
        rule_results, risk_score, risk_level = evaluate_verification_rules(
            db=db,
            document_id=doc_id,
            revision_sha256=rev["sha256"],
            extracted_fields=extracted_fields,
            submitted_metadata=submitted_metadata,
            raw_text=raw_text,
        )

        verification_doc = {
            "document_id": doc_id,
            "revision_number": revision_number,
            "rule_results": rule_results,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "rule_version": "1.0",
            "evaluated_at": datetime.now(timezone.utc),
        }
        db.verification_results.replace_one(
            {"document_id": doc_id, "revision_number": revision_number},
            verification_doc,
            upsert=True,
        )

        # 3. Transition to UNDER_REVIEW
        db.documents.update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "status": "UNDER_REVIEW",
                    "updated_at": datetime.now(timezone.utc),
                    "risk_score": risk_score,
                }
            },
        )

        record_audit_event(
            db=db,
            actor_id="system",
            action="VERIFICATION_EVALUATED",
            entity_type="document",
            entity_id=doc_id,
            details={
                "revision_number": revision_number,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "rule_count": len(rule_results),
            },
        )

    except Exception as e:
        # Technical error transitions to PROCESSING_FAILED, NEVER REJECTED
        db.documents.update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "status": "PROCESSING_FAILED",
                    "processing_error": str(e),
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        record_audit_event(
            db=db,
            actor_id="system",
            action="PROCESSING_FAILED",
            entity_type="document",
            entity_id=doc_id,
            details={"error": str(e), "revision_number": revision_number},
        )

