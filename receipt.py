"""Signed payment receipts. HMAC-SHA256 over canonical JSON.

The receipt proves: this agent, this PayPal order/capture, this exact
integer-cents amount, at this time. Key from env RECEIPT_KEY (hex); if absent
we generate an ephemeral key and log a warning — receipts then verify only
within this process lifetime.
"""

import hashlib
import hmac
import json
import logging
import os
import time

log = logging.getLogger(__name__)

_key: bytes | None = None


def signing_key() -> bytes:
    global _key
    if _key is None:
        key_hex = os.environ.get("RECEIPT_KEY")
        if key_hex:
            _key = bytes.fromhex(key_hex.strip())
        else:
            log.warning(
                "RECEIPT_KEY not set — using ephemeral key; "
                "receipts will not verify across restarts"
            )
            _key = os.urandom(32)
    return _key


def reset_key_cache() -> None:
    """Test helper: forget the cached key so env changes take effect."""
    global _key
    _key = None


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def sign_receipt(payload: dict, key: bytes) -> str:
    """HMAC-SHA256 hex over canonical JSON of payload."""
    assert isinstance(key, bytes) and len(key) >= 16, "key must be bytes >= 16"
    return hmac.new(key, _canonical(payload), hashlib.sha256).hexdigest()


def verify_receipt(receipt: dict, key: bytes) -> bool:
    """True iff receipt['signature'] matches the rest of the payload."""
    sig = receipt.get("signature")
    if not isinstance(sig, str):
        return False
    payload = {k: v for k, v in receipt.items() if k != "signature"}
    return hmac.compare_digest(sign_receipt(payload, key), sig)


def make_receipt(agent_id: str, order_id: str, capture_id: str,
                 amount_cents: int, currency: str = "USD") -> dict:
    """Build and sign a receipt dict. Amount is integer cents — no floats."""
    assert isinstance(amount_cents, int) and not isinstance(amount_cents, bool)
    payload = {
        "agent_id": agent_id,
        "order_id": order_id,
        "capture_id": capture_id,
        "amount_cents": amount_cents,
        "currency": currency,
        "timestamp": int(time.time()),
    }
    payload["signature"] = sign_receipt(payload, signing_key())
    return payload
