#!/usr/bin/env python3
"""
FamilyGuard – 13-Step Demo Scenario E2E Verification Script
Tests all requirements and simulates the live hackathon presentation flow.
"""

import sys
import os
import json
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
from backend.database import Base, engine, SessionLocal
from backend.seed_data import seed_demo_data

def run_demo_verification():
    print("=" * 70)
    print("🛡️  FAMILYGUARD DEMO SCENARIO VERIFICATION")
    print("=" * 70)

    # Reset DB to pristine seed state
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_demo_data(db)
    db.close()

    client = TestClient(app)

    # -------------------------------------------------------------
    # Step 1: Parent logs in
    # -------------------------------------------------------------
    print("\n[Step 1] Parent logs in as 'Demo Parent'...")
    res = client.post("/api/auth/demo/parent")
    assert res.status_code == 200, res.text
    parent_data = res.json()
    parent_token = parent_data["access_token"]
    parent_headers = {"Authorization": f"Bearer {parent_token}"}
    print(f"  ✅ Parent authenticated: {parent_data['full_name']} ({parent_data['email']})")

    # -------------------------------------------------------------
    # Step 2: Parent views Arjun's dashboard & configured limits
    # -------------------------------------------------------------
    print("\n[Step 2] Parent views Arjun's dashboard & spending settings...")
    res = client.get("/api/parent/overview", headers=parent_headers)
    assert res.status_code == 200, res.text
    overview = res.json()
    child = overview["children"][0]
    print(f"  ✅ Child found: {child['name']}, Balance: ₹{child['balance']:,.2f}")
    print(f"  ✅ Configured limits: Daily: ₹{child['daily_limit']}, Weekly: ₹{child['weekly_limit']}, Threshold: ₹{child['approval_threshold']}")

    # -------------------------------------------------------------
    # Step 3: Child initiates a Sandbox payment
    # -------------------------------------------------------------
    print("\n[Step 3] Arjun initiates a Sandbox payment (₹150 for Science Project Books)...")
    child_login = client.post("/api/auth/demo/child").json()
    child_token = child_login["access_token"]
    child_headers = {"Authorization": f"Bearer {child_token}"}

    tx1_payload = {
        "merchant": "Global Book House",
        "amount": 150.0,
        "currency": "INR",
        "category": "Education",
        "description": "Science Project Research Guide",
        "payment_method": "SIMULATED_WALLET"
    }
    tx1_res = client.post("/api/child/pay", json=tx1_payload, headers=child_headers)
    assert tx1_res.status_code == 200, tx1_res.text
    tx1_data = tx1_res.json()
    # Expected new balance after converting INR to USD using FX rate (85 INR = 1 USD)
    expected_usd_amount = round(tx1_payload["amount"] / 85.0, 2)
    expected_balance = round(250.0 - expected_usd_amount, 2)


    # -------------------------------------------------------------
    # Step 4: Backend receives the verified transaction status
    # -------------------------------------------------------------
    print("\n[Step 4] Backend receives and verifies transaction status...")
    print(f"  ✅ Transaction Code: {tx1_data['transaction_code']}, Status: {tx1_data['status']}")
    assert tx1_data["status"] == "COMPLETED"
    assert tx1_data["new_balance"] == expected_balance

    # -------------------------------------------------------------
    # Step 5: AI analyses the transaction
    # -------------------------------------------------------------
    print("\n[Step 5] AI analyses the transaction...")
    ai_report = tx1_data["ai_report"]
    print(f"  ✅ Risk Level: {ai_report['risk_level']}")
    print(f"  ✅ Category: {ai_report['category']}")
    print(f"  ✅ Explanation: {ai_report['explanation']}")
    print(f"  ✅ Spending Summary: {ai_report['spending_summary']}")
    assert ai_report["risk_level"] == "HIGH"

    # -------------------------------------------------------------
    # Step 6: System generates a transaction report
    # -------------------------------------------------------------
    print("\n[Step 6] System generates digital transaction report & PDF receipt...")
    receipt_res = client.get(f"/api/reports/transaction/{tx1_data['transaction_code']}")
    assert receipt_res.status_code == 200, receipt_res.text
    receipt = receipt_res.json()
    print(f"  ✅ Report Title: {receipt['report_title']}")
    print(f"  ✅ Allowance Before: ₹{receipt['daily_spending_before']}, After: ₹{receipt['daily_spending_after']}, Remaining: ₹{receipt['remaining_spending_allowance']}")

    pdf_res = client.get(f"/api/reports/transaction/{tx1_data['transaction_code']}/pdf")
    assert pdf_res.status_code == 200
    print(f"  ✅ PDF generated successfully: {len(pdf_res.content)} bytes")

    # -------------------------------------------------------------
    # Step 7: Parent receives a notification
    # -------------------------------------------------------------
    print("\n[Step 7] Parent receives notification...")
    notifs_res = client.get("/api/parent/notifications", headers=parent_headers)
    notifs = notifs_res.json()
    latest_notif = notifs[0]
    print(f"  ✅ Alert Title: {latest_notif['title']}")
    print(f"  ✅ Alert Message: {latest_notif['message']}")
    assert "Global Book House" in latest_notif["title"]

    # -------------------------------------------------------------
    # Step 8: Parent views the AI explanation
    # -------------------------------------------------------------
    print("\n[Step 8] Parent reviews AI explanation...")
    print(f"  ✅ AI Explanation in receipt: '{receipt['ai_explanation']}'")

    # -------------------------------------------------------------
    # Step 9: A second simulated transaction exceeds the approval threshold
    # -------------------------------------------------------------
    print("\n[Step 9] Arjun initiates second purchase of ₹3500 (Exceeds approval threshold)...")
    tx2_payload = {
        "merchant": "Cyber Arcade & VR Gaming",
        "amount": 3500.0,
        "currency": "INR",
        "category": "Gaming",
        "description": "Virtual Reality Gaming Headset Accessories",
        "payment_method": "SIMULATED_WALLET"
    }
    tx2_res = client.post("/api/child/pay", json=tx2_payload, headers=child_headers)
    assert tx2_res.status_code == 200, tx2_res.text
    tx2_data = tx2_res.json()
    print(f"  ✅ Transaction Code: {tx2_data['transaction_code']}, Status: {tx2_data['status']}")
    print(f"  ✅ Requires Approval: {tx2_data['requires_approval']}")
    assert tx2_data["status"] == "PENDING_APPROVAL"
    # Balance must remain intact
    assert tx2_data["new_balance"] == expected_balance

    # -------------------------------------------------------------
    # Step 10: Parent receives an approval request
    # -------------------------------------------------------------
    print("\n[Step 10] Parent receives pending approval request...")
    approvals_res = client.get("/api/parent/approvals", headers=parent_headers)
    approvals = approvals_res.json()
    pending_req = next((a for a in approvals if a["status"] == "PENDING"), None)
    assert pending_req is not None
    print(f"  ✅ Pending Request ID: {pending_req['id']}, Merchant: {pending_req['merchant']}, Amount: ₹{pending_req['amount']}")

    # -------------------------------------------------------------
    # Step 11: Parent approves or declines
    # -------------------------------------------------------------
    print("\n[Step 11] Parent reviews AI risk assessment and approves the request...")
    act_res = client.post(
        f"/api/parent/approvals/{pending_req['id']}/action",
        json={"action": "APPROVE", "notes": "Approved for excellent report card grades."},
        headers=parent_headers
    )
    assert act_res.status_code == 200, act_res.text
    print(f"  ✅ Parent Action: {act_res.json()['approval_status']}, Message: {act_res.json()['message']}")

    # -------------------------------------------------------------
    # Step 12: Dashboard updates the request status & wallet balance
    # -------------------------------------------------------------
    print("\n[Step 12] Dashboard verifies updated wallet balance...")
    updated_wallet = client.get("/api/child/wallet", headers=child_headers).json()
    # Balance decreases after parental approval
    expected_usd_amount2 = round(tx2_payload["amount"] / 85.0, 2)
    expected_final_balance = round(expected_balance - expected_usd_amount2, 2)
    print(f"  ✅ New Child Wallet Balance: ${updated_wallet['balance']:,.2f} USD")
    assert round(updated_wallet["balance"], 2) == expected_final_balance

    # -------------------------------------------------------------
    # Step 13: Parent asks the AI assistant for a spending summary
    # -------------------------------------------------------------
    print("\n[Step 13] Parent queries AI Parent Assistant...")
    queries = [
        "How much did my child spend today?",
        "What was the highest transaction this week?",
        "Which category has the highest spending?",
        "Show transactions above ₹200",
        "How much of the weekly allowance remains?",
        "Generate a monthly spending summary"
    ]
    for q in queries:
        ai_chat_res = client.post("/api/parent/ai-assistant", json={"prompt": q}, headers=parent_headers)
        assert ai_chat_res.status_code == 200
        reply = ai_chat_res.json()["reply"]
        print(f"\n  Q: '{q}'")
        print(f"  🤖 AI: {reply.splitlines()[0]}")

    print("\n" + "=" * 70)
    print("🎉 ALL 13 DEMO SCENARIO STEPS VERIFIED SUCCESSFULLY WITH 100% PASS!")
    print("=" * 70)

if __name__ == "__main__":
    run_demo_verification()
