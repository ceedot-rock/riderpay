"""Flask demo server. SANDBOX ONLY — no real-money paths exist in this codebase."""

import json
import os

from flask import Flask, jsonify, request, send_from_directory

import agent as agent_mod
import paypal_client
import policy as policy_mod
import receipt as receipt_mod

assert "sandbox" in paypal_client.BASE_URL, "server refuses non-sandbox PayPal base URL"

app = Flask(__name__, static_folder="static")

# Demo policy: $500/tx, $2,000/day. Override via env (integer cents).
POLICY = policy_mod.SpendingPolicy(
    max_per_tx_cents=int(os.environ.get("RIDERPAY_MAX_TX_CENTS", "50000")),
    max_per_day_cents=int(os.environ.get("RIDERPAY_MAX_DAY_CENTS", "200000")),
)

# In-memory demo ledger: agent_id -> cents spent today. Not durable; demo only.
_spent_today: dict = {}


@app.get("/api")
def api_about():
    return jsonify({
        "service": "riderpay",
        "about": "Agentic PayPal sandbox payments: signed Rider credential, "
                 "integer-cents math, spending policy, HMAC-signed receipts.",
        "sandbox": "sandbox" in paypal_client.BASE_URL,
        "endpoints": [
            {"method": "GET",  "path": "/api",          "description": "this service/about/endpoints document"},
            {"method": "GET",  "path": "/healthz",      "description": "liveness probe"},
            {"method": "GET",  "path": "/",             "description": "demo UI"},
            {"method": "POST", "path": "/api/pay",     "description": "instruction + credential -> PayPal order + approval URL"},
            {"method": "POST", "path": "/api/capture", "description": "capture order -> HMAC-signed receipt"},
        ],
    })


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True, "sandbox": "sandbox" in paypal_client.BASE_URL})


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/pay")
def api_pay():
    body = request.get_json(force=True, silent=True) or {}
    instruction = body.get("instruction", "")
    credential = body.get("credential", "")
    if not instruction or not credential:
        return jsonify({"status": "refused", "reason": "instruction and credential required"}), 400
    agent_id = policy_mod.credential_agent_id(credential)
    result = agent_mod.handle_instruction(
        instruction, credential, POLICY,
        spent_today_cents=_spent_today.get(agent_id or "", 0),
    )
    if result.get("status") == "awaiting_approval" and agent_id:
        _spent_today[agent_id] = _spent_today.get(agent_id, 0) + result["amount_cents"]
    return jsonify(result)


@app.post("/api/capture")
def api_capture():
    body = request.get_json(force=True, silent=True) or {}
    order_id = body.get("order_id", "")
    agent_id = body.get("agent_id", "")
    if not order_id:
        return jsonify({"status": "error", "reason": "order_id required"}), 400
    try:
        rcpt = agent_mod.capture_and_receipt(order_id, agent_id)
    except paypal_client.PayPalError as e:
        return jsonify({"status": "error", "reason": str(e)}), 502
    return jsonify({"status": "captured", "receipt": rcpt})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5057")))
