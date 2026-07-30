# Multi-Environment Conformance Audit Plan

## Environments to Audit

| URL | Backend | Bark Needed? | Status |
|-----|---------|-------------|--------|
| testnut.cashu.exchange | FakeWallet | No | ✅ Audited 2026-07-30: 113 pass, 0 fail |
| signut.cashu.exchange | Blink staging | Yes (multi-wallet) | 🔄 Partial: 53 pass, 1 fail, 3 skip |
| rugs.cashu.exchange | Blink mainnet | Yes | ⏳ Not audited |
| rugs01.cashu.exchange | Blink mainnet | Yes | ⏳ Not audited |
| nofees.testnut.cashu.exchange | FakeWallet | No | ⏳ Not audited |
| v2.testnut.cashu.exchange | FakeWallet | No | ⏳ Not audited |
| payto.fakewallet.cashu.exchange | FakeWallet | No | ⏳ Not audited |
| notwos.cashu.exchange | WoS | No (read-only) | ⏳ Not audited |

## Audit Strategy

### Phase 1: FakeWallet Environments (no bark, fast)

Run the conformance suite directly — invoices are auto-paid by FakeWallet.

```bash
python3 run_matrix.py \
  --mint https://nofees.testnut.cashu.exchange \
  --mint https://v2.testnut.cashu.exchange \
  --mint https://payto.fakewallet.cashu.exchange
```

**Rate limiting:** Space each mint ~30 seconds apart to avoid overwhelming the
Cloudflare Workers. Run sequentially, not in parallel.

**Expected time:** ~5 minutes per mint (109 scenarios each).

### Phase 2: Signut Completion (bark multi-wallet)

Refresh all 5 bark wallets, then re-run the full 109-scenario audit.

The round-robin across 5 wallets provides ~100 payment capacity, enough for all
payment-dependent scenarios without mid-audit refresh.

### Phase 3: Blink Mainnet (rugs, rugs01)

These use real mainnet Bitcoin. Each audit payment costs real sats (~500 sat × 60
payment scenarios = ~30k sats per audit). Use the bark multi-wallet pattern.

**WARNING:** rugs has DISABLE_P2PK=true and DISABLE_HTLC=true in wrangler.toml.
Many spending-condition tests will skip. This is expected.

### Results Logging

All results should be saved to:
- `cashu-audit/conformance/reports/<env>-<date>.md` — human-readable
- `cashu-audit/conformance/reports/<env>-<date>.json` — machine-readable (if tool supports)

## Rate Limiting Guidelines

| Mint Type | Delay Between Scenarios | Delay Between Mints |
|-----------|------------------------|--------------------|
| FakeWallet | None (instant) | 30 seconds |
| Blink staging (signut) | Built into bark (~3s/payment) | 60 seconds |
| Blink mainnet (rugs) | Built into bark | 120 seconds |

## Known Issues

1. **test 46 `p2pk_sigall_output_amounts_swapped_fail`**: PASSES on testnut (FakeWallet)
   but FAILS on signut (Blink staging). The mint accepts tampered output amounts when
   it should reject them. This is a real spec compliance issue — needs investigation.

2. **Bark VTXO exit depth**: Each wallet handles ~20 OOR payments before needing refresh.
   See `docs/operations/bark-multi-wallet-round-robin.md` for the multi-wallet solution.

3. **Blink webhook delivery delay**: Intermittent 30s-5min delay in Blink staging webhook
   delivery. The audit's 30-retry × 1s loop usually catches it, but occasionally skips.
   Lowered poll interval to 30s as fallback.
