"""cashu-audit Layer 4: Runtime Conformance Testing.

Tests Cashu mints and wallets against the NUT specification by constructing
real spending-condition proofs and verifying the mint's accept/reject behavior.

Layers:
    Layer 1: Spec quote coverage (static)       — existing
    Layer 2: Divergence database (manual)        — existing
    Layer 3: AI code audit prompts (manual)      — existing
    Layer 4: Runtime conformance (automated)     — THIS PACKAGE
"""
