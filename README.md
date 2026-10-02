# RiderPay — the agent that can pay

PayPal AI Hackathon entry ("Build What's Next with PayPal and AI").
Target: **Best Use of Agentic Commerce**.

An AI agent holding a signed Rider credential pays via PayPal's **sandbox** API —
with spending bounds, exact integer-cents math (no floats, ever), and
HMAC-signed receipts. The agent takes a natural-language instruction like
"Pay $25 to Acme Corp for invoice #123", verifies its credential, checks
policy, creates a PayPal order, and returns an approval URL. After the payer
approves, the agent captures and issues a signed receipt.

**Sandbox only.** The PayPal base URL is pinned to `api-m.sandbox.paypal.com`
and asserted at import time. There are no real-money paths in this codebase.

## Architecture

```
instruction text ──> agent.py ──> policy.py ──> paypal_client.py ──> PayPal sandbox
                        │              │
                        │              └── SpendingPolicy (per-tx / per-day caps)
                        │                   verify_rider_credential (stub -> ES256 JWT later)
                        ├── exact.py ── integer-cents parse/format, no floats
                        └── receipt.py ── HMAC-SHA256 signed receipts
server.py (Flask) ── POST /api/pay, POST /api/capture, GET /healthz
static/index.html ── demo UI (no external deps)
```

- `paypal_client.py` — sandbox REST: OAuth2 client-credentials, create order
  (intent=CAPTURE), capture order. Integer cents converted to `"d.dd"` strings.
- `policy.py` — `SpendingPolicy(max_per_tx_cents, max_per_day_cents).check()`
  returns `(allowed, reason)`; credential stub accepts JSON
  `{agent_id, clearance, exp}` and rejects expired/malformed.
- `exact.py` — `parse_amount` ("$25", "25 dollars", "2500 cents"; rejects €/£/¥…),
  `extract_amount` (find amount inside a sentence), `fmt_cents` ("$d.cc").
- `receipt.py` — `make_receipt` returns dict with timestamp + HMAC-SHA256
  signature; key from `RECEIPT_KEY` env (hex), ephemeral with warning if absent.
- `agent.py` — `handle_instruction(text, credential, policy)` → result dict.
  Refusals return `{"status": "refused", "reason": ...}`; never raises on policy.

## Sandbox setup

1. PayPal Developer account → dashboard → **Apps & Credentials** → create a
   REST API app → copy Client ID and Secret (sandbox).
2. Export env vars:
   ```bash
   export PAYPAL_CLIENT_ID="..."
   export PAYPAL_CLIENT_SECRET="..."
   export RECEIPT_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
   # optional: export RIDERPAY_MAX_TX_CENTS=50000 RIDERPAY_MAX_DAY_CENTS=200000
   ```
3. Install + run:
   ```bash
   pip install -r requirements.txt
   python3 tests.py          # must be green before demo
   python3 server.py         # http://localhost:5057
   ```
4. Demo flow: type instruction → **Pay** → open the PayPal approval URL in a
   new tab (log in with a sandbox buyer account, approve) → **Capture & get
   receipt** → signed receipt JSON appears.

## API

- `POST /api/pay` `{instruction, credential}` →
  `{status: "awaiting_approval", order_id, approve_url, amount, ...}` or
  `{status: "refused", reason}`.
- `POST /api/capture` `{order_id, agent_id}` →
  `{status: "captured", receipt: {...}}`.
- `GET /healthz` → `{"ok": true}`.

## Hackathon submission notes

- Deadline: Nov 12, 2026, 5:00 PM EST.
- Requires: public GitHub repo + MIT license (included), <3 min YouTube demo,
  hosted demo URL or run instructions, text description naming tools used.
- Roadmap before submit: replace credential stub with real ES256 JWT verify
  against Rider JWKS; durable daily-spend ledger (currently in-memory);
  idempotency keys on create_order.

## License

MIT — see [LICENSE](LICENSE).

---
Slid Phi Labs accepts donations to keep the lab independent: https://www.patreon.com/SlidPhiLabs
