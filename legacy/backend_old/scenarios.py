"""
Predefined Scenario Generators for IT System Log Analyzer
Implements Scenarios A, B, C, D from the design specification along with Tamper and Continuous simulations.
"""

from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid

from backend.normalizer import LogNormalizer
from backend.integrity_engine import simulate_log_tampering


def generate_scenario_a() -> List[Dict[str, Any]]:
    """
    Scenario A — Low Risk:
    User attempts login at North location from same known device (DEV-WIN-9021).
    2 failed attempts followed by successful login. Normal user typo recovery.
    """
    now = datetime.now(timezone.utc)
    user = "user_u102"
    device = "DEV-WIN-9021"
    ip = "10.14.2.19"
    loc = "North"
    server = "N-01"

    events = [
        LogNormalizer.normalize_dict({
            "timestamp": (now - timedelta(minutes=6)).isoformat(),
            "location": loc,
            "server_id": server,
            "user_id": user,
            "device_id": device,
            "source_ip": ip,
            "event_type": "FAILED_LOGIN",
            "login_status": "FAILURE",
            "failed_attempt_count": 1,
            "unusual_location": False,
            "unusual_time": False,
            "unknown_device": False,
            "account_verified": True,
            "raw_log": f"pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost={ip} user={user}"
        }),
        LogNormalizer.normalize_dict({
            "timestamp": (now - timedelta(minutes=4)).isoformat(),
            "location": loc,
            "server_id": server,
            "user_id": user,
            "device_id": device,
            "source_ip": ip,
            "event_type": "FAILED_LOGIN",
            "login_status": "FAILURE",
            "failed_attempt_count": 2,
            "unusual_location": False,
            "unusual_time": False,
            "unknown_device": False,
            "account_verified": True,
            "raw_log": f"pam_unix(sshd:auth): authentication failure (attempt 2); rhost={ip} user={user}"
        }),
        LogNormalizer.normalize_dict({
            "timestamp": (now - timedelta(minutes=2)).isoformat(),
            "location": loc,
            "server_id": server,
            "user_id": user,
            "device_id": device,
            "source_ip": ip,
            "event_type": "SUCCESSFUL_LOGIN",
            "login_status": "SUCCESS",
            "failed_attempt_count": 0,
            "unusual_location": False,
            "unusual_time": False,
            "unknown_device": False,
            "account_verified": True,
            "raw_log": f"Accepted password for {user} from {ip} port 52310 ssh2: {device}"
        })
    ]
    return events


def generate_scenario_b() -> List[Dict[str, Any]]:
    """
    Scenario B — Medium Risk:
    Same user u102 at North location from same known device (DEV-WIN-9021).
    7 failed login attempts, then successful login. Suspicious repeated failures.
    """
    now = datetime.now(timezone.utc)
    user = "user_u102"
    device = "DEV-WIN-9021"
    ip = "10.14.2.19"
    loc = "North"
    server = "N-01"

    events = []
    # 7 failed attempts
    for i in range(1, 8):
        t = now - timedelta(minutes=15 - i)
        events.append(LogNormalizer.normalize_dict({
            "timestamp": t.isoformat(),
            "location": loc,
            "server_id": server,
            "user_id": user,
            "device_id": device,
            "source_ip": ip,
            "event_type": "FAILED_LOGIN",
            "login_status": "FAILURE",
            "failed_attempt_count": i,
            "unusual_location": False,
            "unusual_time": False,
            "unknown_device": False,
            "account_verified": True,
            "raw_log": f"Security Event 4625: An account failed to log on. Account: {user}, Attempt: {i}/7, Host: {device}"
        }))

    # Followed by success
    events.append(LogNormalizer.normalize_dict({
        "timestamp": (now - timedelta(minutes=7)).isoformat(),
        "location": loc,
        "server_id": server,
        "user_id": user,
        "device_id": device,
        "source_ip": ip,
        "event_type": "SUCCESSFUL_LOGIN",
        "login_status": "SUCCESS",
        "failed_attempt_count": 0,
        "unusual_location": False,
        "unusual_time": False,
        "unknown_device": False,
        "account_verified": True,
        "raw_log": f"Security Event 4624: An account was successfully logged on. Account: {user}, Host: {device}"
    }))

    return events


def generate_scenario_c() -> List[Dict[str, Any]]:
    """
    Scenario C — High Risk:
    Same account u102:
    North -> multiple failed logins.
    Then successful login from South (unusual location) using UNKNOWN device (DEV-UNKNOWN-88).
    """
    now = datetime.now(timezone.utc)
    user = "user_u102"

    events = [
        # North failed attempts
        LogNormalizer.normalize_dict({
            "timestamp": (now - timedelta(minutes=25)).isoformat(),
            "location": "North",
            "server_id": "N-01",
            "user_id": user,
            "device_id": "DEV-WIN-9021",
            "source_ip": "10.14.2.19",
            "event_type": "FAILED_LOGIN",
            "login_status": "FAILURE",
            "failed_attempt_count": 3,
            "unusual_location": False,
            "unusual_time": False,
            "unknown_device": False,
            "account_verified": True,
            "raw_log": f"SSH logon failure for {user} from 10.14.2.19: Bad password sequence (3 attempts)"
        }),
        LogNormalizer.normalize_dict({
            "timestamp": (now - timedelta(minutes=20)).isoformat(),
            "location": "North",
            "server_id": "N-02",
            "user_id": user,
            "device_id": "DEV-WIN-9021",
            "source_ip": "10.14.2.19",
            "event_type": "FAILED_LOGIN",
            "login_status": "FAILURE",
            "failed_attempt_count": 4,
            "unusual_location": False,
            "unusual_time": False,
            "unknown_device": False,
            "account_verified": True,
            "raw_log": f"Kerberos pre-authentication failure for {user} on N-02 (attempt 4)"
        }),
        # South successful login from unknown device & unusual location
        LogNormalizer.normalize_dict({
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "location": "South",
            "server_id": "S-01",
            "user_id": user,
            "device_id": "DEV-UNKNOWN-88",
            "source_ip": "198.51.100.42",
            "event_type": "SUCCESSFUL_LOGIN",
            "login_status": "SUCCESS",
            "failed_attempt_count": 0,
            "unusual_location": True,
            "unusual_time": False,
            "unknown_device": True,
            "account_verified": False,
            "raw_log": f"VPN Tunnel Established: User={user} RemoteIP=198.51.100.42 Endpoint=S-01 Device=DEV-UNKNOWN-88 [Unregistered Hardware]"
        })
    ]
    return events


def generate_scenario_d() -> List[Dict[str, Any]]:
    """
    Scenario D — Very High Risk (Cross-Location Distributed Attack Chain):
    Same account u102:
    10:00 AM — North -> 5 failed logins (N-01)
    10:05 AM — North -> Successful logon
    10:08 AM — South -> Same account accessed from unusual location + unknown device (S-01)
    10:12 AM — East -> Suspicious database file exfiltration / privilege escalation (E-02)
    All events occur within a compressed 12-minute window.
    """
    now = datetime.now(timezone.utc)
    user = "user_u102"

    events = [
        # Step 1: North failed attempts
        LogNormalizer.normalize_dict({
            "timestamp": (now - timedelta(minutes=14)).isoformat(),
            "location": "North",
            "server_id": "N-01",
            "user_id": user,
            "device_id": "DEV-WIN-9021",
            "source_ip": "10.14.2.19",
            "event_type": "FAILED_LOGIN",
            "login_status": "FAILURE",
            "failed_attempt_count": 5,
            "unusual_location": False,
            "unusual_time": False,
            "unknown_device": False,
            "account_verified": True,
            "raw_log": f"AuthAlert: 5 consecutive failed logon attempts for {user} on Domain Controller N-01"
        }),
        # Step 2: North logon
        LogNormalizer.normalize_dict({
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "location": "North",
            "server_id": "N-01",
            "user_id": user,
            "device_id": "DEV-WIN-9021",
            "source_ip": "10.14.2.19",
            "event_type": "SUCCESSFUL_LOGIN",
            "login_status": "SUCCESS",
            "failed_attempt_count": 0,
            "unusual_location": False,
            "unusual_time": False,
            "unknown_device": False,
            "account_verified": True,
            "raw_log": f"Domain auth accepted for {user} on N-01 after repeated failures"
        }),
        # Step 3: South anomalous login from unknown device & unusual location (Impossible Travel)
        LogNormalizer.normalize_dict({
            "timestamp": (now - timedelta(minutes=7)).isoformat(),
            "location": "South",
            "server_id": "S-01",
            "user_id": user,
            "device_id": "DEV-UNKNOWN-88",
            "source_ip": "198.51.100.42",
            "event_type": "SUCCESSFUL_LOGIN",
            "login_status": "SUCCESS",
            "failed_attempt_count": 0,
            "unusual_location": True,
            "unusual_time": False,
            "unknown_device": True,
            "account_verified": False,
            "raw_log": f"Remote SSH Session Opened: {user} logged in to S-01 (South) via unknown device DEV-UNKNOWN-88"
        }),
        # Step 4: East suspicious file & database exfiltration
        LogNormalizer.normalize_dict({
            "timestamp": (now - timedelta(minutes=2)).isoformat(),
            "location": "East",
            "server_id": "E-02",
            "user_id": user,
            "device_id": "DEV-UNKNOWN-88",
            "source_ip": "198.51.100.42",
            "event_type": "DATA_EXFILTRATION",
            "login_status": "SUCCESS",
            "failed_attempt_count": 0,
            "unusual_location": True,
            "unusual_time": True,
            "unknown_device": True,
            "account_verified": False,
            "target_resource": "/classified/tactical_deployments_2026.sql",
            "raw_log": f"DataAudit: Bulk transfer (4.2 GB) from Classified DB E-02 /tactical_deployments_2026.sql initiated by {user}"
        })
    ]
    return events


def generate_scenario_tamper() -> List[Dict[str, Any]]:
    """
    Demonstrates cryptographic log tampering detection:
    A legitimate log is created with HMAC-SHA256 signature, then maliciously altered.
    """
    now = datetime.now(timezone.utc)
    base_event = LogNormalizer.normalize_dict({
        "timestamp": now.isoformat(),
        "location": "West",
        "server_id": "W-01",
        "user_id": "user_u308",
        "device_id": "DEV-EAST-7721",
        "source_ip": "45.33.32.156",
        "event_type": "SUSPICIOUS_FILE_ACCESS",
        "login_status": "SUCCESS",
        "failed_attempt_count": 0,
        "unusual_location": True,
        "unusual_time": True,
        "unknown_device": True,
        "target_resource": "/etc/shadow",
        "raw_log": "Audit: /etc/shadow read by user_u308 from external IP 45.33.32.156"
    })

    # Malicious actor changes source_ip to 127.0.0.1 to disguise source
    tampered_event = simulate_log_tampering(base_event, "source_ip", "127.0.0.1")
    return [tampered_event]


def generate_random_normal_event(location: str = "North", server_id: str = "N-01") -> Dict[str, Any]:
    """Generates routine baseline background event."""
    users = ["user_u102", "user_u204", "user_u308", "admin_super"]
    user = users[hash(datetime.now().isoformat()) % len(users)]
    device = "DEV-WIN-9021" if location == "North" else "DEV-LAP-5512"

    return LogNormalizer.normalize_dict({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": location,
        "server_id": server_id,
        "user_id": user,
        "device_id": device,
        "source_ip": "10.14.2.19" if location == "North" else "10.22.4.11",
        "event_type": "SUCCESSFUL_LOGIN",
        "login_status": "SUCCESS",
        "failed_attempt_count": 0,
        "unusual_location": False,
        "unusual_time": False,
        "unknown_device": False,
        "account_verified": True,
        "raw_log": f"System Heartbeat / Auth check ok for {user} on {server_id}"
    })
