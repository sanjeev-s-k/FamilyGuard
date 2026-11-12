"""
Log Normalization Engine
Converts heterogeneous log formats (Windows Event, Linux Syslog, Web, Cisco Firewall, DB Audit)
into a unified schema.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from backend.integrity_engine import compute_log_hash


class LogNormalizer:
    """Normalizes unstructured or semi-structured raw logs into standard schema."""

    @staticmethod
    def normalize_raw_log(
        raw_log: str,
        location: str = "North",
        server_id: str = "N-01",
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        lower_log = raw_log.lower()

        # Defaults
        user_id = "user_unknown"
        account = "unknown"
        device_id = "DEV-GENERIC-01"
        source_ip = "192.168.1.100"
        event_type = "SYSTEM_INFO"
        login_status = "N/A"
        failed_attempt_count = 0
        unusual_location = False
        unusual_time = False
        unknown_device = False
        account_verified = True
        target_resource = "/system"

        # Regex extractors
        ip_match = re.search(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", raw_log)
        if ip_match:
            source_ip = ip_match.group(0)

        user_match = re.search(r"\b(?:user|account|username|user_id)\b[:=\s]+([a-zA-Z0-9_\-]+)", raw_log, re.IGNORECASE)
        if user_match:
            user_id = user_match.group(1).lower()
            account = f"{user_id}_acc"

        dev_match = re.search(r"(?:device|workstation|host|dev_id)[:=\s]+([a-zA-Z0-9_\-]+)", raw_log, re.IGNORECASE)
        if dev_match:
            device_id = dev_match.group(1).upper()
            if "unknown" in device_id.lower():
                unknown_device = True

        # Rule-based classification for raw messages
        if any(w in lower_log for w in ["authentication failure", "login failed", "invalid credentials", "logon denied", "bad password", "event id 4625", "4625"]):
            event_type = "FAILED_LOGIN"
            login_status = "FAILURE"
            failed_attempt_count = 1
            # Check for repeated attempt counters in raw text
            attempt_match = re.search(r"(\d+)\s*(?:failed attempts|attempts failed)", lower_log)
            if attempt_match:
                failed_attempt_count = int(attempt_match.group(1))

        elif any(w in lower_log for w in ["successful login", "logon successful", "session opened", "event id 4624", "4624", "accepted password"]):
            event_type = "SUCCESSFUL_LOGIN"
            login_status = "SUCCESS"
            failed_attempt_count = 0

        elif any(w in lower_log for w in ["unauthorized file access", "suspicious file", "accessed sensitive directory", "bulk download", "file exfiltration"]):
            event_type = "SUSPICIOUS_FILE_ACCESS"
            target_resource = "/classified/confidential_records.tar.gz"

        elif any(w in lower_log for w in ["sudo", "privilege escalation", "elevated token", "runas", "setuid"]):
            event_type = "PRIVILEGE_ESCALATION"
            target_resource = "/etc/shadow"

        elif any(w in lower_log for w in ["exfiltration", "data transfer", "large upload", "s3 bucket sync"]):
            event_type = "DATA_EXFILTRATION"
            target_resource = "ext-transfer-endpoint"

        elif any(w in lower_log for w in ["port scan", "nmap", "syn flood", "syn scan"]):
            event_type = "PORT_SCAN"

        elif any(w in lower_log for w in ["command injection", "sql injection", "malicious payload"]):
            event_type = "COMMAND_INJECTION"

        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": ts,
            "location": location,
            "server_id": server_id,
            "user_id": user_id,
            "account": account,
            "device_id": device_id,
            "source_ip": source_ip,
            "event_type": event_type,
            "login_status": login_status,
            "failed_attempt_count": failed_attempt_count,
            "unusual_location": unusual_location,
            "unusual_time": unusual_time,
            "unknown_device": unknown_device,
            "account_verified": account_verified,
            "integrity_status": "VERIFIED",
            "raw_log": raw_log.strip(),
            "target_resource": target_resource,
            "session_id": f"sess_{uuid.uuid4().hex[:6]}",
            "metadata": {"normalized_by": "Central_Normalizer_v1"}
        }

        # Calculate cryptographic integrity HMAC hash
        event["hash_signature"] = compute_log_hash(event)
        return event

    @staticmethod
    def normalize_dict(event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validates and completes structured event dictionary."""
        normalized = dict(event_dict)
        if not normalized.get("event_id"):
            normalized["event_id"] = str(uuid.uuid4())
        if not normalized.get("timestamp"):
            normalized["timestamp"] = datetime.now(timezone.utc).isoformat()
        if not normalized.get("location"):
            normalized["location"] = "North"
        if not normalized.get("server_id"):
            normalized["server_id"] = "N-01"
        if not normalized.get("user_id"):
            normalized["user_id"] = "user_unknown"
        if not normalized.get("device_id"):
            normalized["device_id"] = "DEV-GENERIC-01"
        if not normalized.get("source_ip"):
            normalized["source_ip"] = "192.168.1.1"
        if not normalized.get("event_type"):
            normalized["event_type"] = "SYSTEM_INFO"
        if not normalized.get("login_status"):
            normalized["login_status"] = "N/A"
        if "failed_attempt_count" not in normalized:
            normalized["failed_attempt_count"] = 1 if normalized.get("login_status") == "FAILURE" else 0
        if "unusual_location" not in normalized:
            normalized["unusual_location"] = False
        if "unusual_time" not in normalized:
            normalized["unusual_time"] = False
        if "unknown_device" not in normalized:
            normalized["unknown_device"] = False
        if "account_verified" not in normalized:
            normalized["account_verified"] = True
        if not normalized.get("integrity_status"):
            normalized["integrity_status"] = "VERIFIED"
        if not normalized.get("raw_log"):
            normalized["raw_log"] = f"[{normalized['timestamp']}] {normalized['location']} {normalized['server_id']} {normalized['event_type']} user={normalized['user_id']} ip={normalized['source_ip']}"

        # Hash signature if missing
        if not normalized.get("hash_signature"):
            normalized["hash_signature"] = compute_log_hash(normalized)

        return normalized
