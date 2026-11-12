import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import Base, engine, SessionLocal
from backend.seed_data import seed_demo_data


class TestFamilyGuardAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        seed_demo_data(db)
        db.close()
        cls.client = TestClient(app)

    def test_01_health_check(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")

    def test_02_demo_login_parent(self):
        res = self.client.post("/api/auth/demo/parent")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["role"], "PARENT")
        self.assertEqual(data["email"], "parent@familyguard.demo")
        self.assertIn("access_token", data)
        self.__class__.parent_token = data["access_token"]

    def test_03_demo_login_child(self):
        res = self.client.post("/api/auth/demo/child")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["role"], "CHILD")
        self.assertEqual(data["email"], "arjun@familyguard.demo")
        self.assertIn("access_token", data)
        self.__class__.child_token = data["access_token"]

    def test_04_child_wallet_and_limits(self):
        headers = {"Authorization": f"Bearer {self.child_token}"}
        res = self.client.get("/api/child/wallet", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["balance"], 2000.0)
        self.assertEqual(data["daily_limit"], 500.0)
        self.assertEqual(data["weekly_limit"], 2000.0)
        self.assertEqual(data["approval_threshold"], 300.0)

    def test_05_child_payment_within_limits(self):
        headers = {"Authorization": f"Bearer {self.child_token}"}
        payload = {
            "merchant": "City Bookstore",
            "amount": 150.0,
            "currency": "INR",
            "category": "Education",
            "description": "Math Olympiad Workbook",
            "payment_method": "SIMULATED_WALLET"
        }
        res = self.client.post("/api/child/pay", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "COMPLETED")
        self.assertFalse(data["requires_approval"])
        self.assertEqual(data["new_balance"], 1850.0)
        self.assertEqual(data["ai_report"]["risk_level"], "LOW")

    def test_06_child_payment_exceeding_threshold(self):
        headers = {"Authorization": f"Bearer {self.child_token}"}
        payload = {
            "merchant": "Tech World Electronics",
            "amount": 450.0,
            "currency": "INR",
            "category": "Gaming",
            "description": "Wireless Gaming Controller",
            "payment_method": "SIMULATED_WALLET"
        }
        res = self.client.post("/api/child/pay", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "PENDING_APPROVAL")
        self.assertTrue(data["requires_approval"])
        # Wallet balance should NOT be deducted until approved
        self.assertEqual(data["new_balance"], 1850.0)

    def test_07_parent_approval_workflow(self):
        parent_headers = {"Authorization": f"Bearer {self.parent_token}"}
        # Check pending approvals
        res = self.client.get("/api/parent/approvals", headers=parent_headers)
        self.assertEqual(res.status_code, 200)
        approvals = res.json()
        self.assertGreaterEqual(len(approvals), 1)

        target_req = approvals[0]
        self.assertEqual(target_req["status"], "PENDING")
        self.assertEqual(target_req["amount"], 450.0)

        # Approve the request
        approve_res = self.client.post(
            f"/api/parent/approvals/{target_req['id']}/action",
            json={"action": "APPROVE", "notes": "Approved for good study performance."},
            headers=parent_headers
        )
        self.assertEqual(approve_res.status_code, 200)
        self.assertEqual(approve_res.json()["approval_status"], "APPROVED")

        # Now check child wallet: 1850 - 450 = 1400
        child_headers = {"Authorization": f"Bearer {self.child_token}"}
        wallet_res = self.client.get("/api/child/wallet", headers=child_headers)
        self.assertEqual(wallet_res.json()["balance"], 1400.0)

    def test_08_parent_ai_assistant(self):
        parent_headers = {"Authorization": f"Bearer {self.parent_token}"}
        queries = [
            "How much did my child spend today?",
            "What was the highest transaction this week?",
            "Which category has the highest spending?",
            "Show transactions above ₹200",
            "How much of the weekly allowance remains?",
            "Generate a monthly spending summary"
        ]
        for q in queries:
            res = self.client.post(
                "/api/parent/ai-assistant",
                json={"prompt": q},
                headers=parent_headers
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("reply", data)
            self.assertTrue(len(data["reply"]) > 10)

    def test_09_download_pdf_report(self):
        res = self.client.get("/api/reports/transaction/TX1021/pdf")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/pdf")
        self.assertGreater(len(res.content), 1000)


if __name__ == "__main__":
    unittest.main()
