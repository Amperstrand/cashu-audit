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
