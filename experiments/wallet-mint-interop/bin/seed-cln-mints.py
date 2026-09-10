#!/usr/bin/env python3
"""Seed CLN-backed mints with the auditor: create quote, pay via CLN, mint, submit."""
import asyncio, json, os, subprocess, sys, tempfile, urllib.request

AUDITOR = "http://127.0.0.1:8000"
MINTS = [
    ("http://127.0.0.1:35100", "cln-mint-1"),
    ("http://127.0.0.1:35101", "cln-mint-2"),
]

def pay_via_cln(invoice):
    """Pay a bolt11 invoice through the CLN node."""
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "root@inr2.cashu.exchange",
         f"docker exec cln-hub-signet lightning-cli --signet pay {invoice}"],
        capture_output=True, text=True, timeout=30)
    return r.returncode == 0 and "preimage" in r.stdout

async def seed_cln_mint(url, name):
    from cashu.wallet.wallet import Wallet
    wdir = tempfile.mkdtemp(prefix=f"seed-cln-{name}-")
    w = await Wallet.with_db(url, wdir)
    await w.load_mint()

    # Create mint quote
    quote = await w.request_mint(100)
    invoice = getattr(quote, 'request', None) or quote.quote
    print(f"  {name}: quote={quote.quote[:16]} invoice={str(invoice)[:40]}...")

    # The wallet stores the invoice; get it from the mint API
    import urllib.request as ur
    resp = ur.urlopen(f"{url}/v1/mint/quote/bolt11/{quote.quote}", timeout=10)
    qdata = json.loads(resp.read().decode())
    bolt11 = qdata.get('request', '')
    if not bolt11:
        print(f"  {name}: no bolt11 in quote response, keys: {list(qdata.keys())}")
        return False

    # Pay through CLN
    print(f"  {name}: paying {bolt11[:30]}...")
    if not pay_via_cln(bolt11):
        print(f"  {name}: payment failed")
        return False
    print(f"  {name}: paid!")

    # Wait for mint to process
    await asyncio.sleep(3)

    # Mint proofs
    proofs = await w.mint(100, quote.quote)
    token = await w.serialize_proofs(proofs)
    print(f"  {name}: minted {len(proofs)} proofs")

    # Submit to auditor
    req = urllib.request.Request(
        f"{AUDITOR}/mints/",
        data=json.dumps({"token": token}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"  {name}: auditor registered")
    return True

async def main():
    for url, name in MINTS:
        try:
            if await seed_cln_mint(url, name):
                print(f"  {name}: ✅ SEEDED")
            else:
                print(f"  {name}: ❌ FAILED")
        except Exception as e:
            print(f"  {name}: ❌ {e}")

asyncio.run(main())
