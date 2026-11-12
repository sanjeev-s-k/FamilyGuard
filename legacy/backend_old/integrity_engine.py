"""
Log Integrity and Tamper Detection Engine
Provides cryptographic HMAC SHA-256 verification and detection of log modifications.
"""

import hmac
import hashlib
import json
from typing import Dict, Any, Tuple

# Secret key used by local agents and central analyzer (simulated secure key distribution)
INTEGRITY_SECRET = b"CRPF-SEC-LOG-INTEGRITY-KEY-2026-X99"


def compute_log_hash(event_data: Dict[str, Any], secret_key: bytes = INTEGRITY_SECRET) -> str:
    """
    Computes a deterministic HMAC-SHA256 hash across canonical event fields.
    Canonical fields include: timestamp, location, server_id, user_id, device_id, source_ip, event_type, login_status, raw_log.
    """
    canonical_payload = {
        "timestamp": str(event_data.get("timestamp", "")),
        "location": str(event_data.get("location", "")),
        "server_id": str(event_data.get("server_id", "")),
        "user_id": str(event_data.get("user_id", "")),
        "device_id": str(event_data.get("device_id", "")),
        "source_ip": str(event_data.get("source_ip", "")),
        "event_type": str(event_data.get("event_type", "")),
        "login_status": str(event_data.get("login_status", "")),
        "raw_log": str(event_data.get("raw_log", "")),
        "target_resource": str(event_data.get("target_resource", ""))
    }
    # Sort keys for deterministic JSON encoding
    serialized = json.dumps(canonical_payload, sort_keys=True)
    return hmac.new(secret_key, serialized.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_log_integrity(event_data: Dict[str, Any], secret_key: bytes = INTEGRITY_SECRET) -> Tuple[bool, str, str]:
    """
    Verifies if the event hash matches the payload.
    Returns: (is_valid, calculated_hash, explanation)
    """
    recorded_hash = event_data.get("hash_signature", "")
    if not recorded_hash:
        return False, "", "Missing cryptographic hash signature (Unsigned Log)"

    calculated_hash = compute_log_hash(event_data, secret_key)

    if hmac.compare_digest(recorded_hash, calculated_hash):
        return True, calculated_hash, "Integrity Status: VERIFIED ✅ (Cryptographic HMAC matches payload exactly)"
    else:
        return False, calculated_hash, (
            "Integrity Warning ⚠️ — Log content appears to have changed! "
            f"Original signature ({recorded_hash[:12]}...) does not match recalculated hash ({calculated_hash[:12]}...)"
        )


def simulate_log_tampering(event_data: Dict[str, Any], field_to_alter: str, new_value: Any) -> Dict[str, Any]:
    """
    Creates a tampered version of an existing log event by mutating a specific field
    without updating the original hash signature.
    """
    tampered = dict(event_data)
    tampered[field_to_alter] = new_value
    # Keep the original hash_signature intact to create tamper evidence
    tampered["integrity_status"] = "TAMPERED"
    tampered["raw_log"] = f"[TAMPERED] {tampered.get('raw_log', '')}"
    return tampered
