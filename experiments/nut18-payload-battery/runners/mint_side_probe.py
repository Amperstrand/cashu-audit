#!/usr/bin/env python3
"""Battery cell: mint-side id-spelling acceptance (error-identity assertions).

Needs a live nutshell arm (FakeWallet sat). Env: MINT (default
http://127.0.0.1:28086). Self-contained: mints its own control
proofs, then asserts the frozen identities from expected.json.
"""
import asyncio
import json
import os
import secrets as ps
import sys

sys.path.insert(0, "/opt/cashu-venv/lib/python3.12/site-packages")

import bolt11
import httpx

from cashu.core.crypto import b_dhke
from cashu.core.crypto.secp import PrivateKey, PublicKey

MINT = os.environ.get("MINT", "http://127.0.0.1:28086")
PRIV = "0101010101010101010101010101010101010101010101010101010101010101"

EXPECT = {
    "inputs_full": (200, None),
    "inputs_short": (400, "keyset"),
    "outputs_short": (400, "keyset id unknown."),
}


def inv_for(amt_sat, nonce):
    tags = bolt11.Tags()
    tags.add(bolt11.TagChar.payment_hash, "00" * 32)
    tags.add(bolt11.TagChar.description, f"battery {nonce}")
    tags.add(bolt11.TagChar.payment_secret, "11" * 32)
    i = bolt11.Bolt11(currency="bc", amount_msat=bolt11.MilliSatoshi(amt_sat * 1000),
                      date=1794000000, tags=tags)
    return bolt11.encode(i, private_key=PRIV)


async def mint6(c, kid, pubs, nonce):
    r = await c.post(f"{MINT}/v1/mint/quote/bolt11",
                     json={"invoice": inv_for(6, nonce), "unit": "sat", "amount": 6})
    r.raise_for_status()
    qid = r.json()["quote"]
    outs, rs = [], []
    for amt in (4, 2):
        s = f"battery-{nonce}-{amt}-" + ps.token_hex(14)
        B, rr = b_dhke.step1_alice(s)
        outs.append({"amount": amt, "B_": B.format().hex(), "id": kid})
        rs.append((amt, s, rr))
    r = await c.post(f"{MINT}/v1/mint/bolt11", json={"quote": qid, "outputs": outs})
    assert r.status_code == 200, r.text[:150]
    inputs = []
    for (amt, s, rr), sig in zip(rs, r.json()["signatures"]):
        A = PublicKey(bytes.fromhex(pubs[amt]))
        C = b_dhke.step3_alice(PublicKey(bytes.fromhex(sig["C_"])), rr, A)
        inputs.append({"amount": amt, "id": kid, "secret": s, "C": C.format().hex()})
    return inputs


async def main():
    ok = True
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{MINT}/v1/keys")
        keysets = r.json()["keysets"]
        kid = next(k["id"] for k in keysets if k["active"])
        short = kid[:16]
        r = await c.get(f"{MINT}/v1/keys/{kid}")
        pubs = {int(a): k for a, k in r.json()["keysets"][0]["keys"].items()}

        inputs = await mint6(c, kid, pubs, "ctl")
        outs = [{"amount": 4, "B_": b_dhke.step1_alice("battery-o4-" + ps.token_hex(14))[0].format().hex(), "id": kid},
                {"amount": 2, "B_": b_dhke.step1_alice("battery-o2-" + ps.token_hex(14))[0].format().hex(), "id": kid}]
        # note: swap requires outputs = inputs - fee; assert only identity class here
        r = await c.post(f"{MINT}/v1/swap", json={"inputs": inputs, "outputs": outs})
        print(f"inputs_full -> {r.status_code} (expect 200 or 11000-balance; NOT keyset error)")
        if "keyset" in r.text and r.status_code == 400:
            ok = False

        inputs = await mint6(c, kid, pubs, "short-in")
        r = await c.post(f"{MINT}/v1/swap", json={
            "inputs": [{**p, "id": short} for p in inputs], "outputs": outs})
        body = r.json()
        exp = (400, f"keyset {short} unknown", 0)
        got = (r.status_code, body.get("detail"), body.get("code"))
        good = got[0] == exp[0] and got[1] == exp[1] and got[2] == exp[2]
        ok &= good
        print(f"inputs_short -> {got} {'OK' if good else 'EXPECTED ' + str(exp)}")

        inputs = await mint6(c, kid, pubs, "short-out")
        r = await c.post(f"{MINT}/v1/swap", json={
            "inputs": inputs,
            "outputs": [{**o, "id": short} for o in outs]})
        body = r.json()
        exp = (400, "keyset id unknown.", 11000)
        got = (r.status_code, body.get("detail"), body.get("code"))
        good = got[0] == exp[0] and got[1] == exp[1] and got[2] == exp[2]
        ok &= good
        print(f"outputs_short -> {got} {'OK' if good else 'EXPECTED ' + str(exp)}")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
