import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from bson import ObjectId
from pymongo import ReturnDocument


def sanitize_for_json(obj: Any) -> Any:
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in sorted(obj.items())}
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(item) for item in obj]
    return str(obj)


def compute_event_hash(
    sequence: int,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict,
    previous_hash: str,
    timestamp: str,
) -> str:
    canonical_dict = {
        "action": action,
        "actor_id": str(actor_id),
        "details": sanitize_for_json(details),
        "entity_id": str(entity_id),
        "entity_type": entity_type,
        "previous_hash": previous_hash,
        "sequence": sequence,
        "timestamp": timestamp,
    }
    canonical_json = json.dumps(
        canonical_dict, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def record_audit_event(
    db,
    actor_id: str | ObjectId,
    action: str,
    entity_type: str,
    entity_id: str | ObjectId,
    details: dict | None = None,
) -> dict:
    if details is None:
        details = {}

    counter_doc = db.counters.find_one_and_update(
        {"_id": "audit_sequence"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    sequence = counter_doc["seq"]

    if sequence == 1:
        previous_hash = "0" * 64
    else:
        prev_entry = db.audit_logs.find_one({"sequence": sequence - 1})
        previous_hash = prev_entry["event_hash"] if prev_entry else ("0" * 64)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    event_hash = compute_event_hash(
        sequence=sequence,
        actor_id=str(actor_id),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details,
        previous_hash=previous_hash,
        timestamp=timestamp,
    )

    doc = {
        "sequence": sequence,
        "actor_id": str(actor_id),
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "details": sanitize_for_json(details),
        "previous_hash": previous_hash,
        "event_hash": event_hash,
        "timestamp": timestamp,
        "created_at": datetime.now(timezone.utc),
    }

    db.audit_logs.insert_one(doc)
    doc["id"] = str(doc["_id"])
    return doc


def verify_chain(db) -> dict:
    logs = list(db.audit_logs.find().sort("sequence", 1))
    total = len(logs)
    if total == 0:
        return {"valid": True, "total_events": 0, "broken_at_sequence": None}

    expected_prev = "0" * 64
    for idx, log in enumerate(logs, start=1):
        seq = log.get("sequence")
        if seq != idx:
            return {
                "valid": False,
                "total_events": total,
                "broken_at_sequence": seq,
                "error": f"Sequence discontinuity at index {idx}, expected {idx} got {seq}",
            }

        if log.get("previous_hash") != expected_prev:
            return {
                "valid": False,
                "total_events": total,
                "broken_at_sequence": seq,
                "error": f"Previous hash mismatch at sequence {seq}. Expected {expected_prev}, found {log.get('previous_hash')}",
            }

        recomputed = compute_event_hash(
            sequence=seq,
            actor_id=log.get("actor_id"),
            action=log.get("action"),
            entity_type=log.get("entity_type"),
            entity_id=log.get("entity_id"),
            details=log.get("details", {}),
            previous_hash=log.get("previous_hash"),
            timestamp=log.get("timestamp"),
        )

        if recomputed != log.get("event_hash"):
            return {
                "valid": False,
                "total_events": total,
                "broken_at_sequence": seq,
                "error": f"Event hash tampering detected at sequence {seq}.",
            }

        expected_prev = log.get("event_hash")

    return {"valid": True, "total_events": total, "broken_at_sequence": None}

