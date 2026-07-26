# Cross-Implementation Comparison: NUT-06 (Mint Information)

**Date:** 2026-07-26
**Spec:** cashubtc/nuts @ 734f60e — `06.md` (Mint information, `mandatory`)
**Implementations compared:**
- **cashu-cf** @ c1e3907 (TypeScript / Cloudflare Workers)
- **CDK** @ d033f1b (Rust / `cashu` + `cdk-axum` crates)
- **Nutshell** @ 18539020 (Python / FastAPI)
**Auditor model:** GLM-5.1/5.2 in opencode

---

## Summary Table

| Metric | cashu-cf | CDK | Nutshell |
|--------|----------|-----|----------|
| **Verdict** | PASS | PASS | PASS |
| **PASS** | 19 | 16 | 20 |
| **FAIL** | 0 | 0 | 0 |
| **WARN** | 2 | 1 | 0 |
| **INFO** | 0 | 3 | 0 |
| **N/A** | 0 | 0 | 0 |

---

## Consensus Areas (All Three Agree)

### Endpoint — `GET /v1/info`

All three register the mandatory endpoint at the correct path and return a JSON object:
- **cashu-cf**: Three route registrations (edge `/info` + `/v1/info`, DO router, legacy DO) — all delegate to `buildGetInfoResponse`.
- **CDK**: `.route("/info", get(get_mint_info))` inside `v1_router` nested at `/v1` → `GET /v1/info`. Returns `Json<MintInfo>`.
- **Nutshell**: `@router.get("/v1/info", response_model=GetInfoResponse)`.

### All 12 Spec-Defined Fields Modeled

The spec lists 12 optional fields (§90-101). All three implementations model every field:

| Field | Spec § | cashu-cf | CDK | Nutshell |
|-------|--------|----------|-----|----------|
| `name` | §90 | PASS | PASS (`Option<String>`) | PASS (`Optional[str]`) |
| `pubkey` | §91 | PASS (hex from keyset) | PASS (`Option<PublicKey>` → hex) | PASS (`format().hex()`) |
| `version` | §92 | PASS (`Nutshell-CF/0.0.1`) | PASS (`MintVersion` → `name/version`) | PASS (`Nutshell/0.x.x`) |
| `description` | §93 | PASS | PASS | PASS |
| `description_long` | §94 | PASS | PASS | PASS |
| `contact` | §95 | PASS (WARN: raw-string fallback) | PASS (`Vec<ContactInfo>`) | PASS (`List[MintInfoContact]`) |
| `motd` | §96 | PASS | PASS | PASS |
| `icon_url` | §97 | PASS (resolves relative paths) | PASS | PASS |
| `urls` | §98 | PASS (JSON array or CSV) | PASS (`Vec<String>`) | PASS (`List[str]`) |
| `time` | §99 | PASS (per-request `Date.now()`) | PASS (per-request `unix_time()`) | PASS (per-request `time.time()`) |
| `tos_url` | §100 | PASS | PASS | PASS |
| `nuts` | §101 | PASS | PASS (non-optional) | PASS (`Dict[int, Any]`) |

### Absent Fields Omitted (Not Null)

All three correctly omit absent optional fields rather than serializing them as `null`:
- **cashu-cf**: Conditional spread (`...condition && { field: value }`).
- **CDK**: `#[serde(skip_serializing_if = "Option::is_none")]` on all optional fields.
- **Nutshell**: `response_model_exclude_none=True` on the router decorator.

### Contact Object Shape `{method, info}`

All three model contact entries as objects with exactly `method` and `info` string fields:
- **cashu-cf**: Parses `MINT_CONTACT` env as JSON array of `{method, info}` objects.
- **CDK**: `ContactInfo { method: String, info: String }` with standard serde derive.
- **Nutshell**: `MintInfoContact(BaseModel): method: str, info: str`.

### `time` Field Freshness

All three compute `time` dynamically per-request, not cached:
- **cashu-cf**: `Math.floor(Date.now() / 1000)` in `buildGetInfoResponse`.
- **CDK**: Handler calls `.time(unix_time())` on each request, overriding any stored value.
- **Nutshell**: `time=int(time.time())` computed in the router handler.

### `version` Format `name/version`

All three use the `/` separator format per spec L92:
- **cashu-cf**: `Nutshell-CF/0.0.1` (overridable via `MINT_VERSION`).
- **CDK**: `cdk/1.2.3` (via `MintVersion` custom serde: `format!("{}/{}", name, version)`).
- **Nutshell**: `Nutshell/0.15.0` (via `_VERSION_PREFIX`).

---

## Key Divergences

### 1. Contact Field Type Safety

| Implementation | Contact Handling | Risk |
|----------------|-----------------|------|
| **cashu-cf** | Parses `MINT_CONTACT` as JSON; **falls back to raw string** if non-JSON | **WARN** — spec requires array of objects, not string |
| **CDK** | `Option<Vec<ContactInfo>>` — strictly typed; also accepts legacy array format `["method", "info"]` for backward compat | Clean — serializes as map format (spec-compliant) |
| **Nutshell** | `Optional[List[MintInfoContact]]` — strictly typed pydantic model; backward-compat contact parsing via `model_validator` | Clean |

cashu-cf's raw-string fallback (`info.ts:165-167`) would return `contact: "some string"` instead of an array if an operator sets `MINT_CONTACT` to a plain string. This is unreachable in production (all wrangler.toml environments use JSON arrays), but represents a latent type contract violation.

CDK uniquely supports *deserializing* legacy array-format contacts (`["email", "x"]`) while always *serializing* in spec-compliant map format (`{"method": "email", "info": "x"}`). This is a beneficial interop feature for parsing responses from older mints.

### 2. MintVersion Parsing Strictness (CDK-specific WARN)

CDK's `MintVersion::deserialize` (`nut06.rs:57-60`) splits on `/` and requires **exactly 2 parts**. A version string like `"cdk-mintd/v1.2.3/rc1"` or `"My Mint/v2"` would fail to deserialize.

**Recommendation:** Use `splitn(2, '/')` instead of `split('/')` so the version part can contain additional slashes. This is a theoretical robustness gap — all known Cashu implementations use single-slash version strings.

cashu-cf and Nutshell do not parse incoming version strings (they only produce them), so they don't have this issue.

### 3. `nuts` Object Optionality

| Implementation | `nuts` Field Type | Always Present? |
|----------------|-------------------|-----------------|
| **cashu-cf** | Always constructed in response | Yes |
| **CDK** | `pub nuts: Nuts` (non-optional) | **Yes** — always serialized, even when all sub-fields are defaults |
| **Nutshell** | `nuts: Dict[int, Any]` | Yes — always populated from `mint_features` property |

The spec marks `nuts` as `(optional)` (§101), but all three always include it. This is not a violation — "optional" means the mint CAN include it, and always including it is a valid, more informative choice. CDK explicitly notes this in INFO-1.

### 4. NUT Advertisement Scope

The three implementations advertise different sets of NUTs in the `nuts` object:

| NUT | cashu-cf | CDK | Nutshell |
|-----|----------|-----|----------|
| 4 (Mint) | ✅ methods + disabled | ✅ methods + disabled | ✅ methods + disabled |
| 5 (Melt) | ✅ methods + disabled | ✅ methods + disabled | ✅ methods + disabled |
| 7 (Token state) | ✅ supported | ✅ supported | ✅ supported |
| 8 (Fee return) | ✅ supported | ✅ supported | ✅ supported |
| 9 (Restore) | ✅ supported | ✅ supported | ✅ supported |
| 10 (Spending conditions) | ✅ supported | ✅ supported | ✅ supported |
| 11 (P2PK) | ✅ supported | ✅ supported | ✅ supported |
| 12 (DLEQ) | ✅ supported (hardcoded true) | ✅ supported | ✅ supported |
| 13 (Det. secrets) | ❌ omitted (wallet-only) | ❌ omitted | ❌ omitted (wallet-only) |
| 14 (HTLC) | ✅ supported | ✅ supported | ✅ supported |
| 15 (MPP) | ❌ not advertised | ✅ conditional | ✅ conditional |
| 17 (WebSocket) | ❌ **intentionally omitted** (ISSUE-026) | ✅ conditional | ✅ conditional |
| 19 (Cache) | ✅ conditional | ✅ conditional | ✅ conditional |
| 20 (Quote sig) | ✅ supported | ✅ supported | ✅ supported |
| 21 (Clear auth) | ❌ not advertised | ✅ conditional | ✅ conditional |
| 22 (Blind auth) | ❌ not advertised | ✅ conditional | ✅ conditional |
| 23 (Mint quote sig) | ✅ supported | ❌ not in struct | ❌ not advertised |
| 29 (Batch mint) | ✅ max_batch_size + methods | ✅ conditional | ✅ supported + max_batch_size |

**Key observations:**
- **cashu-cf** is the most conservative — it omits NUT-15 (MPP), NUT-17 (WebSocket), NUT-21, and NUT-22. NUT-17 omission is intentional (ISSUE-026: WS disabled).
- **CDK** has the broadest NUT coverage, including NUT-21/22 auth settings and conditional serialization for NUT-15/17/21/22/29.
- **Nutshell** covers 15 NUTs including conditional NUT-15/17/19/21/22.
- All three correctly omit NUT-13 (wallet-only feature, no mint implementation).

### 5. Placeholder Contact Data (cashu-cf-specific operational issue)

cashu-cf's wrangler.toml contains placeholder contact data across all 5 environments: `contact@me.com`, `@me`, `npub1337`, `uncle_rick`, `pavol`. ISSUE-020 is marked `done` (code fix delivered — configurable contact, `INFO_HIDE_CONTACT` flag, empty array support), but the operator has not updated the data.

**Impact:** Wallets that surface contact info display fake data. Not a spec violation (contact is optional and the array format is valid), but a data quality issue. CDK and Nutshell do not have equivalent placeholder data issues in their audited code.

### 6. Configuration Sources

| Implementation | How Fields Are Populated |
|----------------|--------------------------|
| **cashu-cf** | Environment variables (`MINT_NAME`, `MINT_CONTACT`, `MINT_URLS`, etc.) via `wrangler.toml`; conditional feature flags (`NUT19_ENABLED`, `INFO_HIDE_*`) |
| **CDK** | Config file (`[mint_info]` TOML) + env vars (`CDK_MINTD_MINT_*`) + builder pattern + database persistence (KV store) |
| **Nutshell** | Settings object (`settings.mint_info_*`) from `.env` / config; router injects some fields directly |

CDK has the most sophisticated configuration pipeline (4 sources: config file, env vars, builder, DB), while cashu-cf uses Cloudflare's env binding model and Nutshell uses a centralized settings object.

### 7. Helper/Accessor Methods

| Implementation | Internal Helpers | Impact on Wire |
|----------------|-----------------|----------------|
| **cashu-cf** | `resolveIconUrl` (relative→absolute URL resolution) | Improves `icon_url` quality |
| **CDK** | `protected_endpoints()`, `openid_discovery()`, `client_id()`, `bat_max_mint()`, `supported_units()` | None — internal domain logic only |
| **Nutshell** | `MintInfo` wallet-side model with `supports_mpp`, `requires_clear_auth_path`, etc. | None — wallet-side helpers |

CDK's `MintInfo` struct includes the most internal helper methods for deriving auth-related settings from the nested `nuts` structure. These are clean API design and do not affect wire serialization.

---

## Overall Assessment

**All three implementations PASS NUT-06.** This is the simplest mandatory spec — one GET endpoint returning a JSON info object with all-optional fields. All three correctly model every field, omit absent fields, compute `time` per-request, and use the `name/version` format.

### Cleanliness Ranking

1. **Nutshell (cleanest):** 20 PASS, 0 WARN, 0 INFO. No findings at all. Models all fields with correct types, uses `response_model_exclude_none=True`, computes `time` fresh per-request. The most NUTs advertised (15) with correct per-NUT settings shapes.

2. **CDK:** 16 PASS, 1 WARN, 3 INFO. The single WARN (MintVersion multi-slash rejection) is theoretical. Notable strengths: broadest NUT coverage, legacy array-format contact deserialization for interop, sophisticated 4-source configuration pipeline, and the only implementation with overflow-safe integer handling in version parsing.

3. **cashu-cf:** 19 PASS, 2 WARN. Both WARNs are operational rather than code defects: (1) the raw-string contact fallback is unreachable in production, and (2) placeholder contact data is an operator data issue (ISSUE-020 code fix is delivered). Notable strengths: relative-to-absolute URL resolution for `icon_url`, conditional feature flags for hiding fields, and ISSUE-014 regression verified (USD advertise/reject consistency).

### Interoperability
**Zero interoperability risk.** All three produce valid `GetInfoResponse` JSON objects that any Cashu wallet can parse. The `nuts` object scopes differ (cashu-cf advertises fewer optional NUTs), but this correctly reflects each implementation's actual feature support — advertising features you don't implement would be worse.

### Cross-Cutting Observation
NUT-06 serves as the **capability discovery** mechanism for the Cashu ecosystem. The divergence in `nuts` advertisement scope across implementations is healthy — it reflects genuine differences in feature support. The spec correctly delegates nested NUT settings to "each NUT separately" (§101), and all three implementations honor this by structuring their `nuts.4`/`nuts.5` entries per NUT-04/05 sub-specs.
