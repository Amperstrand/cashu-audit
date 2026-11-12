#!/usr/bin/env /usr/bin/python3
"""Post-deploy certification for testnut (2026-10-31).

Verifies the wire identities of everything landed on cashu-cf main
through 6befce4 (A1 malformed-B_ 400s, A2 request bounds, B2
restore-empty mirror, B3 NUT-15 no-false-ad). Run BEFORE deploy: the
three changed legs FAIL (script self-test). Run AFTER deploy: all PASS.

Usage: /usr/bin/python3 certify_testnut.py [--base https://testnut.cashu.exchange]
"""
import json, sys, secrets, time, uuid, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "must-gap-vectors"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "conformance"))
import must_gap_vectors as mg
from coincurve import PrivateKey

def out(amount, kid, malformed=False):
    s = secrets.token_hex(16); Y = mg.hash_to_curve(s); r = PrivateKey()
    B_ = mg.p_add(Y, r.public_key.format()).hex()
    if malformed: B_ = "zz" + B_[2:]
    return {"amount": amount, "B_": B_, "id": kid}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://testnut.cashu.exchange")
    base = ap.parse_args().base
    results = []

    def check(name, ok, detail):
        results.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")

    ks = json.loads(mg.http("GET", f"{base}/v1/keys")[1])["keysets"]
    ks = [k for k in ks if k.get("unit") == "sat"][0]; kid = ks["id"]

    # A1: malformed B_ (single + batch) with a PAID quote -> 400, not 500
    st, b = mg.http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": 4, "unit": "sat"})
    q = json.loads(b)["quote"]
    for _ in range(30):
        st, b = mg.http("GET", f"{base}/v1/mint/quote/bolt11/{q}")
        if st == 200 and json.loads(b).get("state") == "PAID": break
        time.sleep(1)
    st, b = mg.http("POST", f"{base}/v1/mint/bolt11", {"quote": q, "outputs": [out(4, kid, True)]})
    check("A1 single malformed-B_ -> 400", st == 400, f"{st} {b[:90]}")
    st, b = mg.http("POST", f"{base}/v1/mint/bolt11/batch", {"quotes": [q], "outputs": [out(4, kid, True)]})
    check("A1 batch malformed-B_ -> 400", st == 400, f"{st} {b[:90]}")

    # A2: batch-fetch loops capped at 50 (11014)
    ids = [str(uuid.uuid4()) for _ in range(51)]
    st, b = mg.http("POST", f"{base}/v1/mint/quotes", {"ids": ids})
    check("A2 mint/quotes 51 ids -> 400/11014", st == 400 and "11014" in b, f"{st} {b[:90]}")

    # NUT-04 (2026-10-31 finding): quote must read ISSUED after a successful mint
    # NUT-04 (#118, 2026-11-11): the NUT-29 batch check endpoint (the one coco
    # 2.0+ polls) MUST carry amount_paid/amount_issued/updated_at — coco
    # claimability is amount_paid - amount_issued, state string not consulted;
    # fields absent = PAID quote permanently unclaimable. Pre-deploy baseline
    # banked in research/evidence/2026-11-11-coco-drill/wire.jsonl.
    st, b = mg.http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": 4, "unit": "sat"})
    if st == 200:
        q3 = json.loads(b)["quote"]
        for _ in range(30):
            st, b = mg.http("GET", f"{base}/v1/mint/quote/bolt11/{q3}")
            if st == 200 and json.loads(b).get("state") == "PAID": break
            time.sleep(1)
        st, b = mg.http("POST", f"{base}/v1/mint/quote/bolt11/check", {"quotes": [q3]})
        ent = json.loads(b)[0] if st == 200 and b.startswith("[") else {}
        ua_at_paid = ent.get("updated_at")
        check("NUT-04 #118 check fields present (PAID)",
              st == 200 and ent.get("amount_paid") == 4 and ent.get("amount_issued") == 0
              and isinstance(ent.get("updated_at"), int),
              f"{st} ap={ent.get('amount_paid')!r} ai={ent.get('amount_issued')!r} ua={ent.get('updated_at')!r}")
        oK = out(4, kid)
        st, b = mg.http("POST", f"{base}/v1/mint/bolt11", {"quote": q3, "outputs": [oK]})
        mint_ok = st == 200
        st, b = mg.http("GET", f"{base}/v1/mint/quote/bolt11/{q3}")
        g3 = json.loads(b) if st == 200 else {}
        # Re-pinned 2026-11-11: NUT-04 PR #377 (2026-07-03) dropped the state
        # enum as the contract — accounting is. Pre-deploy baseline (banked,
        # research/evidence/2026-11-11-coco-drill/get-path-stale-accounting.txt):
        # GET served state=PAID, amount_issued=0, updated_at unmoved after a
        # full mint (stale). If this stays RED post-deploy, the staleness is
        # live-on-main (own issue), not deploy-vintage.
        check("NUT-04 #377-epoch GET accounting after full mint",
              mint_ok and g3.get("amount_paid") == 4 and g3.get("amount_issued") == 4
              and isinstance(g3.get("updated_at"), int),
              f"mint={mint_ok} ap={g3.get('amount_paid')!r} ai={g3.get('amount_issued')!r} ua={g3.get('updated_at')!r} state={g3.get('state')!r}")
        st, b = mg.http("POST", f"{base}/v1/mint/quote/bolt11/check", {"quotes": [q3]})
        ent = json.loads(b)[0] if st == 200 and b.startswith("[") else {}
        check("NUT-04 #118 check fields present (ISSUED)",
              st == 200 and ent.get("amount_paid") == 4 and ent.get("amount_issued") == 4
              and isinstance(ent.get("updated_at"), int)
              and ent.get("updated_at") > (ua_at_paid or 0),
              f"{st} ap={ent.get('amount_paid')!r} ai={ent.get('amount_issued')!r} ua={ent.get('updated_at')!r} (paid-time ua={ua_at_paid})")
    else:
        check("NUT-04 #377-epoch GET accounting after full mint", False, f"quote create {st}")

    # B2: restore-empty -> 200 with empty arrays
    st, b = mg.http("POST", f"{base}/v1/restore", {"outputs": []})
    ok = st == 200 and json.loads(b) == {"outputs": [], "signatures": []}
    check("B2 restore-empty -> 200 empty", ok, f"{st} {b[:90]}")

    # B3: fakewallet backend must NOT advertise NUT-15
    st, b = mg.http("GET", f"{base}/v1/info")
    info = json.loads(b)
    nuts = info.get("nuts", {})
    check("B3 no false NUT-15 ad (fakewallet)", "15" not in nuts, f"nut15={'present' if '15' in nuts else 'absent'}")

    # Regression guards: unchanged identities
    p, e = mg.mint_proofs(base, ks, {64: [f"cert-{secrets.token_hex(4)}"]})
    check("regression: mint sanity", not e, e[:80] if e else "64 sat minted")
    if not e:
        # fee-correct shape: testnut fee is 1 sat -> outputs sum 63 (keyed amounts)
        payload = {"inputs": p, "outputs": [out(a, kid) for a in (32, 16, 8, 4, 2, 1)]}
        st, b = mg.http("POST", f"{base}/v1/swap", payload)
        check("regression: swap 200", st == 200, f"{st} {b[:60] if st != 200 else 'ok'}")
        if st == 200:
            st2, b2 = mg.http("POST", f"{base}/v1/swap", payload)
            check("regression: swap replay cached 200", st2 == 200 and b2 == b, f"{st2} identical={b2 == b}")
    p2, e2 = mg.mint_proofs(base, ks, {64: [f"certk-{secrets.token_hex(4)}"]})
    if not e2:
        st, b = mg.http("POST", f"{base}/v1/swap", {"inputs": p2, "outputs": [out(63, kid), out(1, kid)]})
        check("regression: keyless still rejected", st != 200, f"{st} {b[:70]}")

    # Standing coco crash-drill leg (owner-approved 2026-11-11): drive a
    # REAL coco wallet against this mint — mint, crash mid-rollback (proxy
    # 502s every reclaim attempt), fresh-process startup auto-recovery.
    # Proven harness; requires bun + a pinned coco checkout (default
    # ~/src/upstream-cache/coco @ 2d6aa583). SKIPs (recorded, never silent)
    # when the toolchain is absent — a missing drill tool is not a mint
    # regression.
    import glob as _glob
    import os as _os
    import re as _re
    import shutil as _shutil
    import socket as _socket
    import subprocess as _sp
    import tempfile as _tempfile
    import time as _time

    def _drill_leg():
        bun = _shutil.which("bun")
        coco = _os.path.expanduser(_os.environ.get("COCO_DIR", "~/src/upstream-cache/coco"))
        harness = _os.path.join(_os.path.dirname(__file__), "..", "live-mint-matrix", "coco-crash-drill")
        if not bun or not _os.path.exists(_os.path.join(coco, "packages", "core", "index.ts")):
            return ("coco crash-drill (standing)", False,
                    f"SKIP-class: toolchain absent (bun={'yes' if bun else 'no'}, coco clone={'yes' if _os.path.exists(coco) else 'no'})")
        run = _tempfile.mkdtemp(prefix="coco-drill-")
        proxy = None
        try:
            _shutil.copy(_os.path.join(harness, "drill.ts"), run)
            _shutil.copy(_os.path.join(harness, "drill-proxy.ts"), run)
            _os.symlink(coco, _os.path.join(run, "coco"))
            with _socket.socket() as s:
                s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
            env = {**_os.environ, "DRILL_PORT": str(port), "DRILL_UPSTREAM": base}
            proxy = _sp.Popen([bun, "drill-proxy.ts"], cwd=run, env=env,
                              stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
            for _ in range(40):
                try:
                    with _socket.create_connection(("127.0.0.1", port), timeout=1):
                        break
                except OSError:
                    _time.sleep(0.25)
            else:
                return ("coco crash-drill (standing)", False, "proxy never listened")
            p1 = _sp.run([bun, "drill.ts", "phase1"], cwd=run, env=env,
                         capture_output=True, text=True, timeout=300)
            out = p1.stdout + p1.stderr
            m = _re.search(r"SEND_ID=(\S+)", out)
            send_id = m.group(1) if m else None
            persisted = "persisted send state: rolling_back" in out
            minted = 'balance after mint: {"spendable":"21"' in out
            if not (p1.returncode == 0 and minted and persisted and send_id):
                return ("coco crash-drill (standing)", False,
                        f"phase1 failed (rc={p1.returncode}, minted={minted}, persisted={persisted}): {out[-300:]}")
            proxy.terminate(); proxy.wait(timeout=10); proxy = None
            env2 = {**env, "INJECT_OFF": "1"}
            proxy = _sp.Popen([bun, "drill-proxy.ts"], cwd=run, env=env2,
                              stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
            p2 = _sp.run([bun, "drill.ts", "phase2", send_id], cwd=run, env=env2,
                         capture_output=True, text=True, timeout=300)
            out2 = p2.stdout + p2.stderr
            recovered = ("state after recovery.run(): rolled_back" in out2
                         or "state before recovery: rolled_back" in out2)
            balance19 = '"total":"19"' in out2
            swaps = []
            for line in open(_os.path.join(run, "wire.jsonl")):
                e = json.loads(line)
                if e.get("path") == "/v1/swap":
                    swaps.append(e)
            injected = [s_ for s_ in swaps if s_.get("injected")]
            forwarded = [s_ for s_ in swaps if not s_.get("injected")
                         and s_.get("status") == 200
                         and len(json.loads(s_.get("reqBody", '{"inputs":[]}')).get("inputs", [])) == 2]
            replay_identical = bool(injected) and bool(forwarded) and any(
                f_["reqBody"] == i_["reqBody"] for f_ in forwarded for i_ in injected)
            ok = recovered and balance19 and replay_identical
            return ("coco crash-drill (standing)", ok,
                    f"minted=21 persisted=rolling_back recovered={recovered} balance19={balance19} "
                    f"replay_identical={replay_identical} (injected={len(injected)} forwarded={len(forwarded)})")
        finally:
            if proxy is not None:
                proxy.terminate()
                try:
                    proxy.wait(timeout=10)
                except Exception:
                    proxy.kill()
            _shutil.rmtree(run, ignore_errors=True)

    try:
        _name, _ok, _detail = _drill_leg()
    except Exception as _e:  # noqa: BLE001
        _name, _ok, _detail = "coco crash-drill (standing)", False, f"leg error: {_e.__class__.__name__}: {str(_e)[:120]}"
    check(_name, _ok, _detail)

    fails = [r for r in results if not r[1]]
    print(f"\n{'=' * 60}\nCERTIFICATION: {len(results) - len(fails)}/{len(results)} PASS" +
          (" — DEPLOY NOT LIVE YET (expected pre-deploy)" if fails else " — CLEAN"))
    return 1 if fails else 0

if __name__ == "__main__":
    raise SystemExit(main())
