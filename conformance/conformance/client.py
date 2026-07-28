"""Mint HTTP API client — thin wrapper over Cashu NUT REST endpoints."""
from __future__ import annotations

import requests
from typing import Any


class MintClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _post(self, path: str, body: dict) -> tuple[int, dict | str]:
        url = f"{self.base_url}{path}"
        resp = self.session.post(url, json=body, timeout=self.timeout)
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, resp.text

    def _get(self, path: str) -> tuple[int, dict | str]:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, timeout=self.timeout)
        try:
            return resp.status_code, resp.json()
        except Exception:
            return resp.status_code, resp.text

    def get_keysets(self) -> dict:
        _, data = self._get("/v1/keysets")
        return data

    def get_keys(self, keyset_id: str | None = None) -> dict:
        path = "/v1/keys"
        if keyset_id:
            path += f"/{keyset_id}"
        _, data = self._get(path)
        return data

    def mint_quote(self, amount: int, unit: str = "sat") -> dict:
        code, data = self._post("/v1/mint/quote/bolt11", {"amount": amount, "unit": unit})
        if code != 200:
            raise RuntimeError(f"mint_quote failed ({code}): {data}")
        return data

    def mint_tokens(self, quote: str, outputs: list[dict]) -> dict:
        code, data = self._post("/v1/mint/bolt11", {"quote": quote, "outputs": outputs})
        if code != 200:
            raise RuntimeError(f"mint failed ({code}): {data}")
        return data

    def swap(self, inputs: list[dict], outputs: list[dict]) -> dict:
        code, data = self._post("/v1/swap", {"inputs": inputs, "outputs": outputs})
        if code != 200:
            raise RuntimeError(f"swap failed ({code}): {data}")
        return data

    def try_swap(self, inputs: list[dict], outputs: list[dict]) -> tuple[int, dict | str]:
        return self._post("/v1/swap", {"inputs": inputs, "outputs": outputs})

    def melt_quote(self, invoice: str, unit: str = "sat") -> dict:
        code, data = self._post("/v1/melt/quote/bolt11", {"request": invoice, "unit": unit})
        if code != 200:
            raise RuntimeError(f"melt_quote failed ({code}): {data}")
        return data

    def melt(self, quote: str, inputs: list[dict], outputs: list[dict] | None = None) -> tuple[int, dict | str]:
        body: dict[str, Any] = {"quote": quote, "inputs": inputs}
        if outputs:
            body["outputs"] = outputs
        return self._post("/v1/melt/bolt11", body)

    def checkstate(self, ys: list[str]) -> dict:
        code, data = self._post("/v1/checkstate", {"Ys": ys})
        if code != 200:
            raise RuntimeError(f"checkstate failed ({code}): {data}")
        return data

    def get_mint_info(self) -> dict:
        _, data = self._get("/v1/info")
        return data

    # ─── NUT-04 quote status ──────────────────────────────────────────────

    def check_mint_quote(self, quote_id: str) -> dict:
        """GET /v1/mint/quote/bolt11/{quote_id} — check mint quote status."""
        code, data = self._get(f"/v1/mint/quote/bolt11/{quote_id}")
        if code != 200:
            raise RuntimeError(f"check_mint_quote failed ({code}): {data}")
        return data

    # ─── NUT-20 locked quotes ─────────────────────────────────────────────

    def mint_quote_with_pubkey(
        self, amount: int, pubkey: str, unit: str = "sat"
    ) -> dict:
        """Create a mint quote with a NUT-20 locking pubkey."""
        code, data = self._post(
            "/v1/mint/quote/bolt11",
            {"amount": amount, "unit": unit, "pubkey": pubkey},
        )
        if code != 200:
            raise RuntimeError(f"mint_quote_with_pubkey failed ({code}): {data}")
        return data

    def try_mint(
        self,
        quote: str,
        outputs: list[dict],
        signature: str | None = None,
    ) -> tuple[int, dict | str]:
        """POST /v1/mint/bolt11 returning (status, body) without raising."""
        body: dict[str, Any] = {"quote": quote, "outputs": outputs}
        if signature is not None:
            body["signature"] = signature
        return self._post("/v1/mint/bolt11", body)

    # ─── NUT-29 batch operations ──────────────────────────────────────────

    def batch_check_quotes(
        self, quote_ids: list[str]
    ) -> tuple[int, dict | str]:
        """POST /v1/mint/quote/bolt11/check — batch check quote states."""
        return self._post(
            "/v1/mint/quote/bolt11/check", {"quotes": quote_ids}
        )

    def try_batch_mint(
        self, quotes: list[str], outputs: list[dict]
    ) -> tuple[int, dict | str]:
        """POST /v1/mint/bolt11/batch — batch mint, returns (status, body)."""
        return self._post(
            "/v1/mint/bolt11/batch",
            {"quotes": quotes, "outputs": outputs},
        )
