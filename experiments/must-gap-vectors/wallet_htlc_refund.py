#!/usr/bin/env python3
"""Wallet-level HTLC refund spend — the corrected d6 test.

Historical 0/108 result was dominated by a driver bug: positional args on
a keyword-only API + nonexistent kwarg names + no spend ever attempted.

This driver does the full flow with the REAL wallet API:
  1. mint 4 sats
  2. create_htlc_lock(preimage_hash=..., locktime_seconds=2,
     locktime_pubkeys=[our_pk]) -> lock to a 2-second refund window
  3. wait 3s (locktime expires)
  4. sign_p2pk_sig_inputs(proofs) -> adds refund witnesses
  5. swap(64) -> observe

Expected (per live raw-protocol vectors):
  nutshell >=0.19 mints: PASS
  cdk mints: FAIL ("Secret is not a HTLC secret" — witness shape, F6)
"""
import asyncio, json, os, secrets, sys, tempfile, time
import hashlib as hlib
from pathlib import Path

ART = Path(os.environ.get("ARTIFACT_DIR", "/tmp/art")); ART.mkdir(parents=True, exist_ok=True)
result = {"flow": "wallet_htlc_refund", "mint": os.environ.get("MINT_URL"), "verdict": None, "reason": ""}

def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)

def finish(code):
    result.setdefault("verdict", {0: "PASS", 1: "FAIL", 127: "SKIP"}.get(code, "ERROR"))
    (ART / "result.json").write_text(json.dumps(result, indent=1))
    sys.exit(code)

async def main():
    import httpx
    _orig_req = httpx.AsyncClient.request
    async def _req(self, method, url, **kw):
        r = await _orig_req(self, method, url, **kw)
        if r.status_code >= 400:
            print(f"WIRE {method} {url} -> {r.status_code} REQ={r.request.content[:1400]!r} RESP={r.text[:200]!r}", flush=True)
        return r
    httpx.AsyncClient.request = _req
    from cashu.wallet.wallet import Wallet
    w = await Wallet.with_db(os.environ["MINT_URL"], tempfile.mkdtemp(prefix="whtlc-"))
    await w.load_mint()
    log("wallet loaded, keysets:", len(w.keysets))

    # 1. mint
    try:
        quote = await w.request_mint(32)
        log("quote ok:", quote.quote[:16])
    except BaseException as e:
        log("request_mint FAILED:", repr(e)[:200]); raise
    # poll until PAID (cdk FakeWallet settles lazily on GET)
    import urllib.request as _u
    for _ in range(20):
        try:
            with _u.urlopen(_u.Request(os.environ["MINT_URL"] + "/v1/mint/quote/bolt11/" + quote.quote), timeout=5) as _r:
                import json as _j
                if _j.load(_r).get("state") == "PAID":
                    log("quote PAID")
                    break
        except Exception:
            pass
        await asyncio.sleep(1)
    try:
        proofs = await w.mint(32, quote.quote)
        log("minted:", sum(p.amount for p in proofs), "sats")
    except SystemExit as e:
        log("mint raised SystemExit:", e); raise
    except BaseException as e:
        import traceback; traceback.print_exc()
        log("mint FAILED:", repr(e)[:200]); raise

    # 2. lock: hash-lock + 2-second refund window to OUR key
    preimage = secrets.token_bytes(32).hex()
    hash_hex = hlib.sha256(bytes.fromhex(preimage)).hexdigest()
    our_pk = w._get_pubkey().hex() if hasattr(w, "_get_pubkey") else None
    if our_pk is None:
        # fallback: derive from wallet private key attribute
        our_pk = w.private_key.public_key.format().hex()
    locked = await w.create_htlc_lock(
        preimage_hash=hash_hex,
        locktime_seconds=2,
        locktime_pubkeys=[our_pk],
        locktime_n_sigs=1,
    )
    log("lock created:", str(locked)[:120])

    # apply the lock: swap into proofs with the HTLC secret
    try:
        keep, send = await w.swap_to_send(proofs, 4, secret_lock=locked, set_reserved=False, include_fees=True)
    except TypeError:
        keep, send = await w.swap_to_send(proofs, 4, secret_lock=locked, set_reserved=False)
    locked_proofs = send
    log("locked proofs:", len(locked_proofs))

    # 3. wait for locktime expiry
    time.sleep(3)

    # 4. sign refund path (wallet collects refund pubkeys incl. ours)
    signed = w.sign_p2pk_sig_inputs(locked_proofs)
    log("signed proofs:", len(signed))
    if not signed:
        result["reason"] = "wallet produced no refund-signed proofs"
        finish(1)

    # 5. spend
    try:
        keep, spent = await w.split(proofs=signed, amount=0)
        log("REFUND SPENT OK: keep", len(keep), "proofs (", sum(p.amount for p in keep), "sats ) send", len(spent))
        result["verdict"] = "PASS"; finish(0)
    except Exception as e:
        result["reason"] = f"swap: {e!r}"[:250]
        log("swap failed:", repr(e)[:250])
        finish(1)

asyncio.run(main())
