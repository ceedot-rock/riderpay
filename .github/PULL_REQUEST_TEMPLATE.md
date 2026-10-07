## What changed

<!-- One or two sentences. -->

## Checks

- [ ] `python3 tests.py` passes
- [ ] Money math stays in integer cents (no floats anywhere on the money path)
- [ ] The sandbox pin is intact: `paypal_client.BASE_URL` still asserts `sandbox`
      and `server.py` still refuses to boot against a non-sandbox base URL
- [ ] No credentials or keys added to the repo; secrets stay in env vars

---

Slid Phi Labs accepts donations to keep the lab independent: https://www.patreon.com/SlidPhiLabs
