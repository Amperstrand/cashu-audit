

def test_inline_repeated_notation_materializes():
    from consumer_conformance import _materialize_repeated
    assert _materialize_repeated("'x' repeated 1048577 times") == "x" * 1048577
    assert _materialize_repeated("'ab' repeated 3 times") is None  # multi-char: not the notation
    assert _materialize_repeated("plain token body") is None
