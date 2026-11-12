"""
CRPF Personnel Authentication and Account Management Engine
Handles credential verification, secure password hashing, account status (ACTIVE, TEMPORARILY_BLOCKED),
login risk evaluation, and expert notification dispatching.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.database import get_db_connection, DB_PATH
from backend.normalizer import LogNormalizer
from backend.identity_linker import IdentityLinker
from backend.risk_scorer import risk_scorer
from backend.correlation_engine import correlation_engine


def hash_password(password: str, salt: str = "CRPF_SEC_SALT_2026") -> str:
    """Computes SHA-256 hash of password with organizational salt."""
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


# Predefined example accounts for CRPF personnel
INITIAL_CRPF_ACCOUNTS = [
    {
        "force_id": "CRPF-90214",
        "user_id": "user_u102",
        "username": "maj_vikram",
        "full_name": "Major Vikram Rathore",
        "rank": "Commandant (Signals / IT Lead)",
        "password_plain": "Crpf@Signals2026",
        "home_location": "North",
        "authorized_locations": ["North"],
        "trusted_devices": ["DEV-WIN-9021", "DEV-MAC-4102"],
        "trusted_ips": ["10.14.2.19", "10.14.2.20"],
        "status": "ACTIVE"
    },
    {
        "force_id": "CRPF-55120",
        "user_id": "user_u204",
        "username": "insp_priya",
        "full_name": "Inspector Priya Sharma",
        "rank": "Logistics & Personnel Officer",
        "password_plain": "Priya#Logistics26",
        "home_location": "South",
        "authorized_locations": ["South"],
        "trusted_devices": ["DEV-LAP-5512"],
        "trusted_ips": ["10.22.4.11"],
        "status": "ACTIVE"
    },
    {
        "force_id": "CRPF-77218",
        "user_id": "user_u308",
        "username": "si_amit",
        "full_name": "Sub-Inspector Amit Verma",
        "rank": "East Sector Communications Officer",
        "password_plain": "Amit@SectorEast",
        "home_location": "East",
        "authorized_locations": ["East"],
        "trusted_devices": ["DEV-EAST-7721"],
        "trusted_ips": ["10.33.1.5"],
        "status": "ACTIVE"
    },
    {
        "force_id": "CRPF-00001",
        "user_id": "admin_super",
        "username": "hq_root",
        "full_name": "Director General IT / System Root",
        "rank": "Central IT Security Director",
        "password_plain": "CentralHQ#SecRoot99",
        "home_location": "North",
        "authorized_locations": ["North", "South", "East", "West"],
        "trusted_devices": ["DEV-HQ-SEC01"],
        "trusted_ips": ["10.14.1.1"],
        "status": "ACTIVE"
    }
]


class AuthManager:
    """Manages CRPF accounts, login authentication, and expert notification dispatch."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.identity_linker = IdentityLinker()
        self._init_tables()
        self._seed_accounts()

    def _init_tables(self):
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()

        # Accounts Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS crpf_accounts (
            force_id TEXT PRIMARY KEY,
            user_id TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            rank TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            home_location TEXT NOT NULL,
            authorized_locations TEXT NOT NULL,
            trusted_devices TEXT NOT NULL,
            trusted_ips TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            failed_login_count INTEGER DEFAULT 0,
            last_login_time TEXT,
            last_login_location TEXT,
            last_login_ip TEXT,
            last_login_device TEXT,
            block_reason TEXT,
            blocked_by TEXT,
            blocked_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)

        # Expert Notifications Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS expert_notifications (
            notification_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            force_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            incident_id TEXT,
            location TEXT NOT NULL,
            device_id TEXT NOT NULL,
            source_ip TEXT NOT NULL,
            status TEXT DEFAULT 'UNREAD',
            action_taken TEXT DEFAULT 'NONE',
            action_note TEXT
        );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notif_status ON expert_notifications(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notif_time ON expert_notifications(timestamp);")

        conn.commit()
        conn.close()

    def _seed_accounts(self):
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        for acc in INITIAL_CRPF_ACCOUNTS:
            pwd_hash = hash_password(acc["password_plain"])
            cursor.execute("""
            INSERT OR IGNORE INTO crpf_accounts (
                force_id, user_id, username, full_name, rank, password_hash,
                home_location, authorized_locations, trusted_devices, trusted_ips,
                status, failed_login_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """, (
                acc["force_id"],
                acc["user_id"],
                acc["username"],
                acc["full_name"],
                acc["rank"],
                pwd_hash,
                acc["home_location"],
                json.dumps(acc["authorized_locations"]),
                json.dumps(acc["trusted_devices"]),
                json.dumps(acc["trusted_ips"]),
                acc["status"],
                now,
                now
            ))

        conn.commit()
        conn.close()

    def get_account_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Finds account by Force ID, Username, or User ID."""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM crpf_accounts 
        WHERE force_id = ? OR username = ? OR user_id = ?
        """, (identifier.strip(), identifier.strip().lower(), identifier.strip().lower()))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        d["authorized_locations"] = json.loads(d["authorized_locations"])
        d["trusted_devices"] = json.loads(d["trusted_devices"])
        d["trusted_ips"] = json.loads(d["trusted_ips"])
        return d

    def get_all_accounts(self) -> List[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM crpf_accounts ORDER BY force_id ASC")
        rows = cursor.fetchall()
        conn.close()
        result = []
        for r in rows:
            d = dict(r)
            d["authorized_locations"] = json.loads(d["authorized_locations"])
            d["trusted_devices"] = json.loads(d["trusted_devices"])
            d["trusted_ips"] = json.loads(d["trusted_ips"])
            # Do not leak password hash in public list
            d.pop("password_hash", None)
            result.append(d)
        return result

    def set_account_status(self, force_id_or_user_id: str, new_status: str,
                           reason: str = "", expert_name: str = "SOC Security Lead") -> Dict[str, Any]:
        """
        Allows Security Experts to take precautionary containment:
        - TEMPORARILY_BLOCKED: Locks the account immediately across all regional portals.
        - ACTIVE: Restores access.
        """
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        if new_status == "TEMPORARILY_BLOCKED":
            cursor.execute("""
            UPDATE crpf_accounts 
            SET status = ?, block_reason = ?, blocked_by = ?, blocked_at = ?, updated_at = ?
            WHERE force_id = ? OR user_id = ?
            """, (new_status, reason, expert_name, now, now, force_id_or_user_id, force_id_or_user_id))
        else:
            cursor.execute("""
            UPDATE crpf_accounts 
            SET status = ?, block_reason = NULL, blocked_by = NULL, blocked_at = NULL, failed_login_count = 0, updated_at = ?
            WHERE force_id = ? OR user_id = ?
            """, (new_status, now, force_id_or_user_id, force_id_or_user_id))

        conn.commit()
        conn.close()

        # Update any related pending notification status
        self._record_notification_action(force_id_or_user_id, new_status, reason, expert_name)

        return self.get_account_by_identifier(force_id_or_user_id) or {"status": new_status}

    def authenticate_crpf_login(
        self,
        identifier: str,
        password_input: str,
        location: str = "North",
        server_id: str = "N-01",
        device_id: str = "DEV-WIN-9021",
        source_ip: str = "10.14.2.19"
    ) -> Dict[str, Any]:
        """
        Central CRPF Authentication Flow integrated with Log Analyzer:
        1. Validates credentials and account status (checks for TEMPORARILY_BLOCKED).
        2. Normalizes login event and generates immutable HMAC-SHA256 signed log.
        3. Runs real-time Identity Linking, Velocity Analysis, and Risk Scoring.
        4. If High or Very High risk detected, dispatches real-time Expert Notification.
        """
        now = datetime.now(timezone.utc).isoformat()
        account = self.get_account_by_identifier(identifier)

        # Handle Unknown Account / Non-existent User
        if not account:
            event = LogNormalizer.normalize_dict({
                "timestamp": now,
                "location": location,
                "server_id": server_id,
                "user_id": identifier.lower(),
                "account": identifier,
                "device_id": device_id,
                "source_ip": source_ip,
                "event_type": "FAILED_LOGIN",
                "login_status": "FAILURE",
                "failed_attempt_count": 1,
                "unusual_location": True,
                "unknown_device": True,
                "account_verified": False,
                "raw_log": f"CRPF SSO Auth Rejected: Non-existent Personnel ID {identifier} from {location} ({device_id} @ {source_ip})"
            })

            # Evaluate Risk for non-existent account probing
            context = {"cross_location_count": 1, "is_unusual_location": True, "is_unknown_device": True}
            risk_eval = risk_scorer.calculate_risk([event], context)

            return {
                "authenticated": False,
                "auth_code": "INVALID_CREDENTIALS",
                "message": "Authentication Denied: Invalid Force ID / User ID or Password.",
                "event": event,
                "risk_assessment": risk_eval.to_dict(),
                "account": None
            }

        # Check Account Block Status (Precautionary Enforcement)
        if account["status"] == "TEMPORARILY_BLOCKED":
            event = LogNormalizer.normalize_dict({
                "timestamp": now,
                "location": location,
                "server_id": server_id,
                "user_id": account["user_id"],
                "account": account["force_id"],
                "device_id": device_id,
                "source_ip": source_ip,
                "event_type": "FAILED_LOGIN",
                "login_status": "BLOCKED",
                "failed_attempt_count": account["failed_login_count"] + 1,
                "unusual_location": location != account["home_location"],
                "unknown_device": device_id not in account["trusted_devices"],
                "raw_log": f"CRPF SSO Logon Blocked: Account {account['force_id']} ({account['full_name']}) is TEMPORARILY_BLOCKED. Attempt from {location} ({device_id})."
            })

            # Create notification for attempted access on blocked account
            self.create_expert_notification(
                severity="WARNING",
                title=f"🛑 Blocked Account Login Attempt ({account['force_id']})",
                message=f"Login attempt on locked account {account['full_name']} from {location} ({device_id} @ {source_ip}). Reason: {account.get('block_reason', 'Security Precaution')}",
                force_id=account["force_id"],
                user_id=account["user_id"],
                risk_score=75,
                risk_level="HIGH",
                location=location,
                device_id=device_id,
                source_ip=source_ip
            )

            return {
                "authenticated": False,
                "auth_code": "ACCOUNT_BLOCKED",
                "message": f"ACCESS DENIED: Account {account['force_id']} is TEMPORARILY BLOCKED by SOC Defense Command. Reason: {account.get('block_reason', 'Suspicious activity under review')}",
                "event": event,
                "risk_assessment": {
                    "overall_score": 75,
                    "risk_level": "HIGH",
                    "reasons": ["Account is currently under administrative lock / precaution."]
                },
                "account": {
                    "force_id": account["force_id"],
                    "user_id": account["user_id"],
                    "full_name": account["full_name"],
                    "rank": account["rank"],
                    "status": account["status"],
                    "block_reason": account.get("block_reason")
                }
            }

        # Verify Password Hash
        input_hash = hash_password(password_input)
        is_password_valid = (input_hash == account["password_hash"])

        # Determine Contextual Anomalies
        is_unusual_location = location not in account["authorized_locations"]
        is_unknown_device = device_id not in account["trusted_devices"]

        # Check Impossible Travel vs Last Login
        impossible_travel = False
        travel_details = None
        if account.get("last_login_time") and account.get("last_login_location"):
            if account["last_login_location"] != location:
                prev_ev = {
                    "timestamp": account["last_login_time"],
                    "location": account["last_login_location"],
                    "user_id": account["user_id"]
                }
                curr_ev = {
                    "timestamp": now,
                    "location": location,
                    "user_id": account["user_id"]
                }
                id_eval = self.identity_linker.assess_identity_context(curr_ev, [prev_ev])
                if id_eval.get("impossible_travel"):
                    impossible_travel = True
                    travel_details = id_eval.get("travel_details")

        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()

        if is_password_valid:
            # Successful Authentication
            event = LogNormalizer.normalize_dict({
                "timestamp": now,
                "location": location,
                "server_id": server_id,
                "user_id": account["user_id"],
                "account": account["force_id"],
                "device_id": device_id,
                "source_ip": source_ip,
                "event_type": "SUCCESSFUL_LOGIN",
                "login_status": "SUCCESS",
                "failed_attempt_count": 0,
                "unusual_location": is_unusual_location,
                "unknown_device": is_unknown_device,
                "account_verified": True,
                "raw_log": f"CRPF SSO Auth Succeeded: Force ID {account['force_id']} ({account['full_name']}) at {location} [{server_id}] Device={device_id} IP={source_ip}"
            })

            # Update account telemetry
            cursor.execute("""
            UPDATE crpf_accounts 
            SET failed_login_count = 0, last_login_time = ?, last_login_location = ?,
                last_login_ip = ?, last_login_device = ?, updated_at = ?
            WHERE force_id = ?
            """, (now, location, source_ip, device_id, now, account["force_id"]))
            conn.commit()

        else:
            # Failed Authentication
            new_failed_cnt = account["failed_login_count"] + 1
            event = LogNormalizer.normalize_dict({
                "timestamp": now,
                "location": location,
                "server_id": server_id,
                "user_id": account["user_id"],
                "account": account["force_id"],
                "device_id": device_id,
                "source_ip": source_ip,
                "event_type": "FAILED_LOGIN",
                "login_status": "FAILURE",
                "failed_attempt_count": new_failed_cnt,
                "unusual_location": is_unusual_location,
                "unknown_device": is_unknown_device,
                "account_verified": True,
                "raw_log": f"CRPF SSO Auth Failure (Attempt {new_failed_cnt}): Bad credentials for {account['force_id']} ({account['full_name']}) from {location} [{server_id}] Device={device_id}"
            })

            # Increment failed count
            cursor.execute("""
            UPDATE crpf_accounts 
            SET failed_login_count = ?, updated_at = ?
            WHERE force_id = ?
            """, (new_failed_cnt, now, account["force_id"]))
            conn.commit()

        conn.close()

        # Calculate Explainable Risk Score
        context = {
            "cross_location_count": 2 if is_unusual_location else 1,
            "is_unusual_location": is_unusual_location,
            "is_unknown_device": is_unknown_device,
            "impossible_travel": impossible_travel,
            "travel_details": travel_details,
            "success_after_failures": is_password_valid and account["failed_login_count"] >= 3
        }
        risk_eval = risk_scorer.calculate_risk([event], context)

        # Dispatch Expert Notification if Risk is Elevated
        notification_dispatched = False
        if risk_eval.overall_score >= 60 or not is_password_valid and is_unusual_location:
            notif_sev = "CRITICAL" if risk_eval.risk_level == "VERY_HIGH" else "WARNING"
            notif_title = f"🚨 {risk_eval.risk_level} Risk Login Activity: {account['full_name']} ({account['force_id']})"
            notif_msg = (
                f"Anomalous login activity detected for {account['rank']} {account['full_name']}.\n"
                f"Location: {location} (Home: {account['home_location']}) | Device: {device_id} | IP: {source_ip}\n"
                f"Risk Score: {risk_eval.overall_score}/100 ({risk_eval.risk_level})\n"
                f"Reasons: {'; '.join(risk_eval.reasons)}"
            )

            self.create_expert_notification(
                severity=notif_sev,
                title=notif_title,
                message=notif_msg,
                force_id=account["force_id"],
                user_id=account["user_id"],
                risk_score=risk_eval.overall_score,
                risk_level=risk_eval.risk_level,
                location=location,
                device_id=device_id,
                source_ip=source_ip
            )
            notification_dispatched = True

        return {
            "authenticated": is_password_valid,
            "auth_code": "SUCCESS" if is_password_valid else "INVALID_CREDENTIALS",
            "message": "Authentication Successful. Access Granted." if is_password_valid else "Authentication Denied: Invalid Password.",
            "event": event,
            "risk_assessment": risk_eval.to_dict(),
            "notification_dispatched": notification_dispatched,
            "account": {
                "force_id": account["force_id"],
                "user_id": account["user_id"],
                "full_name": account["full_name"],
                "rank": account["rank"],
                "home_location": account["home_location"],
                "status": account["status"]
            }
        }

    def create_expert_notification(
        self,
        severity: str,
        title: str,
        message: str,
        force_id: str,
        user_id: str,
        risk_score: int,
        risk_level: str,
        location: str,
        device_id: str,
        source_ip: str,
        incident_id: Optional[str] = None
    ) -> str:
        """Saves a high-priority alert in the Expert Notifications table."""
        notif_id = f"NOTIF-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO expert_notifications (
            notification_id, timestamp, severity, title, message, force_id,
            user_id, risk_score, risk_level, incident_id, location, device_id,
            source_ip, status, action_taken
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'UNREAD', 'NONE')
        """, (
            notif_id, now, severity, title, message, force_id,
            user_id, risk_score, risk_level, incident_id, location, device_id,
            source_ip
        ))
        conn.commit()
        conn.close()
        return notif_id

    def get_expert_notifications(self, limit: int = 50, unread_only: bool = False) -> List[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        query = "SELECT * FROM expert_notifications WHERE 1=1"
        params = []
        if unread_only:
            query += " AND status = 'UNREAD'"
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _record_notification_action(self, force_id_or_user_id: str, new_status: str, reason: str, expert_name: str):
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        action_name = "BLOCKED_ACCOUNT" if new_status == "TEMPORARILY_BLOCKED" else "RESTORED_ACCOUNT"
        cursor.execute("""
        UPDATE expert_notifications 
        SET status = 'ACTIONED', action_taken = ?, action_note = ?
        WHERE (force_id = ? OR user_id = ?) AND status != 'ACTIONED'
        """, (action_name, f"{action_name} by {expert_name}: {reason}", force_id_or_user_id, force_id_or_user_id))
        conn.commit()
        conn.close()


# Global singleton instance
auth_manager = AuthManager()
