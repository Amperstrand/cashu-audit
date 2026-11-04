#!/usr/bin/env python3
"""Wire probe: NUT-17 subscription kinds × melt-change issuance (cashu-audit #68 B2/B3).

Measures two things per arm, identity-stamped at run start:

1. NUT-17 /v1/ws — which ``subscribe`` kinds the mint accepts:
   ``bolt11_mint_quote`` (the spec'd baseline), ``bolt11_melt_quote``
   and ``proof_state``. gonuts v0.16.0 accepts ONLY the mint-quote kind.

2. NUT-08 melt change — melt with inputs that overpay the invoice and
   NUT-08 blank outputs in the request: does the response carry signed
   ``change``? gonuts never signs change on any path (no writer of the
   response field); cdk/nutshell return it.

Usage:
    python3 nut17_meltchange_probe.py --arm name=url [--arm name=url ...] \
        [--out results/nut17-meltchange/<ts>.json]

Run from conformance/ (sys.path='.'). Not a scenario: gonuts fails the
melt-change row by design — evidence lands in the findings doc +
DIVERGENCE-REGISTRY, per the error_identity_probe.py precedent.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

import requests
import websocket

sys.path.insert(0, ".")

from conformance.builder import ProofBuilder  # noqa: E402
from conformance.client import MintClient  # noqa: E402
from conformance.crypto import generate_secret, hash_to_curve  # noqa: E402

WS_TIMEOUT = 6


def ws_probe_kinds(mint: MintClient) -> dict:
    out = {}
    base = mint.base_url.replace("http", "ws", 1) + "/v1/ws"
    quote_id = mint.mint_quote(4)["quote"]
    # a real curve point for proof_state filters — cdk validates Y as a
    # point at parse time and answers -32700 for non-point hex
    real_y = hash_to_curve(b"nut17-probe-y").format(compressed=True).hex()
    for kind in ("bolt11_mint_quote", "bolt11_melt_quote", "proof_state"):
        # fresh connection per kind: no stale notifications from a
        # previous subscription can be misattributed
        try:
            ws = websocket.create_connection(base, timeout=WS_TIMEOUT)
        except Exception as e:
            out[kind] = {"error": f"connect failed: {str(e)[:60]}"}
            continue
        ws.settimeout(WS_TIMEOUT)
        try:
            sub_id = f"probe-{uuid.uuid4().hex[:8]}"
            filters = [quote_id] if kind != "proof_state" else [real_y]
            req = {
                "jsonrpc": "2.0", "method": "subscribe", "id": int(time.time()) % 100000,
                "params": {"kind": kind, "subId": sub_id, "filters": filters},
            }
            ws.send(json.dumps(req))
            verdict = {"ack": False, "error": None, "notification": False, "notif_subId": None}
            deadline = time.time() + WS_TIMEOUT
            while time.time() < deadline:
                try:
                    raw = ws.recv()
                except Exception:
                    break
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                if msg.get("id") == req["id"]:
                    if isinstance(msg.get("error"), dict):
                        verdict["error"] = msg["error"]
                    elif isinstance(msg.get("result"), dict) and msg["result"].get("status") == "OK":
                        verdict["ack"] = True
                    break
                params = msg.get("params")
                if msg.get("method") == "subscribe" and isinstance(params, dict):
                    verdict["notification"] = True
                    verdict["notif_subId"] = params.get("subId")
                    if params.get("subId") == sub_id:
                        break
            out[kind] = verdict
        finally:
            try:
                ws.close()
            except Exception:
                pass
    return out


def melt_change_probe(mint: MintClient, invoice_src: MintClient) -> dict:
    """Melt 8 sats of inputs against a 2-sat invoice with blank outputs.

    The invoice comes from a nutshell arm: mainnet-prefix invoices with
    payment_secret decode on every arm (gonuts signet invoices are
    rejected by cdk as "Invalid payment method"). Inputs are sized to
    clear every arm's fee reserve (cdk/ns FakeWallets reserve 2 sats on
    a 2-sat invoice; a 4-sat input set is underfunded there).
    """
    builder = ProofBuilder(mint)
    proofs = builder.mint_proofs(8)
    invoice = invoice_src.mint_quote(2).get("request")
    if not invoice:
        return {"error": "no invoice source"}
    try:
        quote = mint.melt_quote(invoice)
    except RuntimeError as e:
        return {"error": str(e)[:160]}

    outputs = builder.outputs_to_api(
        builder.create_outputs(4, lambda: generate_secret())
    )
    code, body = mint.melt(
        quote["quote"], [p.to_dict() for p in proofs], outputs
    )
    return {
        "quote_fee_reserve": quote.get("fee_reserve"),
        "inputs_total": sum(p.amount for p in proofs),
        "invoice_amount": 2,
        "blank_outputs": len(outputs),
        "http": code,
        "state": body.get("state") if isinstance(body, dict) else None,
        "change": body.get("change") if isinstance(body, dict) else None,
        "change_len": len(body.get("change") or []) if isinstance(body, dict) else 0,
        "error_body": None if (isinstance(body, dict) and body.get("state")) else str(body)[:160],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True, help="name=url")
    ap.add_argument("--invoice-src", required=True,
                    help="name of the arm whose invoices are melted (a nutshell arm: "
                         "mainnet-prefix invoices decode on every arm)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    arms = {}
    for spec in args.arm:
        name, url = spec.split("=", 1)
        arms[name] = MintClient(url)
    if args.invoice_src not in arms:
        ap.error(f"--invoice-src {args.invoice_src} not among --arm entries")
    src = arms[args.invoice_src]

    report: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "arms": {}}
    for name, mint in arms.items():
        info = mint.get_mint_info()
        report["arms"][name] = {
            "url": mint.base_url,
            "identity": f"{info.get('name', 'unnamed')} / {info.get('version', '?')}",
            "nut17_kinds": ws_probe_kinds(mint),
            "melt_change": melt_change_probe(
                mint, src
            ),
        }
        print(name, json.dumps(report["arms"][name], default=str)[:200])

    out = args.out or f"results/nut17-meltchange/probe-{int(time.time())}.json"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=1, default=str))
    print("written", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
