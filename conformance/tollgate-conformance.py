#!/usr/bin/env python3
"""
TollGate Payment Conformance Test Suite

Tests TollGate's payment endpoint (:2121/) against NUT spec requirements.
Generates Cashu tokens with various conditions and verifies accept/reject behavior.

Usage:
    python3 tollgate-conformance.py --gateway 10.99.99.1 --mint http://10.99.99.2:8383
"""

import argparse
import json
import subprocess
import sys
import time
import requests
from dataclasses import dataclass
from typing import Optional

@dataclass
class TestResult:
    name: str
    nut: str
    passed: bool
    expected: str
    actual: str
    severity: str = "MUST"
    
    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status} [{self.nut}] {self.name}\n  Expected: {self.expected}\n  Actual: {self.actual}"

class CashuWallet:
    def __init__(self, mint_url: str, wallet_dir: str = "/tmp/tollgate-conf-wallet"):
        self.mint_url = mint_url
        self.wallet_dir = wallet_dir
        self.home = f"{wallet_dir}/home"
        subprocess.run(["mkdir", "-p", self.home], check=True)
        self.cashu = f"/opt/cashu-venv/bin/cashu"
        
    def _run(self, *args):
        env = {"HOME": self.home, "PATH": "/usr/bin:/bin:/opt/cashu-venv/bin"}
        cmd = [self.cashu, "-h", self.mint_url, "-y", "-t"] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
        return result.stdout.strip(), result.stderr.strip()
    
    def ensure_balance(self, amount: int):
        bal = self.balance()
        if bal < amount:
            self._run("invoice", str(amount - bal + 10))
            time.sleep(1)
    
    def balance(self) -> int:
        out, _ = self._run("balance")
        for line in out.split("\n"):
            if "sat" in line:
                try:
                    return int(line.split(":")[1].strip().split()[0])
                except:
                    pass
        return 0
    
    def send_v3(self, amount: int) -> str:
        self.ensure_balance(amount)
        out, _ = self._run("send", str(amount), "--legacy")
        for line in out.split("\n"):
            if line.startswith("cashuA"):
                return line.strip()
        return ""
    
    def send_v4(self, amount: int) -> str:
        self.ensure_balance(amount)
        out, _ = self._run("send", str(amount))
        for line in out.split("\n"):
            if line.startswith("cashuB"):
                return line.strip()
        return ""
    
    def receive(self, token: str):
        out, _ = self._run("receive", token)
        return out

class TollGateClient:
    def __init__(self, gateway_ip: str):
        self.url = f"http://{gateway_ip}:2121/"
    
    def pay(self, token: str) -> dict:
        resp = requests.post(self.url, data=token, headers={"Content-Type": "text/plain"}, timeout=30)
        try:
            event = resp.json()
            tags = dict(event.get("tags", []))
            return {
                "http_code": resp.status_code,
                "kind": event.get("kind"),
                "level": tags.get("level", ""),
                "code": tags.get("code", ""),
                "content": event.get("content", "")[:200],
            }
        except:
            return {"http_code": resp.status_code, "kind": None, "code": "parse-error", "content": resp.text[:200]}
    
    def health(self) -> bool:
        try:
            resp = requests.get(self.url, timeout=5)
            return resp.status_code == 200
        except:
            return False

def run_conformance_suite(gateway_ip: str, mint_url: str) -> list[TestResult]:
    results = []
    
    tg = TollGateClient(gateway_ip)
    wallet = CashuWallet(mint_url)
    
    # Ensure wallet has balance
    wallet.ensure_balance(100)
    
    # ========== NUT-00: Token Format ==========
    
    # Test 1: V3 token accepted
    print("\n--- NUT-00: V3 token payment ---")
    token = wallet.send_v3(5)
    if token:
        r = tg.pay(token)
        passed = r["code"] not in ["payment-error-invalid-token", "parse-error"]
        results.append(TestResult(
            "V3 token payment", "NUT-00", passed,
            "Payment processed (1022 or error other than invalid-token)",
            f"code={r['code']}, content={r['content'][:100]}"
        ))
    else:
        results.append(TestResult("V3 token payment", "NUT-00", False, "Token generated", "Failed to generate V3 token"))
    
    # Test 2: V4 token (expected to fail per known issue)
    print("--- NUT-00: V4 token payment ---")
    token = wallet.send_v4(5)
    if token:
        r = tg.pay(token)
        passed = r["code"] not in ["payment-error-invalid-token"]
        results.append(TestResult(
            "V4 token payment", "NUT-00", passed,
            "V4 token should be accepted (NUT-00 V4 format)",
            f"code={r['code']} — V4 decode broken in gonuts (see #326)"
        ))
    else:
        results.append(TestResult("V4 token payment", "NUT-00", False, "Token generated", "Failed to generate V4 token"))
    
    # ========== NUT-00: Error Handling ==========
    
    # Test 3: Empty body
    print("--- Error: Empty body ---")
    r = tg.pay("")
    results.append(TestResult(
        "Empty body rejection", "ERR", r["http_code"] == 400,
        "HTTP 400", f"HTTP {r['http_code']}, code={r['code']}"
    ))
    
    # Test 4: Garbage string
    print("--- Error: Garbage token ---")
    r = tg.pay("not-a-cashu-token")
    results.append(TestResult(
        "Garbage token rejection", "ERR", "invalid" in r["code"].lower() or r["http_code"] >= 400,
        "Error response (4xx)", f"HTTP {r['http_code']}, code={r['code']}"
    ))
    
    # Test 5: Oversized body (>1MB)
    print("--- Error: Oversized body ---")
    big = "x" * (1 << 21)  # 2MB
    r = tg.pay(big)
    results.append(TestResult(
        "Oversized body rejection", "ERR", r["http_code"] >= 400,
        "Error response (4xx)", f"HTTP {r['http_code']}, code={r['code']}"
    ))
    
    # ========== NUT-05: Spent Token ==========
    
    # Test 6: Double-spend (same token twice)
    print("--- NUT-05: Double-spend ---")
    token = wallet.send_v3(5)
    if token:
        r1 = tg.pay(token)
        time.sleep(1)
        r2 = tg.pay(token)
        passed = "spent" in r2["code"].lower() or "spent" in r2["content"].lower()
        results.append(TestResult(
            "Double-spend detection", "NUT-05", passed,
            "Second spend rejected with 'spent' error",
            f"1st: code={r1['code']}, 2nd: code={r2['code']}, content={r2['content'][:100]}"
        ))
    else:
        results.append(TestResult("Double-spend detection", "NUT-05", False, "Token generated", "Failed"))
    
    # ========== NUT-10/11: Spending Conditions ==========
    
    # Test 7: P2PK-locked token
    print("--- NUT-11: P2PK-locked token ---")
    token = wallet.send_v3(3)
    if token:
        # Try to lock via cashu send with --lock
        out, err = wallet._run("send", "3", "--legacy", "--lock", "02c0a4b7c8f0e4f3a2b1c5d8e7f6a9b0c3d2e1f4a5b8c7d6e5f4a3b2c1d0e9f8a7")
        locked_token = ""
        for line in out.split("\n"):
            if line.startswith("cashuA"):
                locked_token = line.strip()
                break
        
        if locked_token:
            r = tg.pay(locked_token)
            # Currently TollGate does NOT reject locked tokens — this is the vulnerability
            passed = "locked" in r["code"].lower() or "locked" in r["content"].lower()
            results.append(TestResult(
                "P2PK-locked token rejection", "NUT-11", passed,
                "Locked token rejected (should not credit unspendable tokens)",
                f"code={r['code']} — VULNERABILITY: no spending condition validation (see #324)",
                severity="SHOULD"
            ))
        else:
            results.append(TestResult(
                "P2PK-locked token rejection", "NUT-11", False,
                "Locked token generated", f"Could not generate: {err[:100]}"
            ))
    else:
        results.append(TestResult("P2PK-locked token", "NUT-11", False, "Setup", "Failed"))
    
    # ========== Summary ==========
    
    return results

def main():
    parser = argparse.ArgumentParser(description="TollGate Payment Conformance Test Suite")
    parser.add_argument("--gateway", required=True, help="TollGate gateway IP")
    parser.add_argument("--mint", required=True, help="Cashu mint URL")
    args = parser.parse_args()
    
    print(f"TollGate Conformance Test Suite")
    print(f"Gateway: http://{args.gateway}:2121/")
    print(f"Mint: {args.mint}")
    
    # Health check
    tg = TollGateClient(args.gateway)
    if not tg.health():
        print("❌ Gateway not reachable. Aborting.")
        sys.exit(1)
    print("✅ Gateway reachable")
    
    results = run_conformance_suite(args.gateway, args.mint)
    
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    
    for r in results:
        print(f"\n{r}")
    
    print(f"\n{'=' * 60}")
    print(f"Total: {passed} passed, {failed} failed out of {len(results)}")
    print("=" * 60)
    
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
