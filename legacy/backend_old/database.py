"""
Database Persistence Layer for IT System Log Analyzer
Uses SQLite for robust, portable, zero-dependency storage.
"""

import sqlite3
import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "log_analyzer.db")


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Initialize database tables and indices"""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Events Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        location TEXT NOT NULL,
        server_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        account TEXT,
        device_id TEXT NOT NULL,
        source_ip TEXT NOT NULL,
        event_type TEXT NOT NULL,
        login_status TEXT NOT NULL,
        failed_attempt_count INTEGER DEFAULT 0,
        unusual_location INTEGER DEFAULT 0,
        unusual_time INTEGER DEFAULT 0,
        unknown_device INTEGER DEFAULT 0,
        account_verified INTEGER DEFAULT 1,
        integrity_status TEXT DEFAULT 'VERIFIED',
        hash_signature TEXT,
        raw_log TEXT,
        target_resource TEXT,
        session_id TEXT,
        metadata TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # Indices on events
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_location ON events(location);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);")

    # Incidents Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        incident_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        user_id TEXT NOT NULL,
        primary_location TEXT NOT NULL,
        involved_locations TEXT NOT NULL,
        involved_servers TEXT NOT NULL,
        involved_devices TEXT NOT NULL,
        involved_ips TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        event_count INTEGER DEFAULT 0,
        event_ids TEXT NOT NULL,
        overall_score INTEGER NOT NULL,
        risk_level TEXT NOT NULL,
        confidence REAL NOT NULL,
        risk_assessment_json TEXT NOT NULL,
        timeline_json TEXT NOT NULL,
        attack_graph_json TEXT NOT NULL,
        scenario_tag TEXT,
        status TEXT DEFAULT 'OPEN',
        assigned_analyst TEXT DEFAULT 'SOC Analyst 1',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_risk ON incidents(risk_level);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_user ON incidents(user_id);")

    # Agents Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        location TEXT PRIMARY KEY,
        agent_id TEXT NOT NULL,
        status TEXT NOT NULL,
        ip_address TEXT NOT NULL,
        server_ids TEXT NOT NULL,
        total_logs_collected INTEGER DEFAULT 0,
        buffered_logs_count INTEGER DEFAULT 0,
        last_heartbeat TEXT NOT NULL
    );
    """)

    # System Configuration Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    # Insert default config if empty
    default_configs = {
        "threshold_low": "30",
        "threshold_medium": "60",
        "threshold_high": "80",
        "correlation_window_minutes": "60",
        "auto_alert_level": "HIGH",
        "org_name": "Central Reserve Police Force (CRPF) IT Command"
    }

    for k, v in default_configs.items():
        cursor.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES (?, ?);", (k, v))

    conn.commit()
    conn.close()


class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def insert_event(self, event: Dict[str, Any]) -> None:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
        INSERT OR REPLACE INTO events (
            event_id, timestamp, location, server_id, user_id, account,
            device_id, source_ip, event_type, login_status, failed_attempt_count,
            unusual_location, unusual_time, unknown_device, account_verified,
            integrity_status, hash_signature, raw_log, target_resource, session_id,
            metadata, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.get("event_id"),
            event.get("timestamp", now),
            event.get("location", "North"),
            event.get("server_id", "N-01"),
            event.get("user_id", "unknown"),
            event.get("account", ""),
            event.get("device_id", "unknown"),
            event.get("source_ip", "0.0.0.0"),
            event.get("event_type", "UNKNOWN"),
            event.get("login_status", "N/A"),
            int(event.get("failed_attempt_count", 0)),
            1 if event.get("unusual_location") else 0,
            1 if event.get("unusual_time") else 0,
            1 if event.get("unknown_device") else 0,
            1 if event.get("account_verified", True) else 0,
            event.get("integrity_status", "VERIFIED"),
            event.get("hash_signature", ""),
            event.get("raw_log", ""),
            event.get("target_resource", ""),
            event.get("session_id", ""),
            json.dumps(event.get("metadata", {})),
            now
        ))
        conn.commit()
        conn.close()

    def insert_events_batch(self, events: List[Dict[str, Any]]) -> None:
        if not events:
            return
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (
                e.get("event_id"),
                e.get("timestamp", now),
                e.get("location", "North"),
                e.get("server_id", "N-01"),
                e.get("user_id", "unknown"),
                e.get("account", ""),
                e.get("device_id", "unknown"),
                e.get("source_ip", "0.0.0.0"),
                e.get("event_type", "UNKNOWN"),
                e.get("login_status", "N/A"),
                int(e.get("failed_attempt_count", 0)),
                1 if e.get("unusual_location") else 0,
                1 if e.get("unusual_time") else 0,
                1 if e.get("unknown_device") else 0,
                1 if e.get("account_verified", True) else 0,
                e.get("integrity_status", "VERIFIED"),
                e.get("hash_signature", ""),
                e.get("raw_log", ""),
                e.get("target_resource", ""),
                e.get("session_id", ""),
                json.dumps(e.get("metadata", {})),
                now
            )
            for e in events
        ]
        cursor.executemany("""
        INSERT OR REPLACE INTO events (
            event_id, timestamp, location, server_id, user_id, account,
            device_id, source_ip, event_type, login_status, failed_attempt_count,
            unusual_location, unusual_time, unknown_device, account_verified,
            integrity_status, hash_signature, raw_log, target_resource, session_id,
            metadata, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        conn.close()

    def get_events(self, limit: int = 100, offset: int = 0, location: Optional[str] = None,
                   user_id: Optional[str] = None, event_type: Optional[str] = None,
                   integrity_status: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        query = "SELECT * FROM events WHERE 1=1"
        params = []

        if location:
            query += " AND location = ?"
            params.append(location)
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if integrity_status:
            query += " AND integrity_status = ?"
            params.append(integrity_status)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["unusual_location"] = bool(d["unusual_location"])
            d["unusual_time"] = bool(d["unusual_time"])
            d["unknown_device"] = bool(d["unknown_device"])
            d["account_verified"] = bool(d["account_verified"])
            if d.get("metadata"):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except Exception:
                    d["metadata"] = {}
            result.append(d)
        conn.close()
        return result

    def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        d["unusual_location"] = bool(d["unusual_location"])
        d["unusual_time"] = bool(d["unusual_time"])
        d["unknown_device"] = bool(d["unknown_device"])
        d["account_verified"] = bool(d["account_verified"])
        if d.get("metadata"):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except Exception:
                d["metadata"] = {}
        return d

    def update_event_integrity(self, event_id: str, integrity_status: str, raw_log: Optional[str] = None) -> bool:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        if raw_log is not None:
            cursor.execute("UPDATE events SET integrity_status = ?, raw_log = ? WHERE event_id = ?",
                           (integrity_status, raw_log, event_id))
        else:
            cursor.execute("UPDATE events SET integrity_status = ? WHERE event_id = ?",
                           (integrity_status, event_id))
        conn.commit()
        affected = cursor.rowcount > 0
        conn.close()
        return affected

    def insert_incident(self, incident_dict: Dict[str, Any]) -> None:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()

        risk = incident_dict.get("risk_assessment") or {}
        overall_score = risk.get("overall_score", 0)
        risk_level = risk.get("risk_level", "LOW")
        confidence = risk.get("confidence", 1.0)

        cursor.execute("""
        INSERT OR REPLACE INTO incidents (
            incident_id, title, user_id, primary_location, involved_locations,
            involved_servers, involved_devices, involved_ips, start_time, end_time,
            event_count, event_ids, overall_score, risk_level, confidence,
            risk_assessment_json, timeline_json, attack_graph_json, scenario_tag,
            status, assigned_analyst, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            incident_dict.get("incident_id"),
            incident_dict.get("title", "Correlated Cross-Location Incident"),
            incident_dict.get("user_id", "unknown"),
            incident_dict.get("primary_location", "North"),
            json.dumps(incident_dict.get("involved_locations", [])),
            json.dumps(incident_dict.get("involved_servers", [])),
            json.dumps(incident_dict.get("involved_devices", [])),
            json.dumps(incident_dict.get("involved_ips", [])),
            incident_dict.get("start_time", now),
            incident_dict.get("end_time", now),
            incident_dict.get("event_count", 0),
            json.dumps(incident_dict.get("event_ids", [])),
            overall_score,
            risk_level,
            confidence,
            json.dumps(risk),
            json.dumps(incident_dict.get("timeline", [])),
            json.dumps(incident_dict.get("attack_graph", {})),
            incident_dict.get("scenario_tag", ""),
            incident_dict.get("status", "OPEN"),
            incident_dict.get("assigned_analyst", "SOC Analyst 1"),
            now,
            now
        ))
        conn.commit()
        conn.close()

    def get_incidents(self, limit: int = 50, risk_level: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        query = "SELECT * FROM incidents WHERE 1=1"
        params = []
        if risk_level:
            query += " AND risk_level = ?"
            params.append(risk_level)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY overall_score DESC, updated_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["involved_locations"] = json.loads(d["involved_locations"])
            d["involved_servers"] = json.loads(d["involved_servers"])
            d["involved_devices"] = json.loads(d["involved_devices"])
            d["involved_ips"] = json.loads(d["involved_ips"])
            d["event_ids"] = json.loads(d["event_ids"])
            d["risk_assessment"] = json.loads(d["risk_assessment_json"])
            d["timeline"] = json.loads(d["timeline_json"])
            d["attack_graph"] = json.loads(d["attack_graph_json"])
            result.append(d)
        conn.close()
        return result

    def get_incident_by_id(self, incident_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        d["involved_locations"] = json.loads(d["involved_locations"])
        d["involved_servers"] = json.loads(d["involved_servers"])
        d["involved_devices"] = json.loads(d["involved_devices"])
        d["involved_ips"] = json.loads(d["involved_ips"])
        d["event_ids"] = json.loads(d["event_ids"])
        d["risk_assessment"] = json.loads(d["risk_assessment_json"])
        d["timeline"] = json.loads(d["timeline_json"])
        d["attack_graph"] = json.loads(d["attack_graph_json"])
        return d

    def update_incident_status(self, incident_id: str, status: str, analyst: Optional[str] = None) -> bool:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        if analyst:
            cursor.execute("UPDATE incidents SET status = ?, assigned_analyst = ?, updated_at = ? WHERE incident_id = ?",
                           (status, analyst, now, incident_id))
        else:
            cursor.execute("UPDATE incidents SET status = ?, updated_at = ? WHERE incident_id = ?",
                           (status, now, incident_id))
        conn.commit()
        affected = cursor.rowcount > 0
        conn.close()
        return affected

    def update_agent_status(self, location: str, status: str, buffered_count: int = 0) -> None:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
        UPDATE agents SET status = ?, buffered_logs_count = ?, last_heartbeat = ?
        WHERE location = ?
        """, (status, buffered_count, now, location))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict[str, Any]:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM events")
        total_events = cursor.fetchone()[0]

        cursor.execute("SELECT location, COUNT(*) FROM events GROUP BY location")
        location_counts = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) FROM incidents")
        total_incidents = cursor.fetchone()[0]

        cursor.execute("SELECT risk_level, COUNT(*) FROM incidents GROUP BY risk_level")
        risk_distribution = {r[0]: r[1] for r in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) FROM events WHERE integrity_status = 'TAMPERED'")
        tampered_count = cursor.fetchone()[0]

        cursor.execute("SELECT location, status, buffered_logs_count FROM agents")
        agents_data = [dict(r) for r in cursor.fetchall()]

        conn.close()
        return {
            "total_events": total_events,
            "location_counts": location_counts,
            "total_incidents": total_incidents,
            "risk_distribution": risk_distribution,
            "tampered_count": tampered_count,
            "agents": agents_data
        }

    def clear_all(self) -> None:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM events;")
        cursor.execute("DELETE FROM incidents;")
        cursor.execute("UPDATE agents SET total_logs_collected = 0, buffered_logs_count = 0;")
        conn.commit()
        conn.close()
