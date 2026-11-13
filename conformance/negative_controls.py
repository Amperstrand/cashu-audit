#!/usr/bin/env python3
"""negative_controls.py — mutation testing for our own conformance scenarios.

The murdawk method, mechanized: every scenario cited as evidence must FAIL
against a response that violates its claim and PASS against the honest one.
He found (twice) that ours didn't: any-second-200 passed as "cached";
type-coerced bodies passed as "identical". This runner fronts an honest arm
with a mutating proxy and replays selected scenarios per mutation — a
surviving mutant is a false-positive scenario and a red exit.

Usage: negative_controls.py [--arm-url URL]   (default: boot a local cdk 0.18.3 arm)
"""
from __future__ import annotations
import argparse
import copy
import io
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from conformance.client import MintClient  # noqa: E402
from conformance.scenarios import all_scenarios  # noqa: E402  (the registry module)
import pkgutil  # noqa: E402
import importlib  # noqa: E402
import scenarios as _pkg  # noqa: E402  (the scenario-modules package on sys.path)
for _f, _n, _p in pkgutil.iter_modules(_pkg.__path__):  # registry side effects
    importlib.import_module(f"scenarios.{_n}")
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402
import urllib.request  # noqa: E402


# ---------- mutation taxonomy (grow as new classes are found) ----------
def mutate(doc, mode, ctx):
    """Return a mutated copy of a JSON response doc, or None to pass through."""
    if mode == "replay_nonidentical" and ctx.get("melt_posts", 0) >= 2 and "change" in doc:
        m = copy.deepcopy(doc)
        if isinstance(m.get("change"), list) and m["change"]:
            # type-coercion mutation: a JSON boolean where a number was
            # (murdawk round 2: Python True == 1 defeats naive equality)
            m["change"][0]["amount"] = (m["change"][0].get("amount") or 1) is not None and True
        return m
    if mode == "change_minus_one" and isinstance(doc.get("change"), list) and doc["change"]:
        m = copy.deepcopy(doc)
        m["change"][0]["amount"] = max(0, m["change"][0].get("amount", 0) - 1)
        return m
    if mode == "change_type_float" and isinstance(doc.get("change"), list) and doc["change"]:
        m = copy.deepcopy(doc)
        m["change"][0]["amount"] = float(m["change"][0].get("amount", 0))
        return m
    return None


class ProxyHandler(BaseHTTPRequestHandler):
    upstream: str = None
    mode: str = None
    ctx: dict = None

    def log_message(self, *a):
        pass

    def _forward(self, body=None):
        url = self.upstream + self.path
        req = urllib.request.Request(url, data=body, method=self.command)
        for k, v in self.headers.items():
            if k.lower() not in ("host", "content-length", "accept-encoding"):
                req.add_header(k, v)
        req.add_header("Accept-Encoding", "identity")
        req.add_header("User-Agent", "cashu-conformance-lane/1.0")
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                status, rb = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, rb = e.code, e.read()
        if self.command == "POST" and self.path.endswith("/v1/melt/bolt11"):
            self.ctx["melt_posts"] = self.ctx.get("melt_posts", 0) + 1
        try:
            doc = json.loads(rb)
            m = mutate(doc, self.mode, self.ctx) if self.mode != "honest" else None
            if m is not None:
                rb = json.dumps(m).encode()
        except Exception:
            pass
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(rb)))
        self.end_headers()
        self.wfile.write(rb)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        self._forward(self.rfile.read(n) if n else None)

    def do_GET(self):
        self._forward()


def boot_arm():
    from version_matrix import Arm
    arm = Arm("nc-target", "cdk")
    arm.image = "cashubtc/mintd:0.18.3"
    arm.bring_up()
    return arm


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-url")
    a = ap.parse_args()

    arm = None
    upstream = a.arm_url
    oracle = None
    if not upstream:
        arm = boot_arm()
        upstream = arm.url
        from version_matrix import Arm as _A
        oracle = _A("nc-oracle", "cdk")
        oracle.image = "cashubtc/mintd:0.18.3"
        oracle.bring_up()
    print(f"target arm: {upstream} ({getattr(arm, 'identity', 'external')})")

    def make_client(port):
        c = MintClient(f"http://127.0.0.1:{port}", timeout=30)
        c.invoice_oracle = MintClient(oracle.url if oracle else upstream, timeout=30)
        return c

    cases = [
        # (scenario name, mutation, expected verdict under mutation)
        ("melt_replay_returns_cached_response", "honest", "PASS"),
        ("melt_replay_returns_cached_response", "replay_nonidentical", "FAIL"),
        ("melt_change_returned_for_overpay", "honest", "PASS"),
        ("melt_change_returned_for_overpay", "change_minus_one", "FAIL"),
        ("melt_change_returned_for_overpay", "change_type_float", "FAIL"),
    ]
    by_name = {s.name: s for s in all_scenarios()}

    rows, bad = [], 0
    for name, mode, expected in cases:
        ctx: dict = {}
        handler = type("H", (ProxyHandler,), {"upstream": upstream, "mode": mode, "ctx": ctx})
        srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = srv.server_address[1]
        import threading
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        client = make_client(port)
        try:
            res = by_name[name].run(client)
            verdict = res.result.name if hasattr(res.result, "name") else str(res.result)
        except Exception as e:
            verdict = f"ERROR:{type(e).__name__}:{str(e)[:60]}" + (f" @ {traceback.format_exc().splitlines()[-2].strip()[:80]}" if True else "")
        finally:
            srv.shutdown()
        ok = (verdict == expected) or (expected == "PASS" and verdict == "PASS") or \
             (expected == "FAIL" and verdict.startswith("ERROR"))
        # ERROR under mutation = refused uncleanly (crash) — NOT a false
        # positive; flagged for graceful handling, not a surviving mutant.
        note = "ok" if ok else "MUTANT SURVIVED"
        if ok and verdict.startswith("ERROR") and expected == "FAIL":
            note = "ok (refused-by-crash; candidate for graceful handling)"
        rows.append((name, mode, expected, verdict, note))
        if not ok:
            bad += 1
        print(f"  {name} [{mode}] want {expected}: {verdict} -> {note}")

    if arm:
        arm.tear_down()
    if oracle:
        oracle.tear_down()
    print(f"\n{'ALL CONTROLS GREEN' if bad == 0 else f'{bad} MUTANT(S) SURVIVED — false-positive scenarios'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
