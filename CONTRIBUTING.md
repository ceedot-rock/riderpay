# Contributing to RiderPay

Thanks for helping build the agent that can pay.

## Ground rules

- **Sandbox only.** `paypal_client.BASE_URL` is pinned to
  `api-m.sandbox.paypal.com` and asserted at import time. Any change that adds
  a real-money path does not ship. Ever.
- All money math is integer cents. No floats, ever.
- Never commit credentials, client IDs, client secrets, or receipt keys.
  Secrets travel only via env vars (`PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`,
  `RECEIPT_KEY`).

## Quick checks

```sh
pip install -r requirements.txt
python3 tests.py          # must be green before you open a PR
```

CI runs the unit tests, a secret scan, and a server smoke test
(`GET /healthz`, `GET /api`, demo page) on every pull request.

## Demo server

```sh
python3 server.py         # http://localhost:5057
```

- `GET /api` — service/about/endpoints JSON
- `POST /api/pay`, `POST /api/capture` — sandbox flows
- `GET /healthz` — liveness

## Licensing

RiderPay is MIT-licensed. By contributing you agree your contribution may be
distributed under the MIT license.
