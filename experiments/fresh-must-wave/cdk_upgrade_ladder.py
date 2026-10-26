#!/usr/bin/env /usr/bin/python3
"""Closed-loop cdk upgrade ladder (2026-10-26).

One persistent workdir (sqlite + TOML) + one mnemonic, sequential
cdk-mintd containers 0.17.6 -> 0.17.7 -> 0.18.0 -> 0.18.1 -> 0.18.2.
Frozen predictions: PREDICTIONS-cdk-upgrade-ladder.md.
Output: out/cdk-upgrade-ladder.json

Legs per rung (after the first):
  K  /v1/keys keyset id unchanged (mnemonic-derived continuity)
  R  pre-upgrade unspent proof still swaps
  S  spent-proof enforcement, discriminated:
       fresh-outputs retry rejected  -> spent ledger enforced
       byte-identical 200            -> inputs-keyed replay cache hit
       fresh sigs for spent input    -> true double-spend (never seen)
  Q  paid-unminted quote still mintable after the upgrade
"""
import json, sys, secrets, time, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "must-gap-vectors"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "conformance"))
import must_gap_vectors as mg
from coincurve import PrivateKey
from version_matrix import CDK_TOML, WORKROOT, sh

work = WORKROOT / "cdk-upgrade-ladder"
if work.exists(): shutil.rmtree(work)
work.mkdir(parents=True)
MN = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
PORT = 33507
base = f"http://127.0.0.1:{PORT}"
results, state = [], {}
SUF = secrets.token_hex(3)
INIT_DONE = {"toml": False}

def boot(ver, era):
    name = f"abm-ld{SUF}-{ver.replace('.','')}"
    if era == "legacy":
        cmd = ["docker","run","-d","--network","host","--name",name,
               "-v",f"{work}:/root/.cdk-mintd",
               "-e","CDK_MINTD_LN_BACKEND=FakeWallet",
               "-e","CDK_MINTD_FAKE_WALLET_SUPPORTED_UNITS=sat",
               "-e","CDK_MINTD_LISTEN_HOST=127.0.0.1",
               "-e",f"CDK_MINTD_LISTEN_PORT={PORT}",
               "-e",f"CDK_MINTD_URL=http://127.0.0.1:{PORT}/",
               "-e","CDK_MINTD_MINT_NAME=AB ladder",
               "-e",f"CDK_MINTD_MNEMONIC={MN}",
               f"cashubtc/mintd:{ver}"]
    else:
        if not INIT_DONE["toml"]:
            (work / "config.toml").write_text(
                CDK_TOML.format(url_port=PORT, cdk_port=PORT, listen_host="127.0.0.1"))
            r = sh(["docker","run","--rm","--network","host",
                    "-v",f"{work}:/data","-v",f"{work}:/root/.cdk-mintd",
                    "-e",f"AB_CDK_MNEMONIC={MN}",
                    f"cashubtc/mintd:{ver}","cdk-mintd","-w","/data",
                    "config","init","--existing-mint","--file","/data/config.toml"])
            if r.returncode != 0:
                raise RuntimeError(f"{ver} existing-mint init failed: {(r.stdout+r.stderr)[-300:]}")
            INIT_DONE["toml"] = True
        cmd = ["docker","run","-d","--network","host","--name",name,
               "-v",f"{work}:/root/.cdk-mintd","-v",f"{work}:/data",
               "-e",f"AB_CDK_MNEMONIC={MN}",
               f"cashubtc/mintd:{ver}","cdk-mintd","-w","/data"]
    r = sh(cmd)
    assert r.returncode == 0, f"docker run failed: {r.stderr[:150]}"
    for _ in range(40):
        try:
            if mg.http("GET", f"{base}/v1/info")[0] == 200: return name
        except Exception: pass
        time.sleep(3)
    logs = sh(["docker","logs",name]).stdout
    raise RuntimeError(f"{ver} not ready: {logs[-300:]}")

def sat_ks():
    ks = json.loads(mg.http("GET", f"{base}/v1/keys")[1])["keysets"]
    return [k for k in ks if k.get("unit")=="sat"][0]

def out(amount, kid):
    s = secrets.token_hex(16); Y = mg.hash_to_curve(s); r = PrivateKey()
    return ({"amount": amount, "B_": mg.p_add(Y, r.public_key.format()).hex(), "id": kid}, s, r.secret)

def unblind(sig_entry, secret, r, amount, kid, keys):
    C_ = bytes.fromhex(sig_entry["C_"])
    C = mg.p_sub(C_, mg.p_mul(bytes.fromhex(keys[str(amount)]), r))
    return {"amount": amount, "id": kid, "secret": secret, "C": C.hex()}

def mint_paid(amount):
    st, b = mg.http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": amount, "unit": "sat"})
    assert st == 200, b[:120]
    q = json.loads(b)["quote"]
    for _ in range(30):
        st, b = mg.http("GET", f"{base}/v1/mint/quote/bolt11/{q}")
        if st == 200 and json.loads(b).get("state") == "PAID": return q
        time.sleep(1)
    raise RuntimeError("quote never PAID")

def mint_from_quote(q, ks, amount):
    o, s, r = out(amount, ks["id"])
    st, b = mg.http("POST", f"{base}/v1/mint/bolt11", {"quote": q, "outputs": [o]})
    if st != 200: return None, f"{st} {b[:100]}"
    return unblind(json.loads(b)["signatures"][0], s, r, amount, ks["id"], ks["keys"]), ""

def swap_raw(proofs, ks, amounts):
    outs, meta = [], []
    for a in amounts:
        o, s, r = out(a, ks["id"]); outs.append(o); meta.append((s, r))
    st, b = mg.http("POST", f"{base}/v1/swap", {"inputs": proofs, "outputs": outs})
    return st, b, meta

def rung(ver, era, first=False):
    name = boot(ver, era)
    try:
        ks = sat_ks()
        row = {"ver": ver, "kid_len": len(ks["id"])}
        if first:
            state["ks_id"] = ks["id"]
            q = mint_paid(8); state["P"], e = mint_from_quote(q, ks, 8); assert state["P"], e
            q2 = mint_paid(4); spent, e = mint_from_quote(q2, ks, 4); assert spent, e
            st, b, _ = swap_raw([spent], ks, [4]); assert st == 200, b[:100]
            state["paid_quote"] = mint_paid(16)
            row.update({"K":"baseline","R":"P minted","S":"proof spent","Q":"parked"})
        else:
            row["K"] = "same" if ks["id"] == state["ks_id"] else "CHANGED"
            st, b, meta = swap_raw([state["P"]], ks, [8])
            row["R"] = "redeemable" if st == 200 else f"BROKEN {b[:60]}"
            if st == 200:
                sigs = json.loads(b)["signatures"]
                state["P"] = unblind(sigs[0], meta[0][0], meta[0][1], 8, ks["id"], ks["keys"])
            p2, e = mint_from_quote(state["paid_quote"], ks, 16)
            row["Q"] = "minted" if p2 else f"LOST {e[:60]}"
            # S-leg on a dedicated proof: spend, then retry with fresh outputs
            q3 = mint_paid(4); sp, e = mint_from_quote(q3, ks, 4); assert sp, e
            stA, bA, _ = swap_raw([sp], ks, [4])
            stB, bB, _ = swap_raw([sp], ks, [4])   # same input, fresh outputs
            if stA != 200:
                row["S"] = f"first-swap-failed {stA}"
            elif stB != 200:
                row["S"] = "spent-enforced (fresh-outputs retry rejected)"
            elif bB == bA:
                row["S"] = "cache-hit (byte-identical 200; inputs-keyed replay cache)"
            else:
                row["S"] = "DOUBLE-SPEND (fresh sigs for spent input!)"
            if p2:
                state["paid_quote"] = mint_paid(16)
                q = mint_paid(8); state["P"], e = mint_from_quote(q, ks, 8); assert state["P"], e
        results.append(row); print(json.dumps(row), flush=True)
    finally:
        sh(["docker","rm","-f",name])

rung("0.17.6", "legacy", first=True)
rung("0.17.7", "legacy")
for ver in ("0.18.0","0.18.1","0.18.2"):
    rung(ver, "toml")
outp = Path(__file__).resolve().parent / "out" / "cdk-upgrade-ladder.json"
outp.parent.mkdir(exist_ok=True)
outp.write_text(json.dumps({"mnemonic": "all-abandon test vector (no funds)", "rungs": results}, indent=1))
print("saved", len(results), "rungs")
