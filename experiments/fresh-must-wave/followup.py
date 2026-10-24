#!/usr/bin/env python3
"""Follow-ups resolving the fresh-must-wave prediction mismatches:

F1 — cdk array-limit probe with VALID curve points (first run's
     placeholder Ys hit cdk's public-key validation before any length
     check — probe bug, cdk limit cell was inconclusive).
F2 — NUT-19 as the spec defines it: request-replay caching. Same
     melt-quote POST twice per arm -> same quote id (cached) or new one?
     (P2's ETag/Cache-Control construct measured a different, informal
     HTTP-cache surface — kept as a side observation, not NUT-19.)
Side — record which arms curve-validate Ys at checkstate (cdk rejected
     non-point hex; cf/ns accepted).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "conformance"))

import requests  # noqa: E402
from coincurve import PrivateKey  # noqa: E402
from version_matrix import Arm  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
DOCKER_ARMS = [
    ("ns-0.20.3", "nutshell", "cashubtc/nutshell:0.20.3"),
    ("ns-0.21.0", "nutshell", "cashubtc/nutshell:0.21.0"),
    ("cdk-0.18.1", "cdk", "cashubtc/mintd:0.18.1"),
    ("cdk-0.18.2", "cdk", "cashubtc/mintd:0.18.2"),
]
TESTNUT = "https://testnut.cashu.exchange"


def valid_pubkeys(n: int) -> list[str]:
    return [PrivateKey.from_int(i + 1).public_key.format().hex()
            for i in range(n)]


def melt_quote_twice(base: str, invoice: str) -> dict:
    body = {"request": invoice, "unit": "sat", "amount": 1000}
    ids = []
    for _ in range(2):
        r = requests.post(f"{base}/v1/melt/quote/bolt11", timeout=25,
                          json=body)
        try:
            ids.append((r.status_code, r.json().get("quote")))
        except Exception:
            ids.append((r.status_code, r.text[:120]))
    return {"first": ids[0], "second": ids[1],
            "same_quote_id": ids[0] == ids[1] and ids[0][1] is not None}


def main() -> int:
    # oracle invoice
    oracle = Arm("oracle2", "nutshell")
    oracle.image = "cashubtc/nutshell:0.21.0"
    oracle.host_network = True
    oracle.bring_up()
    try:
        invoice = requests.post(f"{oracle.url}/v1/mint/quote/bolt11",
                                timeout=25,
                                json={"amount": 1000, "unit": "sat"}
                                ).json()["request"]
    finally:
        oracle.tear_down()

    res: dict = {}
    y1001 = valid_pubkeys(1001)

    # testnut: F1-valid-points control (60) + limit (1001) + F2 replay
    r60 = requests.post(f"{TESTNUT}/v1/checkstate", timeout=25,
                        json={"Ys": y1001[:60]})
    r1001 = requests.post(f"{TESTNUT}/v1/checkstate", timeout=40,
                          json={"Ys": y1001})
    res["testnut(cashu-cf)"] = {
        "valid_pts_60": r60.status_code,
        "valid_pts_1001": (r1001.status_code, r1001.text[:150]),
        "replay": melt_quote_twice(TESTNUT, invoice),
    }
    print("done testnut")

    for name, family, image in DOCKER_ARMS:
        arm = Arm(name, family)
        arm.image = image
        arm.host_network = True
        t0 = time.time()
        try:
            arm.bring_up()
            cell: dict = {"replay": melt_quote_twice(arm.url, invoice)}
            if family == "cdk":
                r1001 = requests.post(f"{arm.url}/v1/checkstate", timeout=40,
                                      json={"Ys": y1001})
                cell["valid_pts_1001"] = (r1001.status_code, r1001.text[:200])
            res[name] = cell
            print(f"done {name} ({time.time()-t0:.0f}s) {json.dumps(cell)[:220]}")
        finally:
            arm.tear_down()

    (OUT / "followup.json").write_text(json.dumps(res, indent=1))
    print("\n== summary")
    for k, v in res.items():
        print(f"{k:20s} replay_same_id={v['replay']['same_quote_id']} "
              f"ids={[v['replay']['first'][1], v['replay']['second'][1]]} "
              f"valid_pts_1001={v.get('valid_pts_1001', 'n/a')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
