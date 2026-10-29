#!/usr/bin/env /usr/bin/python3
"""Keyset-rotation rung (2026-10-29) — tollgate #818 repro.

cdk-mintd 0.18.2 fakewallet arm + management RPC (KeysetService.
RotateNextKeyset). Mint proof P under keyset A, rotate to B, measure
the wallet-facing surface. Frozen predictions:
PREDICTIONS-keyset-rotation.md. Output: out/keyset-rotation.json.

Legs:
  R1 /v1/keys shows B only (A retired from active)
  R2 /v1/keysets lists BOTH (A inactive/expired)
  R3 /v1/keysets/{A}/keys still 200 (retired keys served)
  R4 swap A-proof -> B outputs: 200 (fund safety)
  W1 swap A-proof -> A-referenced outputs: 4xx 12001-class (#818 identity)
  W2 mint (paid quote) with A-referenced outputs: 4xx 12001-class
  W3 checkstate of A-proof's Y: 200 with state (no keyset error)
"""
import json, sys, secrets, time, subprocess, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "must-gap-vectors"))
sys.path.insert(0, str(HERE.parent.parent / "conformance"))
sys.path.insert(0, str(HERE / "out" / "grpc_stubs"))
import must_gap_vectors as mg
from coincurve import PrivateKey
from version_matrix import CDK_TOML, WORKROOT, sh

MGMT_PORT = 33601
HTTP_PORT = 33602
base = f"http://127.0.0.1:{HTTP_PORT}"
work = WORKROOT / "keyset-rotation"
if work.exists(): shutil.rmtree(work)
work.mkdir(parents=True)
MN = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"

def boot():
    name = f"abm-rot-{secrets.token_hex(3)}"
    (work / "config.toml").write_text(CDK_TOML.format(url_port=HTTP_PORT, cdk_port=HTTP_PORT, listen_host="127.0.0.1")
        + "\n[mint_management_rpc]\nenabled = true\naddress = \"127.0.0.1\"\nport = %d\nallow_insecure = true\n" % MGMT_PORT)
    r = sh(["docker","run","--rm","--network","host","--name",name+"-init",
            "-v",f"{work}:/data","-v",f"{work}:/root/.cdk-mintd",
            "-e",f"AB_CDK_MNEMONIC={MN}",
            "cashubtc/mintd:0.18.2","cdk-mintd","-w","/data",
            "config","init","--new-mint","--file","/data/config.toml"])
    assert r.returncode == 0, (r.stdout + r.stderr)[-300:]
    sh(["docker","run","-d","--network","host","--name",name,
        "-v",f"{work}:/data","-v",f"{work}:/root/.cdk-mintd",
        "-e",f"AB_CDK_MNEMONIC={MN}",
        "-e","CDK_MINTD_MANAGEMENT_ENABLED=true",
        "-e","CDK_MINTD_MANAGEMENT_ADDRESS=127.0.0.1",
        "-e",f"CDK_MINTD_MANAGEMENT_PORT={MGMT_PORT}",
        "-e","CDK_MINTD_MANAGEMENT_ALLOW_INSECURE=true",
        "cashubtc/mintd:0.18.2","cdk-mintd","-w","/data"])
    for _ in range(40):
        try:
            if mg.http("GET", f"{base}/v1/info")[0] == 200: return name
        except Exception: pass
        time.sleep(3)
    raise RuntimeError("arm not ready: " + sh(["docker","logs",name]).stdout[-300:])

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
    if st != 200: return None, f"{st} {b[:110]}"
    return unblind(json.loads(b)["signatures"][0], s, r, amount, ks["id"], ks["keys"]), ""

def sat_active_ks():
    ks = json.loads(mg.http("GET", f"{base}/v1/keys")[1])["keysets"]
    sat = [k for k in ks if k.get("unit") == "sat"]
    assert len(sat) == 1, f"expected 1 active sat keyset, got {[k['id'][:8] for k in sat]}"
    return sat[0]

name = boot()
try:
    ksA = sat_active_ks()
    kidA = ksA["id"]
    q = mint_paid(8)
    P, e = mint_from_quote(q, ksA, 8); assert P, e
    Y_of_P = None  # secret -> Y for checkstate
    from coincurve import PublicKey
    Y_of_P = mg.hash_to_curve(P["secret"]).hex()

    # rotate via management RPC
    import grpc
    from keyset_pb2 import RotateNextKeysetRequest
    from keyset_pb2_grpc import KeysetServiceStub
    ch = grpc.insecure_channel(f"127.0.0.1:{MGMT_PORT}")
    stub = KeysetServiceStub(ch)
    md = (("x-cdk-protocol-version", "1.0.0"),)
    resp = stub.RotateNextKeyset(RotateNextKeysetRequest(unit="sat"), timeout=10, metadata=md)
    kidB = resp.id
    res = {"rotated_to": kidB, "amounts": list(resp.amounts), "unit": resp.unit}

    ksB = sat_active_ks()
    res["R1_keys_only_B"] = (ksB["id"] == kidB and kidB != kidA)
    ksets = json.loads(mg.http("GET", f"{base}/v1/keysets")[1])["keysets"]
    sat_all = [k for k in ksets if k.get("unit") == "sat"]
    res["R2_keysets_lists"] = sorted(k["id"][:8] for k in sat_all)
    res["R2_A_flags"] = next(({"active": k.get("active"), "input_fee_ppk": k.get("input_fee_ppk"), "final_expiry": k.get("final_expiry")} for k in sat_all if k["id"] == kidA), None)
    st, b = mg.http("GET", f"{base}/v1/keysets/{kidA}/keys")
    res["R3_retired_keys_served"] = st == 200

    oB, _, _ = out(8, kidB)
    st, b = mg.http("POST", f"{base}/v1/swap", {"inputs": [P], "outputs": [oB]})
    res["R4_swap_A_proof_to_B"] = f"{st} {b[:100] if st != 200 else 'OK'}"

    oA, _, _ = out(8, kidA)
    p2, e = mint_from_quote(mint_paid(8), ksB, 8); assert p2, e
    st, b = mg.http("POST", f"{base}/v1/swap", {"inputs": [p2], "outputs": [oA]})
    res["W1_swap_to_A_output"] = f"{st} {b[:120]}"

    q2 = mint_paid(4)
    oA2, _, _ = out(4, kidA)
    st, b = mg.http("POST", f"{base}/v1/mint/bolt11", {"quote": q2, "outputs": [oA2]})
    res["W2_mint_A_output"] = f"{st} {b[:120]}"

    st, b = mg.http("POST", f"{base}/v1/checkstate", {"Ys": [Y_of_P]})
    res["W3_checkstate_A_Y"] = f"{st} {b[:120]}"

    print(json.dumps(res, indent=1, default=str))
    (HERE / "out" / "keyset-rotation.json").write_text(json.dumps(res, indent=1, default=str))
finally:
    sh(["docker","rm","-f",name])
