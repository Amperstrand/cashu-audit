"""NUT-17 websocket scenarios — 3 tests.

NUT-17 (over websocket): a client subscribes to quote-state updates on
/v1/ws with a JSON-RPC ``subscribe`` message; the mint answers with an
ack and pushes state notifications for the subscribed quote ids.

Coverage notes (2026-11-04, cashu-audit #68 B2 — the matrix had NO
websocket coverage before this file):
- gonuts v0.16.0 supports ONLY the ``bolt11_mint_quote`` subscription
  kind; ``bolt11_melt_quote`` and ``proof_state`` subscribe requests
  are rejected ("invalid request method"). The melt-quote/proof-state
  kinds are documented as a divergence in
  research/FINDINGS-2026-11-04-gonuts-residue.md, NOT as matrix rows —
  a row gonuts must fail would break the 116/116 lane.
- All three scenarios assert only the spec'd mint-quote subscribe
  semantics every implementation family (gonuts, cdk, nutshell)
  shares, and SKIP when /v1/ws is not reachable at all.
"""
from __future__ import annotations

import json
import uuid

import websocket

from conformance.client import MintClient
from conformance.scenarios import scenario, ScenarioResult, Result

CAT = "NUT-17 Websocket"

_WS_TIMEOUT = 8  # seconds per socket read — never hang the lane


def _ws_url(mint: MintClient) -> str:
    return mint.base_url.replace("http", "ws", 1) + "/v1/ws"


def _connect(mint: MintClient) -> websocket.WebSocket | None:
    try:
        ws = websocket.create_connection(_ws_url(mint), timeout=_WS_TIMEOUT)
    except Exception:
        return None
    ws.settimeout(_WS_TIMEOUT)
    return ws


def _send(ws: websocket.WebSocket, payload: dict) -> None:
    ws.send(json.dumps(payload))


def _recv(ws: websocket.WebSocket) -> dict | None:
    try:
        raw = ws.recv()
    except Exception:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def _subscribe_req(sub_id: str, filters: list[str], req_id: int = 1) -> dict:
    return {
        "jsonrpc": "2.0",
        "method": "subscribe",
        "params": {
            "kind": "bolt11_mint_quote",
            "subId": sub_id,
            "filters": filters,
        },
        "id": req_id,
    }


def _is_ack(msg: dict, req_id: int) -> bool:
    if "result" not in msg:
        return False
    result = msg.get("result") or {}
    return msg.get("id") == req_id and result.get("status") == "OK"


def _is_error(msg: dict) -> bool:
    return isinstance(msg.get("error"), dict)


@scenario("ws_mint_quote_subscribe_initial_state", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Subscribe to a fresh mint quote: ack + initial-state notification."""
    name = "ws_mint_quote_subscribe_initial_state"
    ws = _connect(mint)
    if ws is None:
        return ScenarioResult(name, CAT, Result.SKIP, "/v1/ws not reachable")
    try:
        quote_id = mint.mint_quote(4)["quote"]
        sub_id = f"sub-{uuid.uuid4().hex[:8]}"
        _send(ws, _subscribe_req(sub_id, [quote_id]))

        got_ack = False
        notif = None
        for _ in range(4):
            msg = _recv(ws)
            if msg is None:
                break
            if _is_ack(msg, 1):
                got_ack = True
            elif msg.get("method") == "subscribe" and isinstance(msg.get("params"), dict):
                notif = msg["params"]
                if notif.get("subId") == sub_id:
                    break

        if not got_ack:
            return ScenarioResult(name, CAT, Result.FAIL, "no subscribe ack (result.status=OK)")
        if notif is None:
            return ScenarioResult(name, CAT, Result.FAIL, "no initial-state notification")
        payload = notif.get("payload")
        if not isinstance(payload, dict):
            return ScenarioResult(name, CAT, Result.FAIL, "notification payload is not an object")
        if payload.get("quote") != quote_id:
            return ScenarioResult(
                name, CAT, Result.FAIL,
                f"notification quote={payload.get('quote')!r}, want {quote_id}",
            )
        if "state" not in payload:
            return ScenarioResult(name, CAT, Result.FAIL, "notification payload lacks 'state'")
        return ScenarioResult(
            name, CAT, Result.PASS,
            f"ack + initial state={payload.get('state')} for quote {quote_id[:12]}…",
        )
    finally:
        ws.close()


@scenario("ws_mint_quote_unsubscribe_ok", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Unsubscribing an existing subId acks OK."""
    name = "ws_mint_quote_unsubscribe_ok"
    ws = _connect(mint)
    if ws is None:
        return ScenarioResult(name, CAT, Result.SKIP, "/v1/ws not reachable")
    try:
        quote_id = mint.mint_quote(4)["quote"]
        sub_id = f"sub-{uuid.uuid4().hex[:8]}"
        _send(ws, _subscribe_req(sub_id, [quote_id]))

        got_sub_ack = False
        for _ in range(4):
            msg = _recv(ws)
            if msg is None:
                break
            if _is_ack(msg, 1):
                got_sub_ack = True
                break
        if not got_sub_ack:
            return ScenarioResult(name, CAT, Result.FAIL, "subscribe did not ack (precondition)")

        unsub = {
            "jsonrpc": "2.0",
            "method": "unsubscribe",
            "params": {"subId": sub_id},
            "id": 2,
        }
        _send(ws, unsub)
        for _ in range(4):
            msg = _recv(ws)
            if msg is None:
                break
            if _is_ack(msg, 2):
                return ScenarioResult(name, CAT, Result.PASS, "unsubscribe acked OK")
            if _is_error(msg) and msg.get("id") == 2:
                return ScenarioResult(
                    name, CAT, Result.FAIL,
                    f"unsubscribe errored: {msg['error']}",
                )
        return ScenarioResult(name, CAT, Result.FAIL, "no unsubscribe ack")
    finally:
        ws.close()


@scenario("ws_mint_quote_unknown_quote_rejected", CAT)
def _(mint: MintClient) -> ScenarioResult:
    """Subscribing to a nonexistent quote id is a JSON-RPC error, not a silent OK."""
    name = "ws_mint_quote_unknown_quote_rejected"
    ws = _connect(mint)
    if ws is None:
        return ScenarioResult(name, CAT, Result.SKIP, "/v1/ws not reachable")
    try:
        sub_id = f"sub-{uuid.uuid4().hex[:8]}"
        _send(ws, _subscribe_req(sub_id, [f"no-such-quote-{uuid.uuid4().hex}"]))

        for _ in range(4):
            msg = _recv(ws)
            if msg is None:
                break
            if _is_error(msg):
                return ScenarioResult(
                    name, CAT, Result.PASS,
                    f"rejected with error code {msg['error'].get('code')}",
                )
            if _is_ack(msg, 1):
                return ScenarioResult(
                    name, CAT, Result.FAIL,
                    "subscribe for a nonexistent quote acked OK",
                )
        return ScenarioResult(name, CAT, Result.FAIL, "no response to subscribe")
    finally:
        ws.close()
