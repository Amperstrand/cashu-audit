# Spec Quote Conventions (greatspectations)

This project uses [greatspectations](https://github.com/rustyrussell/greatspectations) to bind Cashu NUT spec text to source code, catching drift between spec and implementation.

## Comment syntax

Verbatim spec quotes use the `// NUT #NN:` prefix (note: space, hash, colon):

```typescript
// NUT #04: Mints **MUST** include `amount_paid`, `amount_issued`, and `updated_at` in all mint quote responses.
const response = { amount_paid: 0, amount_issued: 0, updated_at: nowSec() };
```

Error-code quotes use `// ERRORS:` (single source, no id needed):

```typescript
// ERRORS: Quote request is not paid
QUOTE_NOT_PAID: 20001,
```

## Critical: copy from raw markdown, not rendered docs

The tool verifies byte-exact matches (after whitespace normalization). Markdown formatting markers must be preserved:

- `**MUST**` not `MUST` — the `**` bold markers are part of the spec text
- `` `code` `` not `code` — backticks are preserved
- `[link][01]` — link syntax is preserved

If you copy text from rendered GitHub/docs, you'll lose markdown markers and `spectate check` will fail. Always copy from the raw `.md` source in `nuts/NN.md`.

## Co-existence with legacy comments

Existing `// NUT-XX: <paraphrase>` comments (without `#`) are silently ignored by the tool — they lack the required `#id` for dir+pattern sources. These stay as developer documentation; only `// NUT #XX:` style is mechanically verified.

### Intentional duplication near error codes

In `src/utils/error-handling.ts`, you'll see both `// ERRORS: <verbatim>` and `// NUT-04: <paraphrase>` comments on adjacent lines:

```typescript
// ERRORS: Quote request is not paid        ← validated against error_codes.md
QUOTE_NOT_PAID: 20001,  // NUT-04: Quote request is not paid   ← developer paraphrase
```

This is **intentional**: the `// ERRORS:` line is mechanically verified against `nuts/error_codes.md` by greatspectations, while the inline `// NUT-04:` paraphrase provides developer-facing context linking the code to the NUT-04 spec. They bind to different spec sources (error_codes.md vs 04.md) and serve different purposes. Do not remove either without updating the friction doc.

## Avoid: section-header comments with NUT-XX prefix

Comments like `// NUT-20 errors (spec)` (no colon after marker) trigger parse errors. Reword to `// Errors (NUT-20, spec)` — move the NUT reference out of prefix position.

## Running checks

```bash
npm run spec:check     # exit 0 = all verbatim quotes match spec
npm run spec:coverage  # reports uncovered spec sections
```

## Adding new quotes

1. Read the spec at `nuts/NN.md` (raw markdown)
2. Find the code that implements the requirement
3. Copy the spec text verbatim (including `**`, backticks)
4. Add as `// NUT #NN: <verbatim text>` above the implementing code
5. Run `npm run spec:check` — must exit 0
6. If it fails, check for markdown markers you missed
