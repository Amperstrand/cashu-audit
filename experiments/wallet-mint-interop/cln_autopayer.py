#!/usr/bin/env python3
"""CLN Signet Invoice Auto-Payer (v2).

v1 polled `GET /v1/mint/quote/bolt11` (no ID) — cdk returns 405 (POST-only;
there is NO quote-list endpoint — that was issue #195's root cause).

v2 polls the cdk mints' sqlite databases DIRECTLY (read-only, WAL-safe)
for unpaid quotes and pays them through the CLN signet tunnel. Requires
the payer to run on the mint host (ai-legion) with the battery workdirs
at ~/mint-battery/<name>/cdk-mintd.sqlite.

Usage:
    payer = CLNAutoPayer(mint_urls, db_paths={url: sqlite_path})
    payer.start(); ... payer.stop(); payer.report()
"""
import json
import sqlite3
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
    """Background thread: watches cdk sqlite DBs, pays unpaid invoices via CLN."""

    def __init__(self, mint_urls: list[str], db_paths: dict[str, str] | None = None,
                 poll_interval: float = 2.0):
        super().__init__(daemon=True, name="cln-auto-payer")
        self.mint_urls = mint_urls
        self.db_paths = db_paths or {}
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self.stats = {"paid": 0, "failed": 0, "already_paid": 0, "errors": 0}
        self._seen_quotes: set[str] = set()

    def run(self):
        while not self._stop_event.is_set():
            for url in self.mint_urls:
                try:
                    self._check_mint(url)
                except Exception:
                    self.stats["errors"] += 1
            self._stop_event.wait(self.poll_interval)

    def _check_mint(self, url: str):
        db_path = self.db_paths.get(url)
        if not db_path:
            return  # no sqlite path mapped — nothing to poll (FakeWallet mints don't need us)
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2)
        try:
            rows = conn.execute(
                "SELECT id, request FROM mint_quote WHERE amount_paid = 0 "
                "AND request LIKE 'ln%'").fetchall()
        finally:
            conn.close()
        for quote_id, bolt11 in rows:
            if quote_id in self._seen_quotes:
                continue
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
