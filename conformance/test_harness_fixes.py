"""Harness regression tests (2026-11-21): matcher arg order + body notation.

Both bugs were found by the fork-on-hardware A/B loop: the corpus caught
its own instruments misfiring — dict matchers never fired (swapped args)
and the 1mib vector sent a 30-byte literal instead of a megabyte.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def test_matcher_order_on_correct_tags():
    from consumer_conformance import evaluate_nostr_body
    event = {"kind": 10021, "id": "x", "sig": "y", "content": "",
             "tags": [["metric", "bytes"], ["step_size", "5000"]]}
    body = {"type": "nostr_event", "kind": 10021, "signed": True,
            "tags_include": [
                ["metric", {"matcher": "one-of", "values": ["bytes", "milliseconds"]}],
                ["step_size", {"matcher": "integer"}]]}
    assert evaluate_nostr_body(body, event) == []


def test_matcher_order_still_rejects_wrong_value():
    from consumer_conformance import evaluate_nostr_body
    event = {"kind": 10021, "id": "x", "sig": "y", "content": "",
             "tags": [["metric", "satoshis"]]}
    body = {"type": "nostr_event", "kind": 10021, "signed": True,
            "tags_include": [["metric", {"matcher": "one-of", "values": ["bytes"]}]]}
    assert evaluate_nostr_body(body, event) != []


def test_inline_repeated_notation_materializes():
    from consumer_conformance import _materialize_repeated
    assert _materialize_repeated("'x' repeated 1048577 times") == "x" * 1048577
    assert _materialize_repeated("plain body") is None
