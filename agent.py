"""The agent loop: instruction text + Rider credential -> PayPal sandbox order.

Pipeline: verify credential -> extract amount -> check spending policy ->
create PayPal order. Every refusal returns a dict with status "refused" and a
reason; this module never raises on policy refusal. PayPal calls are isolated
in paypal_client so tests can stub them.
"""

import re

import exact
import paypal_client
import policy as policy_mod
import receipt as receipt_mod

_RECIPIENT_RE = re.compile(
    r"""\bto\s+([A-Za-z0-9][\w\s.&'\-]{0,60}?)(?=\s+for\b|\s*$|[,;])""",
    re.IGNORECASE,
)
_MEMO_RE = re.compile(r"""\bfor\s+(.+?)\s*$""", re.IGNORECASE | re.DOTALL)


def parse_instruction(text: str) -> dict:
    """Pure parse: amount, recipient, memo. Raises ValueError if no amount."""
    amount_cents = exact.extract_amount(text)
    recipient = None
    m = _RECIPIENT_RE.search(text)
    if m:
        recipient = m.group(1).strip().rstrip(",;")
    memo = None
    m = _MEMO_RE.search(text)
    if m:
        memo = m.group(1).strip()
        # don't let the memo swallow the amount echo or recipient
        if recipient and memo.startswith(recipient):
            memo = memo[len(recipient):].strip()
    return {"amount_cents": amount_cents, "recipient": recipient, "memo": memo}


def handle_instruction(text: str, credential: str,
                       spending_policy: policy_mod.SpendingPolicy,
                       spent_today_cents: int = 0) -> dict:
    """Run one agent payment instruction. Returns a result dict, never raises
    on policy/credential/parse refusal (PayPal transport errors -> status error)."""
    ok, reason = policy_mod.verify_rider_credential(credential)
    if not ok:
        return {"status": "refused", "reason": f"credential: {reason}", "agent_id": None}
    agent_id = policy_mod.credential_agent_id(credential)

    try:
        parsed = parse_instruction(text)
    except ValueError as e:
        return {"status": "refused", "reason": f"parse: {e}", "agent_id": agent_id}

    allowed, why = spending_policy.check(parsed["amount_cents"], spent_today_cents)
    if not allowed:
        return {"status": "refused", "reason": f"policy: {why}", "agent_id": agent_id}

    desc_bits = []
    if parsed["recipient"]:
        desc_bits.append(f"to {parsed['recipient']}")
    if parsed["memo"]:
        desc_bits.append(f"for {parsed['memo']}")
    description = "RiderPay agent payment" + (f" {'; '.join(desc_bits)}" if desc_bits else "")

    try:
        order = paypal_client.create_order(
            parsed["amount_cents"], "USD", description[:120]
        )
    except paypal_client.PayPalError as e:
        return {"status": "error", "reason": str(e), "agent_id": agent_id}

    return {
        "status": "awaiting_approval",
        "agent_id": agent_id,
        "order_id": order["order_id"],
        "approve_url": order["approve_url"],
        "amount_cents": parsed["amount_cents"],
        "amount": exact.fmt_cents(parsed["amount_cents"]),
        "recipient": parsed["recipient"],
        "memo": parsed["memo"],
    }


def capture_and_receipt(order_id: str, agent_id: str) -> dict:
    """Capture an approved order and return a signed receipt dict."""
    cap = paypal_client.capture_order(order_id)
    return receipt_mod.make_receipt(
        agent_id=agent_id,
        order_id=order_id,
        capture_id=cap["capture_id"],
        amount_cents=cap["amount_cents"],
        currency=cap.get("currency", "USD"),
    )
