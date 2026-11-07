#!/usr/bin/env python3
"""Compare a battery runner's verdict lines against expected.json (exact identities).

Usage: check_expected.py <column> <verdicts-file> <expected.json>
Verdict line format: <fixture>\t<PASS|FAIL|...>\t<detail>
"""
import json
import sys

column, vf, ef = sys.argv[1], sys.argv[2], sys.argv[3]
expected = json.load(open(ef))
block = {
    "cdk": expected["payload_parse_matrix"]["cdk"],
    "ts_decode": expected["payload_parse_matrix"]["cashu_ts_decodePayload"],
}[column]

got = {}
for line in open(vf):
    parts = line.rstrip("\n").split("\t")
    if len(parts) >= 2:
        got[parts[0]] = (parts[1], parts[2] if len(parts) > 2 else "")

bad = 0
for fixture, exp in block.items():
    if fixture not in got:
        print(f"MISSING\t{fixture}")
        bad += 1
        continue
    verdict, detail = got[fixture]
    if exp.startswith("PASS"):
        ok = verdict == "PASS"
    else:
        ok = verdict == "FAIL" and exp.split(" ", 1)[1].rstrip(")") in detail
    if not ok:
        print(f"MISMATCH\t{fixture}\texpected: {exp}\tgot: {verdict} {detail[:90]}")
        bad += 1
    else:
        print(f"OK\t{fixture}\t{exp[:60]}")

sys.exit(1 if bad else 0)
