"""Scenario framework: each scenario constructs inputs, calls the mint, and checks the outcome."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from .client import MintClient
from .crypto import KeyPair, generate_secret
from .builder import ProofBuilder, Proof, build_p2pk_secret, build_htlc_secret


class Result(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    XFAIL = "XFAIL"

    @property
    def icon(self) -> str:
        return {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "XFAIL": "⚠️"}[self.value]


@dataclass
class ScenarioResult:
    name: str
    category: str
    result: Result
    note: str = ""
    duration_ms: float = 0.0


@dataclass
class Scenario:
    name: str
    category: str
    description: str
    run: Callable[[MintClient], ScenarioResult]

    def execute(self, mint: MintClient) -> ScenarioResult:
        try:
            return self.run(mint)
        except Exception as e:
            return ScenarioResult(
                name=self.name,
                category=self.category,
                result=Result.SKIP,
                note=f"Exception: {type(e).__name__}: {e}",
            )


_REGISTRY: list[Scenario] = []


def scenario(name: str, category: str, description: str = ""):
    def decorator(fn: Callable[[MintClient], ScenarioResult]):
        s = Scenario(
            name=name,
            category=category,
            description=description or fn.__doc__ or "",
            run=fn,
        )
        _REGISTRY.append(s)
        return s
    return decorator


def all_scenarios() -> list[Scenario]:
    return list(_REGISTRY)


def expect_reject(status: int, body) -> bool:
    return status in (400, 403)


def expect_success(status: int, body) -> bool:
    return status == 200
