# Auditor: port move + /mints/ 500 fix (2026-09-12)

- Port 8000 on ai-legion was taken by nemo-lab-backend-1; the
  cashu-auditor was displaced (down). It now runs on **:8100** with a
  5-minute keepalive cron (`~/bin/auditor-keepalive.sh`).
- `GET /mints/` 500 root-caused: `ResponseValidationError` — 4 mint
  rows with `name = NULL` vs strict `MintRead.name: str`. Fixed in
  `~/cashu-auditor/src/schemas.py` (`Optional[str] = None`) + name
  backfill. Verified 200 with 12 mints.
- Refresher: any status check for "auditor running" must test
  `:8100/mints/`, not just pgrep uvicorn (nemo-lab also runs uvicorn).
