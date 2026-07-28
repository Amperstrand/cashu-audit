# Layer 3 AI Audit: tollgate-captive-portal-site — Cashu Interactions — 2026-07-28 — GLM-5.2

## Metadata
- **Date**: 2026-07-28
- **Model**: GLM-5.2 in opencode
- **Target**: OpenTollGate/tollgate-captive-portal-site @ main
- **Cashu library**: @cashu/cashu-ts v2.2.2
- **Auditor**: opencode (Sisyphus agent)
- **Scope**: Token format handling, payment flow, error codes, mint interaction

---

## 1. Executive Summary

| Area | Verdict | Finding |
|---|---|---|
| Token format support | **WARN** | cashu-ts v2.2.2 supports V4 (cashuB), but backend (gonuts) can't decode V4 |
| Payment submission | PASS | Correctly wraps token in Nostr event (kind 21000) per TIP-01 |
| Token validation | PASS | Uses cashu-ts getDecodedToken — handles V1/V3/V4 |
| Error code handling | PASS | Handles CU10x, LN0xx error codes with i18n |
| Mint URL handling | PASS | Extracted from backend advertisement, not hardcoded |
| Content-Type | PASS | Sends application/json (backend accepts this) |

**Overall verdict: WARN** — Portal is V4-ready but backend is V3-only. Users with modern Cashu wallets will have tokens accepted by the portal but rejected by the backend.

---

## 2. Cashu Touchpoint Map

### 2.1 Token Input (src/helpers/cashu.js)
- **Import**: `import { getDecodedToken } from "@cashu/cashu-ts"` — line 2
- **Validation**: `validateToken(token, mint, i18n)` — line ~50
  - Uses `getDecodedToken(token.trim())` to decode — handles V3 AND V4
  - Extracts proofs from decoded token (handles multiple token structures)
  - Validates amount >= mint price

### 2.2 Payment Submission (src/helpers/cashu.js:132)
- **submitToken(token, tollgateDetails, allocation, i18n)**
- Creates Nostr event (kind 21000) with:
  - Tags: `["p", tollgatePubkey]`, `["device-identifier", type, value]`, `["payment", token]`
  - Signs with randomly generated Nostr private key
- POSTs to `http://<hostname>:2121/` with `Content-Type: application/json`
- Body: `JSON.stringify(event)` — the full Nostr event

### 2.3 Advertisement Fetching (src/helpers/tollgate.js)
- `fetchTollgateData()` — GET `http://<hostname>:2121/`
- Parses Nostr event (kind 10021) for pricing/mint info
- Extracts: metric, step_size, price_per_step, mint URLs

### 2.4 Error Handling (src/helpers/cashu.js + src/App.jsx)
- CU001: No access options
- CU002: Insufficient funds
- CU104: Token validation error
- CU105/CU106/CU107/CU108: Payment processing failures
- LN001/LN002/LN003/LN004: Lightning errors (restored in #288)

---

## 3. V4 Token Incompatibility Chain

```
User's Cashu wallet (cashu-ts v2.2.2 or Nutshell ≥0.20.0)
  → produces V4 token (cashuB prefix, CBOR format)
  → pastes into captive portal
  → portal validates with getDecodedToken() ← V4 DECODES SUCCESSFULLY
  → portal wraps in Nostr event (kind 21000)
  → POSTs to backend :2121/
  → backend extractCashuToken() extracts raw token from "payment" tag
  → backend calls cashu.DecodeToken(tokenString) [gonuts]
  → gonuts tries DecodeTokenV4 → FAILS (CBOR struct tags issue)
  → gonuts falls back to DecodeTokenV3 → FAILS (not V3 format)
  → user sees: "invalid token: invalid V3 token"
```

**Root cause**: gonuts's TokenV4 struct uses `json` struct tags with `cbor.Unmarshal`. The CBOR encoding from cashu-ts v2.2.2 doesn't match.

**Test evidence**: Commented-out test tokens in Cashu.jsx use `cashuB` prefix — confirming the developer tested with V4 tokens but may not have noticed the backend rejection.

---

## 4. Token Format Flow Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  User's Wallet   │     │  Captive Portal   │     │  TollGate Backend│
│  (cashu-ts/Nutshell)  │  (cashu-ts v2.2.2)│     │  (gonuts v0.10.0)│
├─────────────────┤     ├──────────────────┤     ├─────────────────┤
│                  │     │                   │     │                  │
│ V4: cashuB...   ─┼─────┼─→ getDecodedToken │     │                  │
│ (CBOR+base64)    │     │  ✓ V4 decodes OK  │     │                  │
│                  │     │                   │     │                  │
│                  │     │  Wrap in Nostr    │     │                  │
│                  │     │  event k=21000   ─┼─────┼─→ extractCashuToken│
│                  │     │                   │     │  → DecodeToken()  │
│                  │     │                   │     │  → V4 FAILS ❌    │
│                  │     │                   │     │  → V3 fallback   │
│                  │     │                   │     │  → V3 FAILS ❌   │
│                  │     │                   │     │  → "invalid V3"  │
│                  │     │                   │     │                  │
│ V3: cashuA...   ─┼─────┼─→ getDecodedToken │     │                  │
│ (JSON+base64)    │     │  ✓ V3 decodes OK  │     │                  │
│                  │     │  Wrap in Nostr   ─┼─────┼─→ extractCashuToken│
│                  │     │                   │     │  → DecodeToken()  │
│                  │     │                   │     │  → V4 try FAILS   │
│                  │     │                   │     │  → V3 fallback ✓  │
│                  │     │                   │     │  → Payment OK ✅  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## 5. Recommendations

1. **Short-term**: Portal should warn users if their token is V4 and the backend doesn't support it. Add a client-side check: after `getDecodedToken`, check if token starts with `cashuB` and display "V4 tokens not yet supported" message.

2. **Medium-term**: Fix gonuts V4 CBOR decoding (issue #326). This unblocks V4 support across the entire stack.

3. **Long-term**: Migrate to CDK-go (#305) which has native V4 support.

4. **Audit**: Add greatspectations spec quotes to captive-portal-site source code for CI drift detection.

---

## Sign-off

Audited by **GLM-5.2** in **opencode** on **2026-07-28**.
Target: OpenTollGate/tollgate-captive-portal-site @ main
Cashu library: @cashu/cashu-ts v2.2.2
Verdict: **WARN** — Portal V4-ready but backend V3-only creates user-facing incompatibility
