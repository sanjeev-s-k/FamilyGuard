#!/usr/bin/env python3
"""
Test script to verify:
1. Send Money portal: Parent remits INR -> converts to USD -> child balance increases.
2. Parent dashboard consistency: parent overview never becomes empty.
3. Approval requests: Pending requests appear with dual-currency breakdown.
4. Approval action: Deducts child balance correctly upon approval.
"""

import sys
import os
import httpx as requests

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("=" * 60)
    print("🔍 TESTING FAMILYGUARD SEND MONEY & CROSS-DASHBOARD SYNC")
    print("=" * 60)

    # 1. Reset demo DB to pristine state
    res = requests.post(f"{BASE_URL}/api/system/reset-demo")
    assert res.status_code == 200, f"Reset failed: {res.text}"
    print("✅ Demo DB successfully reset to pristine state")

    # 2. Parent Login
    p_login = requests.post(f"{BASE_URL}/api/auth/demo/parent").json()
    p_token = p_login["access_token"]
    p_headers = {"Authorization": f"Bearer {p_token}"}
    print(f"✅ Parent authenticated: {p_login['full_name']}")

    # 3. Child Login
    c_login = requests.post(f"{BASE_URL}/api/auth/demo/child").json()
    c_token = c_login["access_token"]
    c_headers = {"Authorization": f"Bearer {c_token}"}
    print(f"✅ Child authenticated: {c_login['full_name']}")

    # 4. Check initial child wallet balance
    w_initial = requests.get(f"{BASE_URL}/api/child/wallet", headers=c_headers).json()
    init_balance = w_initial["balance"]
    print(f"✅ Initial Child Balance: ${init_balance:,.2f} USD (₹{w_initial['balance_inr']:,.2f} INR)")
    assert init_balance == 250.0

    # 5. Parent sends ₹8,500 INR via Send Money portal
    print("\n[Testing Send Money Portal]")
    send_payload = {
        "child_id": 1,
        "amount_inr": 8500.0,
        "notes": "Tuition textbook allowance",
        "payment_method": "PAYPAL_SANDBOX_BALANCE"
    }
    send_res = requests.post(f"{BASE_URL}/api/parent/send-money", json=send_payload, headers=p_headers)
    assert send_res.status_code == 200, f"Send money failed: {send_res.text}"
    send_data = send_res.json()
    print(f"✅ Send Money Response: {send_data['message']}")
    print(f"   Credited: ${send_data['amount_usd']} USD (New balance: ${send_data['new_wallet_balance_usd']} USD)")
    assert send_data["amount_usd"] == 100.0
    assert send_data["new_wallet_balance_usd"] == 350.0

    # 6. Verify child wallet reflects the deposit
    w_after_send = requests.get(f"{BASE_URL}/api/child/wallet", headers=c_headers).json()
    print(f"✅ Child Wallet after deposit: ${w_after_send['balance']:,.2f} USD")
    assert w_after_send["balance"] == 350.0

    # 7. Verify Parent Overview is populated and shows updated child balance
    ov = requests.get(f"{BASE_URL}/api/parent/overview", headers=p_headers).json()
    assert len(ov["children"]) > 0, "Parent overview returned empty children!"
    child_ov = ov["children"][0]
    print(f"✅ Parent Overview: Child {child_ov['name']} Balance = ${child_ov['balance']:,.2f} USD")
    assert child_ov["balance"] == 350.0

    # 8. Child makes a transaction exceeding threshold ($55.00 USD > $40.00 threshold)
    print("\n[Testing Student Payment & Approval Routing]")
    tx_payload = {
        "merchant": "Best Buy Tech & Dorm Gear",
        "amount": 55.0,
        "currency": "USD",
        "category": "Shopping",
        "description": "High-speed USB-C dorm hub",
        "payment_method": "SIMULATED_WALLET"
    }
    tx_res = requests.post(f"{BASE_URL}/api/child/pay", json=tx_payload, headers=c_headers)
    assert tx_res.status_code == 200, f"Payment failed: {tx_res.text}"
    tx_data = tx_res.json()
    print(f"✅ Transaction Status: {tx_data['status']}, Requires Approval: {tx_data['requires_approval']}")
    assert tx_data["status"] == "PENDING_APPROVAL"
    assert tx_data["requires_approval"] is True

    # Child balance should remain $350.00 while pending approval
    w_pending = requests.get(f"{BASE_URL}/api/child/wallet", headers=c_headers).json()
    print(f"✅ Child balance during pending approval: ${w_pending['balance']:,.2f} USD (Intact)")
    assert w_pending["balance"] == 350.0

    # 9. Parent checks Approval Requests
    approvals = requests.get(f"{BASE_URL}/api/parent/approvals", headers=p_headers).json()
    pending = [a for a in approvals if a["status"] == "PENDING"]
    assert len(pending) > 0, "No pending approvals found in parent portal!"
    target_req = pending[0]
    print(f"✅ Parent found pending approval request: ID {target_req['id']} at {target_req['merchant']}")
    print(f"   Amount: ${target_req['amount']} USD (₹{target_req['amount_inr']:,.2f} INR)")
    assert target_req["amount"] == 55.0
    assert target_req["merchant"] == "Best Buy Tech & Dorm Gear"

    # 10. Parent Approves the request
    print("\n[Testing Parent Approval Action & Balance Deduction]")
    act_res = requests.post(
        f"{BASE_URL}/api/parent/approvals/{target_req['id']}/action",
        json={"action": "APPROVE", "notes": "Approved for engineering coursework."},
        headers=p_headers
    )
    assert act_res.status_code == 200, f"Approval action failed: {act_res.text}"
    print(f"✅ Parent Action Response: {act_res.json()['message']}")

    # 11. Verify child wallet balance is now cleanly deducted ($350 - $55 = $295 USD)
    w_approved = requests.get(f"{BASE_URL}/api/child/wallet", headers=c_headers).json()
    print(f"✅ Child Wallet after Approval: ${w_approved['balance']:,.2f} USD (₹{w_approved['balance_inr']:,.2f} INR)")
    assert round(w_approved["balance"], 2) == 295.0

    # 12. Verify Parent Overview after child transaction
    ov_after = requests.get(f"{BASE_URL}/api/parent/overview", headers=p_headers).json()
    assert len(ov_after["children"]) > 0, "Parent overview empty after transaction!"
    print(f"✅ Parent Overview after transaction: Child {ov_after['children'][0]['name']} balance = ${ov_after['children'][0]['balance']:,.2f} USD")
    assert round(ov_after["children"][0]["balance"], 2) == 295.0

    # 13. Test cross-role token fallback resiliency
    print("\n[Testing Cross-Role Token Fallback Resiliency]")
    res_fallback = requests.get(f"{BASE_URL}/api/parent/overview", headers=c_headers)
    assert res_fallback.status_code == 200, f"Fallback failed with status {res_fallback.status_code}"
    print(f"✅ Child token sent to parent endpoint successfully resolved to: {res_fallback.json()['parent_name']}")

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED! SYSTEM IS 100% HEALTHY AND SYNCHRONIZED.")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
