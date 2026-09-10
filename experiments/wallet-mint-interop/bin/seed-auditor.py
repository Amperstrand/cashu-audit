#!/usr/bin/env python3
"""Seed the cashu-auditor with tokens from battery mints.
Run from ~/cashu-auditor with poetry.
"""
import asyncio, json, os, sys, urllib.request
sys.path.insert(0, os.path.expanduser("~/cashu-auditor"))
os.chdir(os.path.expanduser("~/cashu-auditor"))

MINT_PORTS = [35000, 35001, 35002, 35003, 35004, 35005, 35006, 35007, 35008]
AUDITOR = "http://127.0.0.1:8000"
AMOUNT = 100

async def mint_and_submit(port):
    url = f"http://127.0.0.1:{port}"
    from cashu.wallet.wallet import Wallet
    w = await Wallet.with_db(url, f"/tmp/seed-{port}")
    await w.load_mint()
    quote = await w.request_mint(AMOUNT)
    await asyncio.sleep(2)  # FakeWallet pays instantly
    proofs = await w.mint(AMOUNT, quote.id)
    token = await w.serialize_proofs(proofs)
    print(f"  minted {AMOUNT} sats from :{port}, token len={len(token)}")
    # POST to auditor
    req = urllib.request.Request(
        f"{AUDITOR}/mints/",
        data=json.dumps({"token": token}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
        print(f"  auditor: {json.dumps(body)[:120]}")
    return True

async def main():
    for port in MINT_PORTS:
        try:
            await mint_and_submit(port)
        except Exception as e:
            print(f"  :{port} FAILED: {e}")

asyncio.run(main())
