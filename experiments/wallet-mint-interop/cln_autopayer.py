#!/usr/bin/env python3
"""CLN Signet Invoice Auto-Payer.

Runs as a background thread during experiments. Polls all CLN-backed mints
for unpaid bolt11 quotes and pays them through the CLN tunnel. This replaces
FakeWallet's instant-auto-pay with real Lightning payment routing while
keeping experiments fully automated.

The payer adds ~5-15s latency per mint operation (vs 0s for FakeWallet),
which is realistic — real Lightning payments take time to route.

Usage:
    payer = CLNAutoPayer(mint_urls)
    payer.start()
    # ... run experiments ...
    payer.stop()
"""
import json
import subprocess
import threading
import time
import urllib.request


def _pay_via_cln(bolt11: str) -> bool:
    r = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "root@inr2.cashu.exchange",
         f"docker exec cln-hub-signet lightning-cli --signet pay {bolt11}"],
        capture_output=True, text=True, timeout=120)
    return r.returncode == 0 and "preimage" in r.stdout


class CLNAutoPayer(threading.Thread):
    """Background thread that monitors mints and pays unpaid invoices via CLN."""

    def __init__(self, mint_urls: list[str], poll_interval: float = 2.0):
        super().__init__(daemon=True, name="cln-auto-payer")
        self.mint_urls = mint_urls
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self.stats = {"paid": 0, "failed": 0, "already_paid": 0}
        self._seen_quotes: set[str] = set()

    def run(self):
        while not self._stop_event.is_set():
            for url in self.mint_urls:
                self._check_mint(url)
            self._stop_event.wait(self.poll_interval)

    def _check_mint(self, url: str):
        try:
            # List active quotes (the mint tracks all unpaid ones)
            # cdk mints expose quote status via /v1/mint/quote/bolt11/{id}
            # We poll /v1/mint/quote/bolt11 without an ID to get all quotes
            # (this is a cdk extension; nutshell mints need a different approach)
            req = urllib.request.Request(
                f"{url}/v1/mint/quote/bolt11",
                data=json.dumps({}).encode(),
                headers={"Content-Type": "application/json"},
                method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
        except Exception:
            return

        quotes = data if isinstance(data, list) else data.get("quotes", [])
        for q in quotes:
            quote_id = q.get("quote", q.get("id", ""))
            if quote_id in self._seen_quotes:
                continue

            state = q.get("state", "").upper()
            bolt11 = q.get("request", "")

            if state == "PAID":
                self._seen_quotes.add(quote_id)
                self.stats["already_paid"] += 1
            elif state == "UNPAID" and bolt11.startswith("ln"):
                self._seen_quotes.add(quote_id)
                if _pay_via_cln(bolt11):
                    self.stats["paid"] += 1
                else:
                    self.stats["failed"] += 1

    def stop(self):
        self._stop_event.set()
        self.join(timeout=5)

    def report(self) -> dict:
        return {**self.stats, "seen": len(self._seen_quotes)}
