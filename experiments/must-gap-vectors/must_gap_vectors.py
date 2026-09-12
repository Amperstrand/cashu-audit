#!/usr/bin/env python3
"""NUT-11 MUST-gap enforcement probe — raw protocol, self-contained.

Tests the 6 shared coverage gaps from SPECTATE-COVERAGE-REPORT.md against
live mints. We control the secret at blinding time (the mint can't see it),
so we can mint proofs with malformed P2PK secrets and observe enforcement.

Vectors:
  SANITY plain secret, no witness            -> expect ACCEPT (probe precondition)
  CTRL   valid P2PK + proper witness         -> expect ACCEPT
  V2     sigflag "SIG_Voodoo" (11.md:104)    -> spec: MUST reject as unspendable
  V3     SIG_ALL mixed w/ differing input    -> spec: MUST reject (11.md:130)
  V5     nonce = UNCOMPRESSED pubkey         -> spec: MUST reject (11.md:264)
  V6     pubkeys "pkA,pkA", n_sigs=1 (:295)  -> spec: MUST reject as unspundable

FROZEN PREDICTIONS (written 2026-09-12, BEFORE any run — do not edit):
  SANITY: ACCEPT on all 9 mints (else probe bug — SKIP that mint)
  CTRL:   ACCEPT on all 9 (else that mint cannot do basic P2PK: a finding)
  V2:     SPLIT — nutshell>=0.19 likely REJECT (sigflag enum), cdk likely
          ACCEPT-as-anyone-can-spend (NUT-10 caution fallback) = fund-loss
  V5:     ACCEPT on most (compression rarely enforced)
  V6:     ACCEPT on nutshell (distinct-pubkey counting passes with n=1),
          unknown on cdk
  V3:     REJECT on most, but via signature-threshold paths rather than
          the SIG_ALL-consistency MUST itself (discriminate via error body)

Exit 0 always if vectors RAN (verdicts are data, not driver success).
"""
import hashlib
import json
import secrets
import sys
import time
import urllib.error
import urllib.request

from coincurve import PrivateKey, PublicKey

DST = b"Secp256k1_HashToCurve_Cashu_"


def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


# ---------- point ops (mirrors nutshell cashu/core/crypto/secp.py) ----------
def p_add(p1: bytes, p2: bytes) -> bytes:
    return PublicKey(p1).combine([PublicKey(p2)]).format()


def p_neg(p: bytes) -> bytes:
    return ({b"\x02": b"\x03", b"\x03": b"\x02"}[p[:1]]) + p[1:]


def p_sub(p1: bytes, p2: bytes) -> bytes:
    return p_add(p1, p_neg(p2))


def p_mul(point: bytes, scalar: bytes) -> bytes:
    return PublicKey(point).multiply(scalar).format()


def hash_to_curve(msg: str) -> bytes:
    h = sha256(DST + msg.encode())
    for ctr in range(2**16):
        try:
            return PublicKey(b"\x02" + sha256(h + ctr.to_bytes(4, "little"))).format()
        except Exception:
            continue
    raise ValueError("no point found")


def crypto_selftest() -> None:
    a = PrivateKey()
    A = a.public_key.format()
    r = PrivateKey()
    rb = r.secret
    Y = hash_to_curve("selftest")
    B_ = p_add(Y, r.public_key.format())
    C_ = p_mul(B_, a.secret)          # mint signs
    C = p_sub(C_, p_mul(A, rb))       # alice unblinds
    assert C == p_mul(Y, a.secret), "blinding roundtrip failed"
    sk = PrivateKey()
    sig = sk.sign_schnorr(sha256(b"msg"), None)
    from coincurve import PublicKeyXOnly
    xonly = sk.public_key.format()[1:33]
    assert PublicKeyXOnly(xonly).verify(sig, sha256(b"msg")), "schnorr roundtrip failed"


# ---------- HTTP ----------
def http(method: str, url: str, body: dict | None = None, timeout: int = 150):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "curl/8.7.1"})  # CF blocks python UA
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return -1, repr(e)[:300]


# ---------- cashu protocol (raw) ----------
def mint_proofs(base: str, keyset: dict, secrets_by_amount: dict[int, list[str]]) -> tuple[list[dict], str]:
    """Mint proofs with FULLY CONTROLLED secret strings. Returns (proofs, err)."""
    total = sum(a * len(s) for a, s in secrets_by_amount.items())
    st, body = http("POST", f"{base}/v1/mint/quote/bolt11", {"amount": total, "unit": "sat"})
    if st != 200:
        return [], f"quote create {st}: {body[:120]}"
    quote = json.loads(body)["quote"]
    for _ in range(25):
        st, body = http("GET", f"{base}/v1/mint/quote/bolt11/{quote}")
        if st == 200 and json.loads(body).get("state") == "PAID":
            break
        time.sleep(1)
    else:
        return [], f"quote never PAID: {body[:120]}"
    outputs, blind = [], []
    for amt, secs in secrets_by_amount.items():
        for s in secs:
            Y = hash_to_curve(s)
            r = PrivateKey()
            B_ = p_add(Y, r.public_key.format())
            outputs.append({"amount": amt, "B_": B_.hex(), "id": keyset["id"]})
            blind.append((amt, s, r, B_))
    st, body = http("POST", f"{base}/v1/mint/bolt11", {"quote": quote, "outputs": outputs})
    if st != 200:
        return [], f"mint blind {st}: {body[:200]}"
    sigs = {(s["amount"], s["B_"] if "B_" in s else None): s for s in json.loads(body).get("signatures", [])}
    # cdk/nutshell both echo C_ per output index; key by amount+order fallback
    sig_list = json.loads(body).get("signatures", [])
    if len(sig_list) != len(outputs):
        return [], f"signature count mismatch {len(sig_list)} != {len(outputs)}"
    proofs = []
    for (amt, s, r, B_), sig in zip(blind, sig_list):
        C_ = bytes.fromhex(sig["C_"])
        C = p_sub(C_, p_mul(bytes.fromhex(keyset["keys"][str(amt)]), r.secret))
        proofs.append({"amount": amt, "id": keyset["id"], "secret": s, "C": C.hex()})
    return proofs, ""


keyset_id_ref: list[str] = [""]


def fresh_output(amount: int) -> tuple[dict, str]:
    s = secrets.token_hex(16)
    Y = hash_to_curve(s)
    r = PrivateKey()
    B_ = p_add(Y, r.public_key.format())
    return {"amount": amount, "B_": B_.hex(), "id": keyset_id_ref[0]}, s


def _fee_retry(base: str, inputs: list[dict], total: int, retry_fn) -> tuple[int, str]:
    """On a fee-related 400, parse the fee (impl-specific wording) and retry once via retry_fn(fee)."""
    import re as _re
    st, body = retry_fn(None)
    if st == 400:
        fee = None
        m = _re.search(r"required \((\d+)\)", body) or _re.search(r"fees \((\d+)\)", body)
        if m:
            fee = int(m.group(1))
        if fee is not None and "fees" in body and total - fee > 0:
            st, body = retry_fn(fee)
    return st, body


def try_swap(base: str, inputs: list[dict], total: int) -> dict:
    def attempt(fee):
        out, _ = fresh_output(total if fee is None else total - fee)
        return http("POST", f"{base}/v1/swap", {"inputs": inputs, "outputs": [out]})
    st, body = _fee_retry(base, inputs, total, attempt)
    return {"status": st, "body": body[:280]}


def try_swap_sigall(base: str, proofs: list[dict], total: int, sks, build_sigs) -> dict:
    """SIG_ALL swap helper: build witness sigs via build_sigs(proofs, outputs), fee-retry aware."""
    import re as _re
    out, _ = fresh_output(total)
    sigs = build_sigs(proofs, [out])
    for p in proofs:
        p["witness"] = witness(sigs)
    def _post(fee):
        o, _ = fresh_output(total if fee is None else total - fee)
        s = build_sigs(proofs, [o])
        for p in proofs:
            p["witness"] = witness(s)
        return http("POST", f"{base}/v1/swap", {"inputs": proofs, "outputs": [o]}), o
    st, body = _post(None)[0]
    if st == 400:
        m = _re.search(r"required \((\d+)\)", body) or _re.search(r"fees \((\d+)\)", body)
        if m and "fees" in body:
            fee = int(m.group(1))
            if total - fee > 0:
                st, body = _post(fee)[0]
    return {"status": st, "body": body[:280]}


def witness(sigs: list[bytes]) -> str:
    return json.dumps({"signatures": [s.hex() for s in sigs]})


def sign(sk: PrivateKey, msg: str) -> bytes:
    return sk.sign_schnorr(sha256(msg.encode()), None)


def sigall_msg(proofs: list[dict], outputs: list[dict]) -> str:
    m = "".join(p["secret"] + p["C"] for p in proofs)
    m += "".join(str(o["amount"]) + o["B_"] for o in outputs)
    return m


# ---------- vectors ----------
def run_vectors(base: str) -> dict:
    res = {"base": base}
    st, body = http("GET", f"{base}/v1/info")
    if st != 200:
        res["error"] = f"info {st}"
        return res
    res["mint_version"] = json.loads(body).get("version", "?")

    st, body = http("GET", f"{base}/v1/keys")
    if st != 200:
        res["error"] = f"keys {st}"
        return res
    keysets = json.loads(body).get("keysets", [])
    ks = next((k for k in keysets if k.get("unit") == "sat" and "2" in k.get("keys", {})
               and k.get("active", True)), None)
    if not ks:
        res["error"] = "no sat keyset with amount-2 key"
        return res
    res["keyset_id"] = ks["id"][:12]
    keyset_id_ref[0] = ks["id"]

    skA, skB = PrivateKey(), PrivateKey()
    pkA = skA.public_key.format().hex()          # 33-byte compressed
    pkB = skB.public_key.format().hex()
    pkA_unc = skA.public_key.format(compressed=False).hex()  # 65-byte

    # SANITY: plain secret swap
    proofs, err = mint_proofs(base, ks, {2: [secrets.token_hex(16)]})
    if err or not proofs:
        res["SANITY"] = {"status": -1, "body": f"probe bug: {err}", "verdict": "SKIP"}
        return res
    res["SANITY"] = dict(try_swap(base, proofs, 2), expect="ACCEPT")

    # CTRL: valid P2PK (pubkey in `data` per NUT-10; `nonce` is a random string)
    s_ctrl = f'["P2PK",{{"nonce":"{secrets.token_hex(16)}","data":"{pkA}"}}]'
    proofs, err = mint_proofs(base, ks, {2: [s_ctrl]})
    if err or not proofs:
        res["CTRL"] = {"status": -1, "body": f"probe bug: {err}", "verdict": "SKIP"}
    else:
        proofs[0]["witness"] = witness([sign(skA, s_ctrl)])
        res["CTRL"] = dict(try_swap(base, proofs, 2), expect="ACCEPT")

    # V2: invalid sigflag (11.md:104 MUST reject)
    s_v2 = f'["P2PK",{{"nonce":"{secrets.token_hex(16)}","data":"{pkA}","tags":[["sigflag","SIG_Voodoo"]]}}]'
    proofs, err = mint_proofs(base, ks, {2: [s_v2]})
    if err or not proofs:
        res["V2"] = {"status": -1, "body": f"probe bug: {err}", "verdict": "SKIP"}
    else:
        proofs[0]["witness"] = witness([sign(skA, s_v2)])
        res["V2"] = dict(try_swap(base, proofs, 2), expect="REJECT", gap="11.md:104 invalid sigflag")

    # V3: SIG_ALL mixed with differing input (11.md:130 MUST reject)
    s1 = f'["P2PK",{{"nonce":"{secrets.token_hex(16)}","data":"{pkA}","tags":[["sigflag","SIG_ALL"]]}}]'
    s2 = f'["P2PK",{{"nonce":"{secrets.token_hex(16)}","data":"{pkB}","tags":[["sigflag","SIG_INPUTS"]]}}]'
    proofs, err = mint_proofs(base, ks, {2: [s1, s2]})
    if err or len(proofs) != 2:
        res["V3"] = {"status": -1, "body": f"probe bug: {err}", "verdict": "SKIP"}
    else:
        out, _ = fresh_output(4)
        # witness on first input per SIG_ALL; second input gets its own-mode sig
        proofs[0]["witness"] = witness([sign(skA, sigall_msg(proofs, [out]))])
        proofs[1]["witness"] = witness([sign(skB, s2)])
        st_, body_ = http("POST", f"{base}/v1/swap", {"inputs": proofs, "outputs": [out]})
        if st_ == 400 and "not balanced" in body_ and "fees (" in body_:
            import re as _re
            m = _re.search(r"fees \((\d+)\)", body_)
            if m and 4 - int(m.group(1)) > 0:
                out, _ = fresh_output(4 - int(m.group(1)))
                proofs[0]["witness"] = witness([sign(skA, sigall_msg(proofs, [out]))])
                proofs[1]["witness"] = witness([sign(skB, s2)])
                st_, body_ = http("POST", f"{base}/v1/swap", {"inputs": proofs, "outputs": [out]})
        res["V3"] = {"status": st_, "body": body_[:280], "expect": "REJECT",
                     "gap": "11.md:130 SIG_ALL mixed inputs"}

    # V5: uncompressed nonce (11.md:264 MUST reject) — signature IS valid
    s_v5 = f'["P2PK",{{"nonce":"{secrets.token_hex(16)}","data":"{pkA_unc}"}}]'
    proofs, err = mint_proofs(base, ks, {2: [s_v5]})
    if err or not proofs:
        res["V5"] = {"status": -1, "body": f"probe bug: {err}", "verdict": "SKIP"}
    else:
        proofs[0]["witness"] = witness([sign(skA, s_v5)])
        res["V5"] = dict(try_swap(base, proofs, 2), expect="REJECT", gap="11.md:264 uncompressed pubkey")

    # V6: duplicate keys in pathway, n_sigs=1 (11.md:295 MUST reject)
    s_v6 = f'["P2PK",{{"nonce":"{secrets.token_hex(16)}","data":"{pkA}","tags":[["n_sigs","1"],["pubkeys","{pkA}","{pkA}"]]}}]'
    proofs, err = mint_proofs(base, ks, {2: [s_v6]})
    if err or not proofs:
        res["V6"] = {"status": -1, "body": f"probe bug: {err}", "verdict": "SKIP"}
    else:
        proofs[0]["witness"] = witness([sign(skA, s_v6)])
        res["V6"] = dict(try_swap(base, proofs, 2), expect="REJECT",
                         gap="11.md:295 duplicate keys in pathway")

    # V3B control: both inputs SIG_ALL with SAME data+tags (nonce differs) -> expect ACCEPT
    s3b1 = f'["P2PK",{{"nonce":"{secrets.token_hex(16)}","data":"{pkA}","tags":[["sigflag","SIG_ALL"]]}}]'
    s3b2 = f'["P2PK",{{"nonce":"{secrets.token_hex(16)}","data":"{pkA}","tags":[["sigflag","SIG_ALL"]]}}]'
    proofs, err = mint_proofs(base, ks, {2: [s3b1, s3b2]})
    if err or len(proofs) != 2:
        res["V3B"] = {"status": -1, "body": f"probe bug: {err}", "verdict": "SKIP"}
    else:
        out, _ = fresh_output(4)
        proofs[0]["witness"] = witness([sign(skA, sigall_msg(proofs, [out]))])
        st_, body_ = http("POST", f"{base}/v1/swap", {"inputs": proofs, "outputs": [out]})
        if st_ == 400 and "not balanced" in body_ and "fees (" in body_:
            import re as _re
            m = _re.search(r"fees \((\d+)\)", body_)
            if m and 4 - int(m.group(1)) > 0:
                out, _ = fresh_output(4 - int(m.group(1)))
                proofs[0]["witness"] = witness([sign(skA, sigall_msg(proofs, [out]))])
                st_, body_ = http("POST", f"{base}/v1/swap", {"inputs": proofs, "outputs": [out]})
        res["V3B"] = {"status": st_, "body": body_[:280], "expect": "ACCEPT",
                      "gap": "control for V3"}

    # V3C: same as V3B but witness on BOTH inputs -> discriminates per-input witness requirement
    s3c1 = f'["P2PK",{{"nonce":"{secrets.token_hex(16)}","data":"{pkA}","tags":[["sigflag","SIG_ALL"]]}}]'
    s3c2 = f'["P2PK",{{"nonce":"{secrets.token_hex(16)}","data":"{pkA}","tags":[["sigflag","SIG_ALL"]]}}]'
    proofs, err = mint_proofs(base, ks, {2: [s3c1, s3c2]})
    if err or len(proofs) != 2:
        res["V3C"] = {"status": -1, "body": f"probe bug: {err}", "verdict": "SKIP"}
    else:
        out, _ = fresh_output(4)
        msg = sigall_msg(proofs, [out])
        for p in proofs:
            p["witness"] = witness([sign(skA, msg)])
        st_, body_ = http("POST", f"{base}/v1/swap", {"inputs": proofs, "outputs": [out]})
        if st_ == 400 and "not balanced" in body_ and "fees (" in body_:
            import re as _re
            m = _re.search(r"fees \((\d+)\)", body_)
            if m and 4 - int(m.group(1)) > 0:
                out, _ = fresh_output(4 - int(m.group(1)))
                msg = sigall_msg(proofs, [out])
                for p in proofs:
                    p["witness"] = witness([sign(skA, msg)])
                st_, body_ = http("POST", f"{base}/v1/swap", {"inputs": proofs, "outputs": [out]})
        res["V3C"] = {"status": st_, "body": body_[:280], "expect": "DIAGNOSTIC",
                      "gap": "SIG_ALL witness placement"}

    # V3D: SINGLE-input SIG_ALL (degenerate but legal)
    s3d = f'["P2PK",{{"nonce":"{secrets.token_hex(16)}","data":"{pkA}","tags":[["sigflag","SIG_ALL"]]}}]'
    proofs, err = mint_proofs(base, ks, {2: [s3d]})
    if err or not proofs:
        res["V3D"] = {"status": -1, "body": f"probe bug: {err}", "verdict": "SKIP"}
    else:
        res["V3D"] = dict(try_swap_sigall(base, proofs, 2, [(skA,)], lambda pr, o: [
            sign(skA, sigall_msg(pr, o)),
            sign(skA, "".join(p["secret"] for p in pr) + "".join(x["B_"] for x in o)),  # old 0.18.2 format
        ]), expect="ACCEPT", gap="single-input SIG_ALL")

    # ---------- NUT-14 / refund-path family ----------
    skR = PrivateKey()
    pkR = skR.public_key.format().hex()
    preimage = secrets.token_bytes(32).hex()
    hash_lc = sha256(bytes.fromhex(preimage)).hex()      # lowercase digest
    hash_uc = hash_lc.upper()
    t_past, t_future = 1700000000, int(time.time()) + 3600
    def htlc(data: str, tags: list) -> str:
        payload = {"nonce": secrets.token_hex(16), "data": data}
        if tags:
            payload["tags"] = [[k, v] for k, v in tags]
        return json.dumps(["HTLC", payload], separators=(",", ":"))
    wit_pre = lambda: json.dumps({"preimage": preimage})
    wit_sig = lambda sk, m: witness([sign(sk, m)])

    # H1 CTRL: valid preimage -> ACCEPT
    s = htlc(hash_lc, "")
    pr, err = mint_proofs(base, ks, {2: [s]})
    if err or not pr: res["H1"] = {"status": -1, "body": f"probe: {err}", "verdict": "SKIP"}
    else:
        pr[0]["witness"] = wit_pre()
        res["H1"] = dict(try_swap(base, pr, 2), expect="ACCEPT", gap="14.md hash-lock control")

    # H2: UPPERCASE hash + same valid preimage -> digest-compare mints accept, string-compare reject
    s = htlc(hash_uc, "")
    pr, err = mint_proofs(base, ks, {2: [s]})
    if err or not pr: res["H2"] = {"status": -1, "body": f"probe: {err}", "verdict": "SKIP"}
    else:
        pr[0]["witness"] = wit_pre()
        res["H2"] = dict(try_swap(base, pr, 2), expect="MAP", gap="14.md:48 hash case sensitivity")

    # H3: refund path, locktime expired + refund sig -> ACCEPT (d6 isolation)
    s = htlc(hash_lc, [("locktime", str(t_past)), ("refund", pkR)])
    pr, err = mint_proofs(base, ks, {2: [s]})
    if err or not pr: res["H3"] = {"status": -1, "body": f"probe: {err}", "verdict": "SKIP"}
    else:
        pr[0]["witness"] = wit_sig(skR, pr[0]["secret"])
        res["H3"] = dict(try_swap(base, pr, 2), expect="ACCEPT", gap="14.md:69 refund path (d6)")

    # H4: refund path, locktime NOT expired -> REJECT
    s = htlc(hash_lc, [("locktime", str(t_future)), ("refund", pkR)])
    pr, err = mint_proofs(base, ks, {2: [s]})
    if err or not pr: res["H4"] = {"status": -1, "body": f"probe: {err}", "verdict": "SKIP"}
    else:
        pr[0]["witness"] = wit_sig(skR, pr[0]["secret"])
        res["H4"] = dict(try_swap(base, pr, 2), expect="REJECT", gap="14.md locktime unexpired")

    # H5: no witness at all -> REJECT
    s = htlc(hash_lc, "")
    pr, err = mint_proofs(base, ks, {2: [s]})
    if err or not pr: res["H5"] = {"status": -1, "body": f"probe: {err}", "verdict": "SKIP"}
    else:
        res["H5"] = dict(try_swap(base, pr, 2), expect="REJECT", gap="14.md no witness")

    # P1: P2PK refund path, locktime expired -> ACCEPT
    s = f'["P2PK",{{"nonce":"{secrets.token_hex(16)}","data":"{pkA}","tags":[["locktime","{t_past}"],["refund","{pkR}"]]}}]'
    pr, err = mint_proofs(base, ks, {2: [s]})
    if err or not pr: res["P1"] = {"status": -1, "body": f"probe: {err}", "verdict": "SKIP"}
    else:
        pr[0]["witness"] = wit_sig(skR, pr[0]["secret"])
        res["P1"] = dict(try_swap(base, pr, 2), expect="ACCEPT", gap="11.md P2PK refund path")

    # P2: P2PK refund path, locktime future -> REJECT
    s = f'["P2PK",{{"nonce":"{secrets.token_hex(16)}","data":"{pkA}","tags":[["locktime","{t_future}"],["refund","{pkR}"]]}}]'
    pr, err = mint_proofs(base, ks, {2: [s]})
    if err or not pr: res["P2"] = {"status": -1, "body": f"probe: {err}", "verdict": "SKIP"}
    else:
        pr[0]["witness"] = wit_sig(skR, pr[0]["secret"])
        res["P2"] = dict(try_swap(base, pr, 2), expect="REJECT", gap="11.md P2PK refund unexpired")

    # H6: refund sig with EMPTY preimage field (cdk HTLCWitness.preimage is required String)
    s = htlc(hash_lc, [("locktime", str(t_past)), ("refund", pkR)])
    pr, err = mint_proofs(base, ks, {2: [s]})
    if err or not pr: res["H6"] = {"status": -1, "body": f"probe: {err}", "verdict": "SKIP"}
    else:
        pr[0]["witness"] = json.dumps({"preimage": "", "signatures": [sign(skR, pr[0]["secret"]).hex()]})
        res["H6"] = dict(try_swap(base, pr, 2), expect="DIAGNOSTIC", gap="HTLC refund witness shape workaround")

    # verdicts
    for name in ("SANITY", "CTRL", "V2", "V3", "V3B", "V3C", "V3D", "V5", "V6",
                 "H1", "H2", "H3", "H4", "H5", "H6", "P1", "P2"):
        v = res.get(name)
        if not v or v.get("verdict") == "SKIP":
            continue
        accepted = 200 <= v["status"] < 300
        v["verdict"] = ("ACCEPTED" if accepted else "REJECTED")
    return res


def main() -> int:
    crypto_selftest()
    mints = sys.argv[1:]
    out = []
    for m in mints:
        r = run_vectors(m)
        out.append(r)
        print(json.dumps(r), flush=True)
    print("\n==== SUMMARY ====")
    for r in out:
        name = r.get("mint_version", r.get("error", "?"))
        cells = " ".join(
            f"{k}={r[k].get('verdict', '?')[:4]}" for k in ("SANITY", "CTRL", "V2", "V3", "V3B", "V3C", "V3D", "V5", "V6",
             "H1", "H2", "H3", "H4", "H5", "H6", "P1", "P2")
            if k in r)
        print(f"{r['base']} ({name}): {cells}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
