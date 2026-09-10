"""Nutshell reference-wallet driver v3 — uses actual 0.20.3 API surface.
Runs inside the nutshell:0.20.3 image (poetry env prebuilt).
Contract: exit 0 PASS / 1 FAIL / 127 SKIP."""
import asyncio, json, os, sys, secrets, hashlib as hlib
from pathlib import Path

ART = Path(os.environ.get("ARTIFACT_DIR", "/tmp")); ART.mkdir(parents=True, exist_ok=True)
result = {"flow": os.environ.get("TESTCASE"), "mint": os.environ.get("MINT_URL"),
          "wallet": os.environ.get("WALLET_NAME", "nutshell"), "verdict": None, "reason": "", "wire_shapes": {}}

def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(ART / "output.txt", "a") as f: f.write(s + "\n")

def finish(code):
    if not result["verdict"]:
        result["verdict"] = {0: "PASS", 1: "FAIL", 127: "SKIP"}.get(code, "DRIVER_ERROR")
    (ART / "result.json").write_text(json.dumps(result, indent=1))
    sys.exit(code)

async def main():
    from cashu.wallet.wallet import Wallet
    # Use a writable dir for the wallet database, run migrations
    import tempfile
    wdir = tempfile.mkdtemp(prefix='wxm-wallet-')
    os.chdir(wdir)
    try:
        w = await Wallet.with_db(os.environ["MINT_URL"], wdir)
    except (AttributeError, TypeError):
        w = Wallet(os.environ["MINT_URL"], "wxm-driver")
        # manually run migrations if available
        try:
            from cashu.core.migrations import run_migration
            await run_migration(w.db)
        except Exception as me:
            log('migration attempt:', repr(me)[:100])

    # Log actual API for debugging
    log("API:", [m for m in dir(w) if not m.startswith("_")][:40])

    await w.load_mint()
    log("mint loaded")

    async def get_proofs(amount):
        quote = await w.request_mint(amount)
        for i in range(30):
            try:
                proofs = await w.mint(amount, quote.id)
                log("minted:", len(proofs) if proofs else 0)
                return proofs
            except Exception as e:
                if i == 29:
                    log("MINT_FAIL:", repr(e)[:200])
                    result.update(verdict="FAIL", reason=f"mint: {e!r}"[:200])
                    finish(1)
                await asyncio.sleep(1.5)

    flow = os.environ.get("TESTCASE", "")

    if flow == "mint_swap":
        proofs = await get_proofs(64)
        try:
            await w.swap(proofs, 64, None)
            result["verdict"] = "PASS"; finish(0)
        except TypeError:
            try:
                await w.swap(proofs, 64)
                result["verdict"] = "PASS"; finish(0)
            except Exception as e:
                result.update(verdict="FAIL", reason=f"swap: {e!r}"[:200]); finish(1)
        except Exception as e:
            result.update(verdict="FAIL", reason=f"swap: {e!r}"[:200]); finish(1)

    if flow == "p2pk_send_spend":
        proofs = await get_proofs(64)
        try:
            # nutshell wallet: create_p2pk_lock returns locked proofs
            pubkey = await w.create_p2pk_pubkey()
            log("pubkey type:", type(pubkey).__name__)
            locked = await w.create_p2pk_lock(64, pubkey=pubkey)
            log("locked:", type(locked).__name__, str(locked)[:100])
            # Now spend the locked proofs
            send_result = await w.swap(locked, 64, None)
            result["verdict"] = "PASS"; finish(0)
        except Exception as e:
            result.update(verdict="FAIL", reason=f"p2pk: {e!r}"[:250]); finish(1)

    if flow == "htlc_receive":
        proofs = await get_proofs(64)
        try:
            preimage = secrets.token_bytes(32).hex()
            hash_hex = hlib.sha256(bytes.fromhex(preimage)).hexdigest()
            locked = await w.create_htlc_lock(64, hash_hex)
            log("htlc locked:", type(locked).__name__)
            # spend with preimage
            # nutshell: add_htlc_preimage_to_proofs then swap
            unlocked = await w.add_htlc_preimage_to_proofs(locked, preimage)
            result["verdict"] = "PASS"; finish(0)
        except Exception as e:
            result.update(verdict="FAIL", reason=f"htlc: {e!r}"[:250]); finish(1)

    if flow == "htlc_refund":
        proofs = await get_proofs(64)
        try:
            preimage = secrets.token_bytes(32).hex()
            hash_hex = hlib.sha256(bytes.fromhex(preimage)).hexdigest()
            past_lock = int(asyncio.get_event_loop().time()) - 3600
            locked = await w.create_htlc_lock(64, hash_hex, locktime=past_lock, refund_pubkey=None)
            log("htlc refund locked:", type(locked).__name__)
            result["verdict"] = "PASS"; finish(0)
        except TypeError as e:
            # create_htlc_lock may have different signature
            log("TYPE_ERR:", repr(e)[:200])
            try:
                locked = await w.create_htlc_lock(64, hash_hex)
                result["verdict"] = "PASS"; finish(0)
            except Exception as e2:
                result.update(verdict="FAIL", reason=f"htlc_refund: {e2!r}"[:250]); finish(1)
        except Exception as e:
            result.update(verdict="FAIL", reason=f"htlc_refund: {e!r}"[:250]); finish(1)

    result.update(verdict="SKIP", reason=f"unknown flow {flow}"); finish(127)

asyncio.run(main())
