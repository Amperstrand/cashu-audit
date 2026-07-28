"""Crypto helpers for constructing Cashu spending-condition proofs.

Uses coincurve (secp256k1) directly. Implements the Cashu blind DHKE
protocol from NUT-00 so we can mint proofs with arbitrary secrets
(P2PK, HTLC) without depending on the cashu wallet package.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

from coincurve import PrivateKey, PublicKey

DOMAIN_SEPARATOR = b"Secp256k1_HashToCurve_Cashu_"
SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


def hash_to_curve(message: bytes) -> PublicKey:
    msg_hash = hashlib.sha256(DOMAIN_SEPARATOR + message).digest()
    counter = 0
    while counter < 2**16:
        h = hashlib.sha256(msg_hash + counter.to_bytes(4, "little")).digest()
        try:
            return PublicKey(b"\x02" + h)
        except Exception:
            counter += 1
    raise ValueError("No valid point found")


def pubkey_neg(pub: PublicKey) -> PublicKey:
    ser = pub.format()
    first = b"\x03" if ser[:1] == b"\x02" else b"\x02"
    return PublicKey(first + ser[1:])


def pubkey_add(a: PublicKey, b: PublicKey) -> PublicKey:
    return a.combine_keys([b])


def pubkey_mul(pub: PublicKey, scalar_hex: str) -> PublicKey:
    return pub.multiply(bytes.fromhex(scalar_hex))


def step1_alice(secret_msg: str) -> tuple[PublicKey, PrivateKey]:
    Y = hash_to_curve(secret_msg.encode("utf-8"))
    r = PrivateKey()
    B_ = pubkey_add(Y, r.public_key)
    return B_, r


def step3_alice(C_blinded: PublicKey, r: PrivateKey, A: PublicKey) -> PublicKey:
    rA = pubkey_mul(A, r.to_hex())
    return pubkey_add(C_blinded, pubkey_neg(rA))


@dataclass
class KeyPair:
    priv: PrivateKey
    pub_hex: str

    @classmethod
    def generate(cls) -> KeyPair:
        priv = PrivateKey()
        pub_hex = priv.public_key.format(compressed=True).hex()
        return cls(priv=priv, pub_hex=pub_hex)

    def sign_schnorr(self, message: bytes) -> str:
        return self.priv.sign_schnorr(message).hex()

    def sign_schnorr_hex(self, message_hex: str) -> str:
        return self.sign_schnorr(bytes.fromhex(message_hex))


def generate_secret() -> str:
    return os.urandom(32).hex()
