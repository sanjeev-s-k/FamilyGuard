"""
Unit and Integration Test Suite for IT System Log Analyzer
"""

import unittest
import os
import sys
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.database import DatabaseManager
from backend.normalizer import LogNormalizer
from backend.integrity_engine import compute_log_hash, verify_log_integrity, simulate_log_tampering
from backend.identity_linker import IdentityLinker
from backend.risk_scorer import risk_scorer
from backend.correlation_engine import correlation_engine
from backend.agent_simulator import AgentManager
from backend.ml_engine import ml_classifier
from backend.scenarios import (
    generate_scenario_a, generate_scenario_b, generate_scenario_c, generate_scenario_d
)

TEST_DB_PATH = os.path.join(ROOT_DIR, "data", "test_log_analyzer.db")


class TestLogAnalyzer(unittest.TestCase):

    def setUp(self):
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        self.db = DatabaseManager(TEST_DB_PATH)
        self.agent_mgr = AgentManager(self.db)
        self.id_linker = IdentityLinker()

    def tearDown(self):
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def test_log_normalization(self):
        """Test normalization across varied raw log formats into canonical schema."""
        raw_linux = "pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=10.14.2.19 user=user_u102"
        ev1 = LogNormalizer.normalize_raw_log(raw_linux, location="North", server_id="N-01")
        self.assertEqual(ev1["event_type"], "FAILED_LOGIN")
        self.assertEqual(ev1["login_status"], "FAILURE")
        self.assertEqual(ev1["user_id"], "user_u102")
        self.assertEqual(ev1["location"], "North")
        self.assertTrue(len(ev1["hash_signature"]) > 20)

        raw_win = "Security Event 4624: An account was successfully logged on. Account: user_u102, Host: DEV-WIN-9021"
        ev2 = LogNormalizer.normalize_raw_log(raw_win, location="North", server_id="N-01")
        self.assertEqual(ev2["event_type"], "SUCCESSFUL_LOGIN")
        self.assertEqual(ev2["login_status"], "SUCCESS")

    def test_cryptographic_integrity_and_tampering(self):
        """Test HMAC SHA-256 verification and detection of tampering."""
        event = LogNormalizer.normalize_dict({
            "location": "North",
            "server_id": "N-01",
            "user_id": "user_u102",
            "device_id": "DEV-WIN-9021",
            "source_ip": "10.14.2.19",
            "event_type": "SUCCESSFUL_LOGIN",
            "login_status": "SUCCESS"
        })

        # Untampered check
        is_valid, _, msg = verify_log_integrity(event)
        self.assertTrue(is_valid)
        self.assertIn("VERIFIED", msg)

        # Tampered check
        tampered = simulate_log_tampering(event, "source_ip", "1.2.3.4")
        is_valid_tampered, _, msg_tampered = verify_log_integrity(tampered)
        self.assertFalse(is_valid_tampered)
        self.assertIn("Integrity Warning", msg_tampered)

    def test_identity_linking_and_impossible_travel(self):
        """Test impossible travel velocity detection between remote locations."""
        ev_north = {
            "timestamp": "2026-08-18T10:00:00Z",
            "location": "North",
            "user_id": "user_u102",
            "device_id": "DEV-WIN-9021"
        }
        ev_south_fast = {
            "timestamp": "2026-08-18T10:08:00Z",  # 8 minutes later!
            "location": "South",
            "user_id": "user_u102",
            "device_id": "DEV-UNKNOWN-88"
        }

        res = self.id_linker.assess_identity_context(ev_south_fast, previous_events=[ev_north])
        self.assertTrue(res["impossible_travel"])
        self.assertTrue(res["is_unusual_location"])
        self.assertTrue(res["is_unknown_device"])
        self.assertGreater(res["travel_details"]["calculated_speed_kmh"], 800)

    def test_scenario_a_low_risk(self):
        """Scenario A: 2 failed attempts from known device/location -> Low Risk."""
        events = generate_scenario_a()
        inc = correlation_engine.correlate_user_events(events, scenario_tag="SCENARIO_A")
        self.assertEqual(inc.risk_assessment.risk_level, "LOW")
        self.assertLessEqual(inc.risk_assessment.overall_score, 30)

    def test_scenario_b_medium_risk(self):
        """Scenario B: 7 failed attempts from known device/location -> Medium Risk."""
        events = generate_scenario_b()
        inc = correlation_engine.correlate_user_events(events, scenario_tag="SCENARIO_B")
        self.assertEqual(inc.risk_assessment.risk_level, "MEDIUM")
        self.assertTrue(31 <= inc.risk_assessment.overall_score <= 60)

    def test_scenario_c_high_risk(self):
        """Scenario C: Failures in North -> Success in South from unknown device -> High Risk."""
        events = generate_scenario_c()
        inc = correlation_engine.correlate_user_events(events, scenario_tag="SCENARIO_C")
        self.assertIn(inc.risk_assessment.risk_level, ["HIGH", "VERY_HIGH"])
        self.assertGreaterEqual(inc.risk_assessment.overall_score, 60)

    def test_scenario_d_very_high_risk(self):
        """Scenario D: North -> South -> East data exfiltration across 3 locations in 12 min -> Very High Risk."""
        events = generate_scenario_d()
        inc = correlation_engine.correlate_user_events(events, scenario_tag="SCENARIO_D")
        self.assertEqual(inc.risk_assessment.risk_level, "VERY_HIGH")
        self.assertGreaterEqual(inc.risk_assessment.overall_score, 80)
        self.assertEqual(len(inc.timeline), 4)
        self.assertTrue(len(inc.attack_graph.nodes) >= 6)

    def test_local_agent_offline_buffering_and_sync(self):
        """Test local agent disconnect, offline buffering, and resynchronization."""
        # 1. Agent starts online
        agent = self.agent_mgr.get_agent("East")
        self.assertEqual(agent.status, "ONLINE")

        # 2. Agent goes offline
        self.agent_mgr.set_agent_status("East", "OFFLINE")
        self.assertEqual(agent.status, "OFFLINE")

        # 3. Log collected while offline -> buffered
        res1 = self.agent_mgr.collect_log("East", "Log 1 while offline", server_id="E-01")
        self.assertTrue(res1["buffered"])
        self.assertEqual(len(agent.buffer), 1)

        res2 = self.agent_mgr.collect_log("East", "Log 2 while offline", server_id="E-02")
        self.assertEqual(len(agent.buffer), 2)

        # 4. Sync buffer when connection restored
        sync_res = self.agent_mgr.sync_agent_buffer("East")
        self.assertEqual(sync_res["synced_count"], 2)
        self.assertEqual(len(agent.buffer), 0)
        self.assertEqual(agent.status, "ONLINE")

        # Verify logs were ingested to database
        db_events = self.db.get_events(location="East")
        self.assertGreaterEqual(len(db_events), 2)


if __name__ == "__main__":
    unittest.main()
