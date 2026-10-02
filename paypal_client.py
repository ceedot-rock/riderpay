"""PayPal SANDBOX client. Sandbox only — never production.

Base URL is pinned to api-m.sandbox.paypal.com and asserted at import time.
Credentials come from env: PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET.
No secrets in code, logs, or error strings.
"""

import base64
import os

import requests

BASE_URL = "https://api-m.sandbox.paypal.com"
assert "sandbox" in BASE_URL, "RiderPay is SANDBOX ONLY — refusing to configure a live base URL"


class PayPalError(Exception):
    pass


def _credentials() -> tuple:
    cid = os.environ.get("PAYPAL_CLIENT_ID")
    secret = os.environ.get("PAYPAL_CLIENT_SECRET")
    if not cid or not secret:
        raise PayPalError("PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET not set")
    return cid, secret


def get_token() -> str:
    """OAuth2 client-credentials grant. Returns a bearer access token."""
    cid, secret = _credentials()
    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post(
        f"{BASE_URL}/v1/oauth2/token",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
        timeout=30,
    )
    if not r.ok:
        raise PayPalError(f"oauth token request failed: HTTP {r.status_code}")
    try:
        return r.json()["access_token"]
    except (ValueError, KeyError) as e:
        raise PayPalError(f"oauth token response malformed: {e}")


def _cents_to_value(amount_cents: int) -> str:
    """Integer cents -> PayPal 'd.dd' string. No floats."""
    assert isinstance(amount_cents, int) and not isinstance(amount_cents, bool)
    assert amount_cents > 0, "PayPal order amount must be positive"
    return f"{amount_cents // 100}.{amount_cents % 100:02d}"


def create_order(amount_cents: int, currency: str = "USD", description: str = "RiderPay agent payment") -> dict:
    """Create an order with intent=CAPTURE. Returns {order_id, approve_url, status}."""
    token = get_token()
    r = requests.post(
        f"{BASE_URL}/v2/checkout/orders",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency,
                        "value": _cents_to_value(amount_cents),
                    },
                    "description": description[:120],
                }
            ],
        },
        timeout=30,
    )
    if not r.ok:
        raise PayPalError(f"create order failed: HTTP {r.status_code}")
    data = r.json()
    approve_url = next(
        (l.get("href") for l in data.get("links", []) if l.get("rel") == "approve"),
        None,
    )
    return {"order_id": data["id"], "approve_url": approve_url, "status": data.get("status")}


def capture_order(order_id: str) -> dict:
    """Capture an approved order. Returns {capture_id, status, amount_cents}."""
    token = get_token()
    r = requests.post(
        f"{BASE_URL}/v2/checkout/orders/{order_id}/capture",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={},
        timeout=30,
    )
    if not r.ok:
        raise PayPalError(f"capture failed: HTTP {r.status_code}")
    data = r.json()
    units = data.get("purchase_units") or []
    captures = (units[0].get("payments", {}).get("captures", []) if units else [])
    cap = captures[0] if captures else {}
    amount = (cap.get("amount") or {})
    return {
        "capture_id": cap.get("id"),
        "status": data.get("status"),
        "amount_cents": _value_to_cents(amount.get("value", "0.00")),
        "currency": amount.get("currency_code", "USD"),
    }


def _value_to_cents(value: str) -> int:
    """PayPal 'd.dd' string -> integer cents. No floats."""
    dollars, _, cents = value.partition(".")
    return int(dollars or "0") * 100 + int((cents + "00")[:2] or "0")
