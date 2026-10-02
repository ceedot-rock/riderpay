"""Unit tests: exact.py, policy.py, receipt.py. No network. Run: python3 tests.py"""

import json
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import exact
import policy as policy_mod
import receipt as receipt_mod


class TestExact(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(exact.parse_amount("$25"), 2500)
        self.assertEqual(exact.parse_amount("25"), 2500)
        self.assertEqual(exact.parse_amount("$25.50"), 2550)
        self.assertEqual(exact.parse_amount("25 dollars"), 2500)
        self.assertEqual(exact.parse_amount("2500 cents"), 2500)
        self.assertEqual(exact.parse_amount("$1,234.56"), 123456)

    def test_no_floats(self):
        # the classic: 0.1 + 0.2 != 0.3 in float. In cents it must be exact.
        total = exact.parse_amount("$0.10") + exact.parse_amount("$0.20")
        self.assertEqual(total, exact.parse_amount("$0.30"))
        self.assertEqual(total, 30)
        self.assertIsInstance(total, int)
        # a cent is a cent
        self.assertEqual(exact.parse_amount("$0.01"), 1)
        self.assertEqual(exact.parse_amount("$0.1"), 10)
        self.assertEqual(exact.parse_amount("$.99"), 99)

    def test_rejects(self):
        for bad in ["€25", "£10", "¥100", "", "   ", "twenty bucks", "$1.234", "$-5"]:
            with self.assertRaises(ValueError, msg=bad):
                exact.parse_amount(bad)

    def test_extract(self):
        self.assertEqual(exact.extract_amount("Pay $25 to Acme Corp for invoice #123"), 2500)
        self.assertEqual(exact.extract_amount("send 3000 cents please"), 3000)
        with self.assertRaises(ValueError):
            exact.extract_amount("Pay €25 to Acme")

    def test_fmt(self):
        self.assertEqual(exact.fmt_cents(2500), "$25.00")
        self.assertEqual(exact.fmt_cents(5), "$0.05")
        self.assertEqual(exact.fmt_cents(0), "$0.00")
        with self.assertRaises(AssertionError):
            exact.fmt_cents(25.0)  # floats refused


class TestPolicy(unittest.TestCase):
    def setUp(self):
        self.p = policy_mod.SpendingPolicy(max_per_tx_cents=50000, max_per_day_cents=200000)

    def test_allow(self):
        ok, why = self.p.check(2500, 0)
        self.assertTrue(ok)
        self.assertEqual(why, "ok")

    def test_per_tx_bound(self):
        ok, why = self.p.check(50001, 0)
        self.assertFalse(ok)
        self.assertIn("per-transaction", why)
        ok, _ = self.p.check(50000, 0)
        self.assertTrue(ok)  # boundary inclusive

    def test_daily_bound(self):
        ok, why = self.p.check(1000, 200000)
        self.assertFalse(ok)
        self.assertIn("daily", why)
        ok, _ = self.p.check(1000, 199000)
        self.assertTrue(ok)

    def test_nonpositive(self):
        for bad in (0, -100):
            ok, why = self.p.check(bad, 0)
            self.assertFalse(ok)
            self.assertIn("positive", why)

    def test_int_only(self):
        ok, why = self.p.check(25.5, 0)
        self.assertFalse(ok)

    def test_credential_stub(self):
        good = json.dumps({"agent_id": "a1", "clearance": "L2", "exp": time.time() + 3600})
        ok, _ = policy_mod.verify_rider_credential(good)
        self.assertTrue(ok)
        bad_exp = json.dumps({"agent_id": "a1", "clearance": "L2", "exp": time.time() - 1})
        ok, why = policy_mod.verify_rider_credential(bad_exp)
        self.assertFalse(ok)
        self.assertIn("expired", why)
        ok, _ = policy_mod.verify_rider_credential("not json")
        self.assertFalse(ok)
        ok, _ = policy_mod.verify_rider_credential(json.dumps({"agent_id": "a1"}))
        self.assertFalse(ok)


class TestReceipt(unittest.TestCase):
    def test_roundtrip(self):
        key = os.urandom(32)
        payload = {"agent_id": "a1", "amount_cents": 2500}
        sig = receipt_mod.sign_receipt(payload, key)
        self.assertIsInstance(sig, str)
        self.assertEqual(len(sig), 64)
        rcpt = dict(payload, signature=sig)
        self.assertTrue(receipt_mod.verify_receipt(rcpt, key))

    def test_tamper(self):
        key = os.urandom(32)
        payload = {"agent_id": "a1", "amount_cents": 2500}
        rcpt = dict(payload, signature=receipt_mod.sign_receipt(payload, key))
        rcpt["amount_cents"] = 2501
        self.assertFalse(receipt_mod.verify_receipt(rcpt, key))

    def test_wrong_key(self):
        rcpt = {"a": 1, "signature": receipt_mod.sign_receipt({"a": 1}, os.urandom(32))}
        self.assertFalse(receipt_mod.verify_receipt(rcpt, os.urandom(32)))

    def test_make_receipt(self):
        os.environ["RECEIPT_KEY"] = os.urandom(32).hex()
        receipt_mod.reset_key_cache()
        r = receipt_mod.make_receipt("a1", "ORDER-1", "CAP-1", 2500, "USD")
        self.assertEqual(r["amount_cents"], 2500)
        self.assertIn("signature", r)
        self.assertIn("timestamp", r)
        key = bytes.fromhex(os.environ["RECEIPT_KEY"])
        self.assertTrue(receipt_mod.verify_receipt(r, key))
        del os.environ["RECEIPT_KEY"]
        receipt_mod.reset_key_cache()


if __name__ == "__main__":
    unittest.main(verbosity=2)
