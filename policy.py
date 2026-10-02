"""Spending policy + Rider credential check.

Policy is pure: integer cents in, (allowed, reason) out. Refusals are data,
never exceptions — the agent returns them to the caller.
"""

import json
import time

# STUB: real verification is ES256 JWT against the Rider JWKS (see Agent Rider).
# This stub accepts a JSON string with {agent_id, clearance, exp} so the
# policy/agent flow is testable end-to-end without key infrastructure.
# DO NOT treat a passing stub as a verified credential.


class SpendingPolicy:
    def __init__(self, max_per_tx_cents: int, max_per_day_cents: int):
        assert isinstance(max_per_tx_cents, int) and isinstance(max_per_day_cents, int)
        assert max_per_tx_cents > 0, "per-tx limit must be positive"
        assert max_per_day_cents > 0, "daily limit must be positive"
        self.max_per_tx_cents = max_per_tx_cents
        self.max_per_day_cents = max_per_day_cents

    def check(self, amount_cents: int, spent_today_cents: int) -> tuple:
        """Return (allowed: bool, reason: str)."""
        if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
            return False, "amount must be integer cents"
        if isinstance(spent_today_cents, bool) or not isinstance(spent_today_cents, int):
            return False, "spent_today must be integer cents"
        if amount_cents <= 0:
            return False, "amount must be positive"
        if spent_today_cents < 0:
            return False, "spent_today cannot be negative"
        if amount_cents > self.max_per_tx_cents:
            return False, (
                f"amount exceeds per-transaction limit "
                f"({amount_cents} > {self.max_per_tx_cents} cents)"
            )
        if spent_today_cents + amount_cents > self.max_per_day_cents:
            return False, (
                f"amount exceeds daily limit "
                f"({spent_today_cents + amount_cents} > {self.max_per_day_cents} cents)"
            )
        return True, "ok"


def verify_rider_credential(cred: str) -> tuple:
    """STUB — see module docstring. Returns (ok: bool, reason: str)."""
    if not isinstance(cred, str) or not cred.strip():
        return False, "malformed credential: empty"
    try:
        data = json.loads(cred)
    except (json.JSONDecodeError, TypeError):
        return False, "malformed credential: not JSON"
    if not isinstance(data, dict):
        return False, "malformed credential: not an object"
    for field in ("agent_id", "clearance", "exp"):
        if field not in data:
            return False, f"malformed credential: missing field {field!r}"
    exp = data["exp"]
    if isinstance(exp, bool) or not isinstance(exp, (int, float)):
        return False, "malformed credential: exp must be a number"
    if exp <= time.time():
        return False, "credential expired"
    return True, "ok"


def credential_agent_id(cred: str) -> str | None:
    """Extract agent_id from a credential that passed verify_rider_credential."""
    try:
        return json.loads(cred).get("agent_id")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return None
