"""
Multi-Case Authentication and Cross-Account Intrusion Test Suite
Tests legitimate logins, typos, brute force, cross-account unauthorized access attempts,
expert notification triggers, account locking/blocking, and cryptographic log immutability.
"""

import unittest
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.database import DatabaseManager
from backend.auth_manager import AuthManager, hash_password
from backend.integrity_engine import verify_log_integrity, simulate_log_tampering

TEST_DB_PATH = os.path.join(ROOT_DIR, "data", "test_auth_intrusion.db")


class TestCRPFAuthAndIntrusion(unittest.TestCase):

    def setUp(self):
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        self.auth_mgr = AuthManager(TEST_DB_PATH)

    def tearDown(self):
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

    def test_case_1_legitimate_login(self):
        """Case 1: Legitimate Authorized Login (Major Vikram from North with known device)."""
        res = self.auth_mgr.authenticate_crpf_login(
            identifier="CRPF-90214",
            password_input="Crpf@Signals2026",
            location="North",
            server_id="N-01",
            device_id="DEV-WIN-9021",
            source_ip="10.14.2.19"
        )
        self.assertTrue(res["authenticated"])
        self.assertEqual(res["auth_code"], "SUCCESS")
        self.assertEqual(res["account"]["full_name"], "Major Vikram Rathore")
        self.assertLessEqual(res["risk_assessment"]["overall_score"], 30)
        self.assertEqual(res["risk_assessment"]["risk_level"], "LOW")
        
        # Verify immutable HMAC log signature
        is_valid, _, msg = verify_log_integrity(res["event"])
        self.assertTrue(is_valid)

    def test_case_2_wrong_password_typo(self):
        """Case 2: Accidental typo (1 failed attempt from normal device/location)."""
        res = self.auth_mgr.authenticate_crpf_login(
            identifier="CRPF-90214",
            password_input="WrongTypoPassword",
            location="North",
            server_id="N-01",
            device_id="DEV-WIN-9021",
            source_ip="10.14.2.19"
        )
        self.assertFalse(res["authenticated"])
        self.assertEqual(res["auth_code"], "INVALID_CREDENTIALS")
        self.assertLessEqual(res["risk_assessment"]["overall_score"], 30)

    def test_case_3_brute_force_on_account(self):
        """Case 3: Repeated failed attempts on an account."""
        for _ in range(6):
            res = self.auth_mgr.authenticate_crpf_login(
                identifier="CRPF-90214",
                password_input="BruteForceAttempt",
                location="North",
                server_id="N-01",
                device_id="DEV-WIN-9021",
                source_ip="10.14.2.19"
            )
        self.assertFalse(res["authenticated"])
        self.assertGreaterEqual(res["risk_assessment"]["overall_score"], 20)

    def test_case_4_cross_account_intrusion_attempt(self):
        """
        Case 4: Cross-Account Intrusion Attempt:
        Attacker from South Hub using unregistered hardware (DEV-UNKNOWN-88) tries to break
        into Major Vikram's North account (CRPF-90214) with guessed password.
        Should trigger High/Very High risk and dispatch an Expert Notification.
        """
        res = self.auth_mgr.authenticate_crpf_login(
            identifier="CRPF-90214",
            password_input="HackedP@ssw0rd99",
            location="South",                     # Unusual location (Home is North)
            server_id="S-01",
            device_id="DEV-UNKNOWN-88",           # Unknown device
            source_ip="198.51.100.42"             # External IP
        )
        self.assertFalse(res["authenticated"])
        self.assertTrue(res["notification_dispatched"])
        self.assertIn(res["risk_assessment"]["risk_level"], ["HIGH", "VERY_HIGH"])
        self.assertGreaterEqual(res["risk_assessment"]["overall_score"], 60)

        # Check that Expert Notification was recorded in DB
        notifs = self.auth_mgr.get_expert_notifications(unread_only=True)
        self.assertGreaterEqual(len(notifs), 1)
        self.assertEqual(notifs[0]["force_id"], "CRPF-90214")
        self.assertEqual(notifs[0]["device_id"], "DEV-UNKNOWN-88")

    def test_case_5_precautionary_account_block_and_rejection(self):
        """
        Case 5: Precautionary Account Blocking:
        SOC Security Expert blocks the account. Subsequent logins are rejected with ACCOUNT_BLOCKED.
        """
        # 1. Expert temporarily blocks account
        self.auth_mgr.set_account_status(
            force_id_or_user_id="CRPF-90214",
            new_status="TEMPORARILY_BLOCKED",
            reason="Precaution: Intrusion attempt detected from South region",
            expert_name="SOC Defense Lead"
        )

        acc = self.auth_mgr.get_account_by_identifier("CRPF-90214")
        self.assertEqual(acc["status"], "TEMPORARILY_BLOCKED")

        # 2. Even with correct password, login must be blocked
        res = self.auth_mgr.authenticate_crpf_login(
            identifier="CRPF-90214",
            password_input="Crpf@Signals2026",
            location="North",
            server_id="N-01",
            device_id="DEV-WIN-9021",
            source_ip="10.14.2.19"
        )
        self.assertFalse(res["authenticated"])
        self.assertEqual(res["auth_code"], "ACCOUNT_BLOCKED")
        self.assertIn("TEMPORARILY BLOCKED", res["message"])

        # 3. Unblock account and verify login succeeds again
        self.auth_mgr.set_account_status("CRPF-90214", "ACTIVE")
        res_after = self.auth_mgr.authenticate_crpf_login(
            identifier="CRPF-90214",
            password_input="Crpf@Signals2026",
            location="North",
            server_id="N-01",
            device_id="DEV-WIN-9021",
            source_ip="10.14.2.19"
        )
        self.assertTrue(res_after["authenticated"])

    def test_case_6_immutable_login_audit_integrity(self):
        """Case 6: Verifies cryptographic HMAC immutability on login audit records."""
        res = self.auth_mgr.authenticate_crpf_login(
            identifier="CRPF-55120",
            password_input="Priya#Logistics26",
            location="South",
            server_id="S-01",
            device_id="DEV-LAP-5512",
            source_ip="10.22.4.11"
        )
        event = res["event"]

        # Valid untampered check
        is_valid, _, _ = verify_log_integrity(event)
        self.assertTrue(is_valid)

        # Altering login_status from SUCCESS to FAILURE or IP to 1.1.1.1 creates tamper mismatch
        tampered = simulate_log_tampering(event, "login_status", "FAILURE")
        is_valid_tampered, _, msg = verify_log_integrity(tampered)
        self.assertFalse(is_valid_tampered)
        self.assertIn("Integrity Warning", msg)


if __name__ == "__main__":
    unittest.main()
