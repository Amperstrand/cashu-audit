#!/usr/bin/env python3
"""Batch-quote-count limit sizing: how many quote IDs does each mint
accept in a /v1/mint/bolt11/batch request? Sizes cashu-cf's
batchQuotesCap=50 against the reference mints. Unknown UUIDs suffice if
the length check fires before existence (observed check-order datum).

Frozen predictions (2026-10-25, before run):
  testnut (cf): 50 OK-length (then unknown-quote error), 51 -> length
    error (batchQuotesCap=50, source-read info.ts:165)
  ns-0.21.0:    limit 1000 (pydantic class, like checkstate)
  cdk-0.18.2:   limit unknown; advertised max_array_length 1000
Check-order datum: which error fires at 51-ids on each arm.
"""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "must-gap-vectors"))
sys.path.insert(0, str(HERE.parent.parent / "conformance"))

import must_gap_vectors as mg  # noqa: E402
from version_matrix import Arm  # noqa: E402

OUT = HERE / "out"
TESTNUT = "https://testnut.cashu.exchange"


def batch_n(base, n):
    ids = [str(uuid.uuid4()) for _ in range(n)]
    st, body = mg.http("POST", f"{base}/v1/mint/bolt11/batch",
                       {"quotes": ids, "outputs": []})
    return {"n": n, "status": st, "body": body[:130]}


def run_arm(base):
    res = {}
    for n in (50, 51, 100, 1001):
        res[f"n{n}"] = batch_n(base, n)
    return res


def main() -> int:
    results = {"testnut(cashu-cf)": run_arm(TESTNUT)}
    print("testnut:", json.dumps(results["testnut(cashu-cf)"])[:300])
    for name, family, image in (("ns-0.21.0", "nutshell", "cashubtc/nutshell:0.21.0"),
                                ("cdk-0.18.2", "cdk", "cashubtc/mintd:0.18.2")):
        arm = Arm(name.replace(".", "-"), family)
        arm.image = image
        arm.host_network = True
        try:
            arm.bring_up()
            results[name] = run_arm(arm.url)
            print(f"{name}:", json.dumps(results[name])[:300])
        finally:
            arm.tear_down()
    (OUT / "nut29_caps.json").write_text(json.dumps(results, indent=1))
    print("\n== summary")
    for arm, v in results.items():
        print(f"\n{arm}:")
        for k, r in v.items():
            print(f"  {k}: {r['status']} {r['body'][:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
