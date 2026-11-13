#!/usr/bin/env bash
# scenario-drift-lint.sh — flag name/assertion drift in conformance scenarios.
#
# murdawkmedia's 2026-11-12 fixture audit found a scenario NAMED "cached"
# whose PASS accepted any second 200, with the distinction ("non-identical
# body") merely REPORTED in the note. The general defect class: a scenario's
# note mentions a distinction its verdict does not gate on.
#
# This lint greps for the smell: PASS-notes containing parenthesised hedges
# and comparisons that suggest an unchecked distinction, plus FAIL-notes that
# describe conditions the code never tests. It is a prompt to re-read the
# assertion, not a verdict.
set -u
cd "$(dirname "$0")/../conformance/scenarios"
rc=0
echo "== PASS notes that report distinctions — verify each is GATED, not just mentioned =="
grep -rn -B0 -A0 'Result.PASS' . --include='*.py' | grep -E '\((non-identical|identical|but|however|unexpected|degraded|partial)[^)]*\)' && rc=1
echo "== conditional-language in PASS strings =="
grep -rn 'Result.PASS' . --include='*.py' -A1 | grep -iE '"(cached|valid|ok)[^"]*\bif\b' && rc=1
echo "== name/assertion vocabulary check: names promising equality/identity =="
for f in *.py; do
  python3 - "$f" <<'EOF'
import re, sys
src = open(sys.argv[1]).read()
for m in re.finditer(r'@scenario\("([^"]+)"', src):
    name = m.group(1)
    if re.search(r'(identical|byte|cached|exact|equality)', name):
        body = src[m.end():m.end()+2500]
        if not re.search(r'(==\s*b1|==\s*first|body\s*==|identical)', body):
            print(f"  {sys.argv[1]}: {name} — name promises identity; no comparison found nearby")
            globals()['rc'] = 1
EOF
done
[ $rc -eq 0 ] && echo "clean: no drift smells found" || echo "REVIEW NEEDED: re-read the flagged assertions against their names (EXTERNAL-CLAIMS-CHECKLIST rule 1)"
exit $rc

echo "== type-equality check: direct body == comparisons without canonicalization =="
grep -rn -E 'b2 == b1|body2 == body1|resp2 == resp1|\.json\(\) ==' . --include='*.py' | grep -v canon && rc=1
echo "(any hit above: replace with canonical-dump comparison — see negative_controls.py canon())"
