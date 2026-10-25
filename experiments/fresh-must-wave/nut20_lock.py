#!/usr/bin/env python3
"""NUT-20 quote-lock probes: locked-quote lifecycle per 20.md (current text).

Self-test first: BIP340 verify against 20.md's own worked example
(validates message construction + verifier). Then per arm:
L1 locked quote creation (pubkey echo), L2 mint-no-sig (error identity),
L3 mint-with-valid-sig, L4 wrong-key sig, L5 unlocked quote + spurious
sig, and the retry-after-rejection fund-loss check.

Usage: /usr/bin/python3 experiments/fresh-must-wave/nut20_lock.py
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "must-gap-vectors"))
sys.path.insert(0, str(HERE.parent.parent / "conformance"))

import must_gap_vectors as mg  # noqa: E402
from coincurve import PrivateKey  # noqa: E402
from version_matrix import Arm  # noqa: E402

OUT = HERE / "out"
TESTNUT = "https://testnut.cashu.exchange"
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = PrivateKey.from_int(1).public_key.format()


def tagged(tag: bytes, msg: bytes) -> bytes:
    t = hashlib.sha256(tag).digest()
    return hashlib.sha256(t + t + msg).digest()


def lift_x(b: bytes):
    x = int.from_bytes(b, "big")
    y_sq = (pow(x, 3, P) + 7) % P
    y = pow(y_sq, (P + 1) // 4, P)
    if pow(y_sq, (P + 1) // 4, P) != y:  # not a residue
        return None
    return x, y


def point_from_bytes(b: bytes):
    if len(b) == 33 and b[0] == 0x02:
        r = lift_x(b[1:])
        return (r[0], P - r[1]) if r else None
    if len(b) == 33 and b[0] == 0x03:
        r = lift_x(b[1:])
        return (r[0], r[1]) if r else None
    return None


def point_mul(b: bytes, k: int) -> bytes:
    return mg.p_mul(b, k.to_bytes(32, "big"))


def x_of(b: bytes) -> int:
    return int.from_bytes(b[1:], "big")


def even_y(b: bytes) -> bytes:
    """x-only canonical form: flip to even-y if needed."""
    return b if b[0] == 0x02 else mg.p_neg(b)


def bip340_verify(pubkey33: bytes, msg32: bytes, sig: bytes,
                  x_only: bool = False) -> bool:
    assert len(sig) == 64 and len(msg32) == 32
    Pb = even_y(pubkey33) if x_only else pubkey33
    if point_from_bytes(Pb) is None:
        return False
    px = x_of(Pb)
    r = lift_x(sig[:32])
    if r is None:
        return False
    s = int.from_bytes(sig[32:], "big")
    if s >= N:
        return False
    e = int.from_bytes(tagged(b"BIP0340/challenge",
                              sig[:32] + px.to_bytes(32, "big") + msg32), "big") % N
    Rp = mg.p_add(point_mul(G, s), mg.p_neg(point_mul(Pb, e)))
    if Rp is None or len(Rp) != 33:
        return False
    return x_of(Rp) == int.from_bytes(sig[:32], "big")


def bip340_sign(d: int, msg32: bytes) -> bytes:
    """Reference BIP340 signing (deterministic nonce, aux=0)."""
    pub = point_mul(G, d)
    d_eff = d if pub[0] == 0x02 else N - d
    pub = even_y(pub)
    px = x_of(pub)
    t = d_eff ^ int.from_bytes(tagged(b"BIP0340/aux", b"\x00" * 32), "big")
    rand = tagged(b"BIP0340/nonce", t.to_bytes(32, "big")
                  + px.to_bytes(32, "big") + msg32)
    k0 = int.from_bytes(rand, "big") % N
    R = point_mul(G, k0)
    k = k0 if R[0] == 0x02 else N - k0
    R = even_y(R)
    e = int.from_bytes(tagged(b"BIP0340/challenge",
                              R[1:] + px.to_bytes(32, "big") + msg32), "big") % N
    return R[1:] + ((k + e * d_eff) % N).to_bytes(32, "big")


def len32(b: bytes) -> bytes:
    return len(b).to_bytes(4, "big")


def amount_be(a: int) -> bytes:
    if a == 0:
        return b""
    return a.to_bytes((a.bit_length() + 7) // 8, "big")


def mint_quote_sig_msg(quote: str, outputs: list[dict]) -> bytes:
    m = b"Cashu_MintQuoteSig_v1"
    qb = quote.encode()
    m += len32(qb) + qb
    for o in outputs:
        ab = amount_be(o["amount"])
        b = bytes.fromhex(o["B_"])
        m += len32(ab) + ab + len32(b) + b
    return m


def selftest():
    """Validate against cdk v0.18.2's test vector (real crypto), then
    record what the 20.md prose example does (suspected decorative)."""
    quote = "0192d3c0-7e8a-7c3d-8e9f-1a2b3c4d5e6f"
    outputs = [
        {"amount": 1, "id": "009a1f293253e41e",
         "B_": "036d6caac248af96f6afa7f904f550253a0f3ef3f5aa2fe6838a95b216691468e2"},
        {"amount": 1, "id": "009a1f293253e41e",
         "B_": "021f8a566c205633d029094747d2e18f44e05993dda7a5f88f496078205f656e59"},
    ]
    sig = bytes.fromhex(
        "4881093a332ff7c79f3e598ce5b249d64978b47165a0b19c18adf0ced0246228"
        "e61e702f0abaf1bf27b92be4336bdbabacfbe4c914076386b3c66fdcd0b3480e")
    pubkey = bytes.fromhex(
        "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798")  # = G, d=1
    msg = mint_quote_sig_msg(quote, outputs)
    expected_msg = bytes.fromhex(
        "43617368755f4d696e7451756f74655369675f76310000002430313932643363302d3765386"
        "12d376333642d386539662d316132623363346435653666000000010100000021036d6caac"
        "248af96f6afa7f904f550253a0f3ef3f5aa2fe6838a95b216691468e200000001010000002"
        "1021f8a566c205633d029094747d2e18f44e05993dda7a5f88f496078205f656e59")
    msg_ok = msg == expected_msg
    m32 = hashlib.sha256(msg).digest()
    hash_ok = m32.hex() == ("c164fd384879f74ab6ea2e7cf13d90ed"
                            "42e6df9d5de607eeb5c9cc7d36fb1c21")
    vec_ok = bip340_verify(pubkey, m32, sig, x_only=True)

    # 20.md prose example — does it verify under any construction?
    spec_results = {}
    sq = "9d745270-1405-46de-b5c5-e2762b4f5e00"
    souts = [
        {"amount": 8, "id": "009a1f293253e41e",
         "B_": "035015e6d7ade60ba8426cefaf1832bbd27257636e44a76b922d78e79b47cb689d"},
        {"amount": 2, "id": "009a1f293253e41e",
         "B_": "0288d7649652d0a83fc9c966c969fb217f15904431e61a44b14999fabc1b5d9ac6"},
    ]
    ssig = bytes.fromhex(
        "d9be080b33179387e504bb6991ea41ae0dd715e28b01ce9f63d57198a095bccc"
        "776874914288e6989e97ac9d255ac667c205fa8d90a211184b417b4ffdd24092")
    spub = bytes.fromhex(
        "03d56ce4e446a85bbdaa547b4ec2b073d40ff802831352b8272b7dd7a4de5a7cac")
    new_m = hashlib.sha256(mint_quote_sig_msg(sq, souts)).digest()
    legacy = sq.encode() + b"".join(bytes.fromhex(o["B_"]) for o in souts)
    legacy_m = hashlib.sha256(legacy).digest()
    spec_results["new_format"] = bip340_verify(spub, new_m, ssig, x_only=True)
    spec_results["legacy_hashed"] = bip340_verify(spub, legacy_m, ssig, x_only=True)
    spec_results["legacy_raw"] = bip340_verify(spub, legacy[:32], ssig, x_only=True)

    # round-trip our own signer (odd-y pubkeys included)
    ok2 = True
    for d in (1, 2, 3, 4, 5):
        m2 = hashlib.sha256(b"selftest-%d" % d).digest()
        s2 = bip340_sign(d, m2)
        pub2 = point_mul(G, d)
        if not bip340_verify(pub2, m2, s2, x_only=True):
            ok2 = False
    return {"msg_bytes": msg_ok, "sha256": hash_ok, "cdk_vector_sig": vec_ok,
            "signer_roundtrip_xonly": ok2, "spec20_example": spec_results}


def outputs_for(total, kid):
    outs, rem = [], total
    for amt in (64, 32, 16, 8, 4, 2, 1):
        while rem >= amt:
            s = secrets.token_hex(16)
            Y = mg.hash_to_curve(s)
            r = PrivateKey()
            outs.append({"amount": amt, "B_": mg.p_add(Y, r.public_key.format()).hex(), "id": kid})
            rem -= amt
    return outs


def sat_keyset(base):
    ks = json.loads(mg.http("GET", f"{base}/v1/keys")[1])["keysets"]
    return [k for k in ks if k.get("unit") == "sat"][0]


def paid_locked_quote(base, amount, pubkey_hex):
    st, body = mg.http("POST", f"{base}/v1/mint/quote/bolt11",
                       {"amount": amount, "unit": "sat", "pubkey": pubkey_hex})
    if st != 200:
        return None, f"L1 quote {st}: {body[:140]}"
    j = json.loads(body)
    for _ in range(40):
        st, body = mg.http("GET", f"{base}/v1/mint/quote/bolt11/{j['quote']}")
        if st == 200 and json.loads(body).get("state") == "PAID":
            return j, ""
        time.sleep(1)
    return None, f"never paid: {body[:100]}"


def mint(base, quote, outputs, signature_hex=None):
    payload = {"quote": quote, "outputs": outputs}
    if signature_hex is not None:
        payload["signature"] = signature_hex
    st, body = mg.http("POST", f"{base}/v1/mint/bolt11", payload)
    sigs = len(json.loads(body).get("signatures", [])) if st == 200 else 0
    return {"status": st, "sigs": sigs, "body": body[:200]}


def run_arm(base):
    ks = sat_keyset(base)
    d = secrets.randbelow(N - 1) + 1
    pub = mg.p_mul(G, d.to_bytes(32, "big")).hex()
    res = {"pubkey": pub[:16] + "…"}

    q, err = paid_locked_quote(base, 64, pub)
    if not q:
        return {"L1": {"error": err}}
    res["L1_echo_pubkey"] = (q.get("pubkey") == pub, str(q.get("pubkey"))[:20])

    outs = outputs_for(64, ks["id"])
    res["L2_no_sig"] = mint(base, q["quote"], outs)
    # L3 retry same quote WITH valid signature (also the fund-loss check:
    # did L2's rejection burn the paid quote?)
    msg = hashlib.sha256(mint_quote_sig_msg(q["quote"], outs)).digest()
    sig = bip340_sign(d, msg).hex()
    res["L3_valid_sig_after_reject"] = mint(base, q["quote"], outs, sig)

    # L4 wrong key
    d2 = secrets.randbelow(N - 1) + 1
    q2, err = paid_locked_quote(base, 32, pub)
    if q2:
        outs2 = outputs_for(32, ks["id"])
        bad_sig = bip340_sign(d2, hashlib.sha256(
            mint_quote_sig_msg(q2["quote"], outs2)).digest()).hex()
        res["L4_wrong_key"] = mint(base, q2["quote"], outs2, bad_sig)
        # retry L4's quote with the RIGHT key (quote survival check)
        good = bip340_sign(d, hashlib.sha256(
            mint_quote_sig_msg(q2["quote"], outs2)).digest()).hex()
        res["L4_retry_valid"] = mint(base, q2["quote"], outs2, good)

    # L5 unlocked quote + spurious signature
    st, body = mg.http("POST", f"{base}/v1/mint/quote/bolt11",
                       {"amount": 16, "unit": "sat"})
    if st == 200:
        qu = json.loads(body)["quote"]
        for _ in range(40):
            st, body = mg.http("GET", f"{base}/v1/mint/quote/bolt11/{qu}")
            if st == 200 and json.loads(body).get("state") == "PAID":
                break
            time.sleep(1)
        outs3 = outputs_for(16, ks["id"])
        spur = bip340_sign(d, hashlib.sha256(
            mint_quote_sig_msg(qu, outs3)).digest()).hex()
        res["L5_unlocked_plus_sig"] = mint(base, qu, outs3, spur)
    return res


def main() -> int:
    OUT.mkdir(exist_ok=True)
    st = selftest()
    print(f"selftest: {json.dumps(st)}")
    if not (st["msg_bytes"] and st["sha256"] and st["cdk_vector_sig"]
            and st["signer_roundtrip_xonly"]):
        print("SELFTEST FAILED — not probing (probe-bug discipline)")
        return 1

    results = {}
    results["testnut(cashu-cf)"] = run_arm(TESTNUT)
    print("testnut:", json.dumps(results["testnut(cashu-cf)"])[:300])
    for name, family, image in (("ns-0.21.0", "nutshell", "cashubtc/nutshell:0.21.0"),
                                ("cdk-0.18.2", "cdk", "cashubtc/mintd:0.18.2")):
        arm = Arm(name.replace(".", "-"), family)
        arm.image = image
        arm.host_network = True
        t0 = time.time()
        try:
            arm.bring_up()
            results[name] = run_arm(arm.url)
            print(f"{name} ({time.time()-t0:.0f}s):", json.dumps(results[name])[:300])
        finally:
            arm.tear_down()
    (OUT / "nut20.json").write_text(json.dumps(results, indent=1))

    print("\n== summary")
    for arm, v in results.items():
        print(f"\n{arm}: L1_echo={v.get('L1_echo_pubkey')}")
        for leg in ("L2_no_sig", "L3_valid_sig_after_reject", "L4_wrong_key",
                    "L4_retry_valid", "L5_unlocked_plus_sig"):
            r = v.get(leg)
            if r:
                print(f"  {leg}: {r.get('status')} sigs={r.get('sigs')} {str(r.get('body'))[:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
