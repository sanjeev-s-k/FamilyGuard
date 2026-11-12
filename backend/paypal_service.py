import os
import time
import base64
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger("familyguard.paypal")

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID", "")

SANDBOX_API_URL = "https://api-m.sandbox.paypal.com"
LIVE_API_URL = "https://api-m.paypal.com"

BASE_URL = SANDBOX_API_URL if PAYPAL_MODE == "sandbox" else LIVE_API_URL

_token_cache: Dict[str, Any] = {
    "access_token": None,
    "expires_at": 0
}


def is_configured() -> bool:
    return bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET and "your_" not in PAYPAL_CLIENT_ID.lower())


async def get_access_token() -> Optional[str]:
    """Generates OAuth 2.0 access token using PayPal Client ID and Secret."""
    if not is_configured():
        return None

    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["access_token"]

    auth_header = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}".encode()).decode()
    url = f"{BASE_URL}/v1/oauth2/token"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={"grant_type": "client_credentials"}
            )
            if response.status_code == 200:
                data = response.json()
                _token_cache["access_token"] = data["access_token"]
                _token_cache["expires_at"] = now + data.get("expires_in", 3600)
                return _token_cache["access_token"]
            else:
                logger.error(f"PayPal OAuth failed [{response.status_code}]: {response.text}")
                return None
    except Exception as e:
        logger.error(f"Error fetching PayPal access token: {e}")
        return None


async def create_order(
    amount: float,
    currency: str = "USD",
    reference_id: str = "",
    description: str = "FamilyGuard Parental Monitored Sandbox Payment"
) -> Dict[str, Any]:
    """
    Creates a PayPal order via v2/checkout/orders.
    If credentials are not configured, generates a simulated sandbox order response.
    """
    token = await get_access_token()

    if not token or not is_configured():
        # Demo Sandbox Mode
        fake_order_id = f"PAYPAL-SANDBOX-{int(time.time() * 1000)}"
        return {
            "order_id": fake_order_id,
            "status": "CREATED",
            "approval_url": f"https://www.sandbox.paypal.com/checkoutnow?token={fake_order_id}",
            "amount": amount,
            "currency": currency,
            "mode": "DEMO_SANDBOX",
            "message": "Demo mode simulated PayPal sandbox order (No PayPal API credentials configured)"
        }

    url = f"{BASE_URL}/v2/checkout/orders"
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": reference_id,
                "description": description,
                "amount": {
                    "currency_code": currency,
                    "value": f"{amount:.2f}"
                }
            }
        ],
        "application_context": {
            "brand_name": "FamilyGuard Fintech",
            "landing_page": "BILLING",
            "user_action": "PAY_NOW",
            "return_url": "http://localhost:5173/child/payment-success",
            "cancel_url": "http://localhost:5173/child/payment-cancelled"
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            if res.status_code in (200, 201):
                data = res.json()
                approve_link = next((link["href"] for link in data.get("links", []) if link.get("rel") == "approve"), None)
                return {
                    "order_id": data["id"],
                    "status": data["status"],
                    "approval_url": approve_link,
                    "amount": amount,
                    "currency": currency,
                    "mode": "LIVE_SANDBOX",
                    "raw": data
                }
            else:
                logger.error(f"PayPal order creation failed [{res.status_code}]: {res.text}")
                raise Exception(f"PayPal order creation failed: {res.text}")
    except Exception as e:
        logger.error(f"Failed to create PayPal order: {e}")
        raise e


async def capture_order(order_id: str) -> Dict[str, Any]:
    """
    Captures payment for an approved PayPal order via v2/checkout/orders/{id}/capture.
    """
    token = await get_access_token()

    if not token or not is_configured() or order_id.startswith("PAYPAL-SANDBOX-"):
        # Demo Sandbox Mode Capture
        fake_capture_id = f"CAP-{int(time.time() * 1000)}"
        return {
            "capture_id": fake_capture_id,
            "order_id": order_id,
            "status": "COMPLETED",
            "mode": "DEMO_SANDBOX",
            "message": "Demo mode payment captured successfully (Verified Sandbox simulation)"
        }

    url = f"{BASE_URL}/v2/checkout/orders/{order_id}/capture"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            if res.status_code in (200, 201):
                data = res.json()
                capture_id = ""
                try:
                    capture_id = data["purchase_units"][0]["payments"]["captures"][0]["id"]
                except (KeyError, IndexError):
                    capture_id = f"CAP-{order_id}"

                return {
                    "capture_id": capture_id,
                    "order_id": order_id,
                    "status": data.get("status", "COMPLETED"),
                    "mode": "LIVE_SANDBOX",
                    "raw": data
                }
            else:
                logger.error(f"PayPal capture failed [{res.status_code}]: {res.text}")
                raise Exception(f"PayPal capture failed: {res.text}")
    except Exception as e:
        logger.error(f"Failed to capture PayPal order: {e}")
        raise e


async def verify_webhook_signature(
    transmission_id: str,
    timestamp: str,
    webhook_id: str,
    event_body: dict,
    cert_url: str,
    actual_sig: str,
    auth_algo: str
) -> bool:
    """Verifies PayPal webhook signature against PayPal APIs."""
    if not is_configured():
        return True  # Allowed in local demo mode

    token = await get_access_token()
    if not token:
        return False

    url = f"{BASE_URL}/v1/notifications/verify-webhook-signature"
    payload = {
        "transmission_id": transmission_id,
        "transmission_time": timestamp,
        "cert_url": cert_url,
        "auth_algo": auth_algo,
        "transmission_sig": actual_sig,
        "webhook_id": webhook_id or PAYPAL_WEBHOOK_ID,
        "webhook_event": event_body
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            if res.status_code == 200:
                data = res.json()
                return data.get("verification_status") == "SUCCESS"
            return False
    except Exception as e:
        logger.error(f"Webhook verification error: {e}")
        return False
