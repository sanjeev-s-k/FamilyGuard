"""
Central Threat Intelligence & Log Analyzer REST API Server
Built with zero external dependencies using Python's standard library.
Multi-threaded HTTP Server providing JSON REST APIs and frontend static asset delivery.
"""

import sys
import os
import json
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Dict, Any, Optional

# Ensure project root is in python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.database import DatabaseManager, DB_PATH
from backend.normalizer import LogNormalizer
from backend.integrity_engine import verify_log_integrity, simulate_log_tampering
from backend.agent_simulator import AgentManager
from backend.correlation_engine import correlation_engine
from backend.ml_engine import ml_classifier
from backend.scenarios import (
    generate_scenario_a, generate_scenario_b, generate_scenario_c,
    generate_scenario_d, generate_scenario_tamper, generate_random_normal_event
)
from backend.auth_manager import auth_manager

FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
db_manager = DatabaseManager(DB_PATH)
agent_manager = AgentManager(db_manager)


def seed_initial_demo_data():
    """Seeds baseline data if database is fresh"""
    stats = db_manager.get_stats()
    if stats["total_events"] == 0:
        print("[*] Fresh database detected. Seeding initial baseline telemetry...")
        # Ingest baseline events
        sc_d = generate_scenario_d()
        for e in sc_d:
            db_manager.insert_event(e)

        sc_c = generate_scenario_c()
        for e in sc_c:
            db_manager.insert_event(e)

        sc_a = generate_scenario_a()
        for e in sc_a:
            db_manager.insert_event(e)

        # Correlate and generate initial incidents
        inc_d = correlation_engine.correlate_user_events(sc_d, scenario_tag="SCENARIO_D")
        db_manager.insert_incident(inc_d.to_dict())

        inc_c = correlation_engine.correlate_user_events(sc_c, scenario_tag="SCENARIO_C")
        db_manager.insert_incident(inc_c.to_dict())

        inc_a = correlation_engine.correlate_user_events(sc_a, scenario_tag="SCENARIO_A")
        db_manager.insert_incident(inc_a.to_dict())
        print("[+] Initial baseline data successfully seeded.")


class ThreatAnalyzerHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def _send_json(self, data: Any, status_code: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                raw_body = self.rfile.read(content_length).decode("utf-8")
                return json.loads(raw_body)
        except Exception as ex:
            print(f"[!] Error parsing JSON body: {ex}")
        return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Health check
        if path == "/api/health":
            self._send_json({"status": "ONLINE", "service": "IT System Log Analyzer Core", "version": "1.0.0"})
            return

        # System stats
        if path == "/api/stats":
            stats = db_manager.get_stats()
            stats["agent_details"] = agent_manager.get_all_agents()
            self._send_json(stats)
            return

        # Log Events list
        if path == "/api/events":
            limit = int(query.get("limit", [100])[0])
            offset = int(query.get("offset", [0])[0])
            location = query.get("location", [None])[0]
            user_id = query.get("user_id", [None])[0]
            event_type = query.get("event_type", [None])[0]
            integrity_status = query.get("integrity_status", [None])[0]

            events = db_manager.get_events(
                limit=limit, offset=offset, location=location,
                user_id=user_id, event_type=event_type, integrity_status=integrity_status
            )
            self._send_json({"total": len(events), "events": events})
            return

        # Single Event
        if path.startswith("/api/events/") and not path.endswith("/verify") and not path.endswith("/tamper"):
            event_id = path.split("/")[3]
            ev = db_manager.get_event_by_id(event_id)
            if ev:
                is_valid, _, msg = verify_log_integrity(ev)
                ev["integrity_verification"] = {"is_valid": is_valid, "message": msg}
                self._send_json(ev)
            else:
                self._send_json({"error": "Event not found"}, status_code=404)
            return

        # Correlated Incidents list
        if path == "/api/incidents":
            risk_level = query.get("risk_level", [None])[0]
            status = query.get("status", [None])[0]
            limit = int(query.get("limit", [50])[0])
            incidents = db_manager.get_incidents(limit=limit, risk_level=risk_level, status=status)
            self._send_json({"total": len(incidents), "incidents": incidents})
            return

        # Single Incident
        if path.startswith("/api/incidents/"):
            inc_id = path.split("/")[3]
            inc = db_manager.get_incident_by_id(inc_id)
            if inc:
                self._send_json(inc)
            else:
                self._send_json({"error": "Incident not found"}, status_code=404)
            return

        # Agents list
        if path == "/api/agents":
            self._send_json({"agents": agent_manager.get_all_agents()})
            return

        # ML metrics
        if path == "/api/ml/metrics":
            self._send_json(ml_classifier.metrics)
            return

        # CRPF Accounts list
        if path == "/api/auth/accounts":
            accounts = auth_manager.get_all_accounts()
            self._send_json({"total": len(accounts), "accounts": accounts})
            return

        # Expert Notifications list
        if path == "/api/notifications":
            unread_only = query.get("unread", ["false"])[0].lower() == "true"
            notifs = auth_manager.get_expert_notifications(limit=50, unread_only=unread_only)
            self._send_json({"total": len(notifs), "notifications": notifs})
            return

        # Default static file handling
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()

        # Ingest Log via Agent
        if path == "/api/events":
            location = body.get("location", "North")
            raw_log = body.get("raw_log") or body.get("event")
            server_id = body.get("server_id", "N-01")

            result = agent_manager.collect_log(location, raw_log or body, server_id=server_id)
            self._send_json(result)
            return

        # Tamper Log (Lab simulation)
        if path.startswith("/api/events/") and path.endswith("/tamper"):
            parts = path.split("/")
            event_id = parts[3]
            field_to_alter = body.get("field", "source_ip")
            new_value = body.get("value", "127.0.0.1")

            ev = db_manager.get_event_by_id(event_id)
            if not ev:
                self._send_json({"error": "Event not found"}, status_code=404)
                return

            tampered = simulate_log_tampering(ev, field_to_alter, new_value)
            db_manager.update_event_integrity(event_id, "TAMPERED", tampered["raw_log"])

            # Verify and explain discrepancy
            is_valid, calc_hash, explanation = verify_log_integrity(tampered)

            self._send_json({
                "status": "TAMPERED_SIMULATION_EXECUTED",
                "event_id": event_id,
                "field_altered": field_to_alter,
                "new_value": new_value,
                "original_hash": tampered.get("hash_signature"),
                "recalculated_hash": calc_hash,
                "is_valid": is_valid,
                "explanation": explanation
            })
            return

        # Verify Log Integrity
        if path.startswith("/api/events/") and path.endswith("/verify"):
            parts = path.split("/")
            event_id = parts[3]
            ev = db_manager.get_event_by_id(event_id)
            if not ev:
                self._send_json({"error": "Event not found"}, status_code=404)
                return

            is_valid, calc_hash, explanation = verify_log_integrity(ev)
            self._send_json({
                "event_id": event_id,
                "recorded_hash": ev.get("hash_signature"),
                "calculated_hash": calc_hash,
                "is_valid": is_valid,
                "integrity_status": "VERIFIED" if is_valid else "TAMPERED",
                "explanation": explanation
            })
            return

        # Toggle Agent Status (Online / Offline)
        if path.startswith("/api/agents/") and path.endswith("/status"):
            parts = path.split("/")
            location = parts[3]
            new_status = body.get("status", "ONLINE")
            updated = agent_manager.set_agent_status(location, new_status)
            self._send_json({"status": "SUCCESS", "agent": updated})
            return

        # Sync Agent Buffer
        if path.startswith("/api/agents/") and path.endswith("/sync"):
            parts = path.split("/")
            location = parts[3]
            res = agent_manager.sync_agent_buffer(location)
            self._send_json(res)
            return

        # Trigger Cross-Location Threat Correlation on recent events
        if path == "/api/correlate":
            user_id = body.get("user_id")
            events = db_manager.get_events(limit=50, user_id=user_id)
            if not events:
                self._send_json({"error": "No events found to correlate"}, status_code=400)
                return

            incident = correlation_engine.correlate_user_events(events, scenario_tag=body.get("scenario_tag", "MANUAL"))
            db_manager.insert_incident(incident.to_dict())
            self._send_json({
                "status": "CORRELATION_COMPLETED",
                "incident": incident.to_dict()
            })
            return

        # Update Incident Status
        if path.startswith("/api/incidents/") and path.endswith("/status"):
            parts = path.split("/")
            incident_id = parts[3]
            new_status = body.get("status", "INVESTIGATING")
            analyst = body.get("analyst", "SOC Analyst 1")
            ok = db_manager.update_incident_status(incident_id, new_status, analyst)
            self._send_json({"success": ok, "incident_id": incident_id, "status": new_status})
            return

        # Run Scenario Presets (Scenario A, B, C, D, Tamper, Random)
        if path == "/api/scenarios/run":
            scenario_name = body.get("scenario", "SCENARIO_A").upper()

            if scenario_name == "SCENARIO_A":
                events = generate_scenario_a()
                title_tag = "Scenario A — Low Risk (Normal Typo Recovery)"
            elif scenario_name == "SCENARIO_B":
                events = generate_scenario_b()
                title_tag = "Scenario B — Medium Risk (Repeated Auth Failures)"
            elif scenario_name == "SCENARIO_C":
                events = generate_scenario_c()
                title_tag = "Scenario C — High Risk (Unknown Device & Location)"
            elif scenario_name == "SCENARIO_D":
                events = generate_scenario_d()
                title_tag = "Scenario D — Very High Risk (Cross-Location Attack Chain)"
            elif scenario_name == "TAMPER":
                events = generate_scenario_tamper()
                title_tag = "Cryptographic Tamper Attack Simulation"
            elif scenario_name == "RANDOM_NORMAL":
                loc = body.get("location", "North")
                srv = body.get("server_id", "N-01")
                events = [generate_random_normal_event(loc, srv)]
                title_tag = "Routine Background Telemetry"
            else:
                self._send_json({"error": f"Unknown scenario preset: {scenario_name}"}, status_code=400)
                return

            # Ingest events to DB
            for e in events:
                db_manager.insert_event(e)

            # Correlate immediately if not routine single log
            if scenario_name != "RANDOM_NORMAL":
                incident = correlation_engine.correlate_user_events(events, scenario_tag=scenario_name)
                db_manager.insert_incident(incident.to_dict())
                inc_dict = incident.to_dict()
            else:
                inc_dict = None

            self._send_json({
                "status": "SCENARIO_EXECUTED",
                "scenario": scenario_name,
                "title": title_tag,
                "events_created": len(events),
                "incident": inc_dict
            })
            return

        # ML Prediction on custom inputs
        if path == "/api/ml/predict":
            pred = ml_classifier.predict(body, body.get("context", {}))
            self._send_json(pred)
            return

        # ML Retrain
        if path == "/api/ml/retrain":
            ml_classifier._generate_dataset_and_train()
            self._send_json({"status": "RETRAIN_COMPLETED", "metrics": ml_classifier.metrics})
            return

        # CRPF Login Authentication
        if path == "/api/auth/login":
            identifier = body.get("identifier", "")
            password = body.get("password", "")
            location = body.get("location", "North")
            server_id = body.get("server_id", "N-01")
            device_id = body.get("device_id", "DEV-WIN-9021")
            source_ip = body.get("source_ip", "10.14.2.19")

            auth_result = auth_manager.authenticate_crpf_login(
                identifier=identifier,
                password_input=password,
                location=location,
                server_id=server_id,
                device_id=device_id,
                source_ip=source_ip
            )

            # Ingest the generated login log into DB
            if auth_result.get("event"):
                db_manager.insert_event(auth_result["event"])

            # If risk is elevated, correlate immediately into incidents
            if auth_result.get("risk_assessment", {}).get("overall_score", 0) >= 50 or auth_result.get("auth_code") == "ACCOUNT_BLOCKED":
                user_events = db_manager.get_events(limit=20, user_id=auth_result["event"]["user_id"])
                if user_events:
                    incident = correlation_engine.correlate_user_events(user_events, scenario_tag="CRPF_LOGIN_MONITOR")
                    db_manager.insert_incident(incident.to_dict())
                    auth_result["incident_id"] = incident.incident_id

            self._send_json(auth_result)
            return

        # Update Account Status (e.g. Block Account / Unblock)
        if path.startswith("/api/auth/accounts/") and path.endswith("/status"):
            parts = path.split("/")
            account_id = parts[4]
            new_status = body.get("status", "TEMPORARILY_BLOCKED")
            reason = body.get("reason", "Precautionary administrative lock by SOC Expert")
            expert = body.get("expert_name", "SOC Lead Expert")

            updated_acc = auth_manager.set_account_status(account_id, new_status, reason, expert)
            self._send_json({"success": True, "account": updated_acc})
            return

        # Action on Expert Notification
        if path.startswith("/api/notifications/") and path.endswith("/action"):
            parts = path.split("/")
            notif_id = parts[3]
            action = body.get("action", "ACKNOWLEDGED")  # BLOCK_ACCOUNT, ACKNOWLEDGED, DISMISS
            force_id = body.get("force_id")
            reason = body.get("reason", "Action taken by SOC Expert")

            if action == "BLOCK_ACCOUNT" and force_id:
                auth_manager.set_account_status(force_id, "TEMPORARILY_BLOCKED", reason, "SOC Security Lead")

            self._send_json({"success": True, "notification_id": notif_id, "action": action})
            return

        # System reset
        if path == "/api/system/reset":
            db_manager.clear_all()
            seed_initial_demo_data()
            self._send_json({"status": "SYSTEM_RESET_COMPLETED"})
            return

        self._send_json({"error": "Endpoint not found"}, status_code=404)


def run_server(host: str = "127.0.0.1", port: int = 8000):
    seed_initial_demo_data()
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, ThreatAnalyzerHTTPRequestHandler)
    print(f"=================================================================")
    print(f"  CRPF / Enterprise IT System Log Analyzer & Threat Intelligence  ")
    print(f"  Centralized Cross-Location Threat Correlation & Risk Assessment ")
    print(f"=================================================================")
    print(f"[*] Dashboard URL: http://{host}:{port}/")
    print(f"[*] REST API Base: http://{host}:{port}/api/")
    print(f"[*] Press Ctrl+C to terminate.")
    print(f"=================================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutting down server gracefully...")
        httpd.server_close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    run_server(port=port)
