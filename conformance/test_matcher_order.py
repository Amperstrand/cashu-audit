
"""Regression: matcher argument order (2026-11-21 live-found).

The tags_include caller passed (assertion, actual) into
match(value, assertion) — dict matchers never fired, so one-of/integer
tags on a CORRECT advertisement failed ("class 3" of the tollgate
consumer-conformance triage, misdiagnosed as a fork divergence).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_one_of_and_integer_matchers_fire_on_correct_tags():
    from consumer_conformance import evaluate_nostr_body
    event = {
        "kind": 10021, "id": "x", "sig": "y", "content": "",
        "tags": [["metric", "bytes"], ["step_size", "5000"]],
    }
    body = {
        "type": "nostr_event", "kind": 10021, "signed": True,
        "tags_include": [
            ["metric", {"matcher": "one-of", "values": ["bytes", "milliseconds"]}],
            ["step_size", {"matcher": "integer"}],
        ],
    }
    assert evaluate_nostr_body(body, event) == []


def test_one_of_still_rejects_wrong_value():
    from consumer_conformance import evaluate_nostr_body
    event = {
        "kind": 10021, "id": "x", "sig": "y", "content": "",
        "tags": [["metric", "satoshis"]],
    }
    body = {
        "type": "nostr_event", "kind": 10021, "signed": True,
        "tags_include": [
            ["metric", {"matcher": "one-of", "values": ["bytes", "milliseconds"]}],
        ],
    }
    assert evaluate_nostr_body(body, event) != []
