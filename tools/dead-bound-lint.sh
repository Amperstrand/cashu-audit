#!/usr/bin/env bash
# dead-bound-lint.sh — flag numeric bounds that compare against TYPE maxima
# where DOMAIN bounds are required. Review aid, not CI: every hit is a
# "prove the domain range" instruction.
#
# Born from the #1212 review miss (2026-11-13): `fee > math.MaxInt64` was the
# ONLY check on a caller-supplied fee — a bound no sane fee ever reaches, i.e.
# decoration — while the domain bound (fee vs the operation's FeeReserveMSat)
# was absent. felixfelix-bot found it with an on-head probe; our review had
# read the same line and moved on. This lint exists so the line glows first.
#
# Usage: dead-bound-lint.sh <go-files-or-dirs>
set -u
TARGETS=("$@")
[ ${#TARGETS[@]} -eq 0 ] && TARGETS=(.)
echo "== type-max bounds in validation/arithmetic paths (prove the DOMAIN range) =="
grep -rn -E '(>|>=|<|<=)[[:space:]]*(math\.Max(U?Int(8|16|32|64)?)|1[[:space:]]*<<[[:space:]]*(31|32|63|64)|0x7[Ff]+[Ff]+[Ff]+[Ff]+)' \
  --include='*.go' "${TARGETS[@]}" 2>/dev/null | \
  grep -vE '_test\.go|/\* dead-bound-lint:justify \*/' | \
  while read -r line; do
    case "$line" in
      /*) f=$(cut -d: -f1 <<<"$line"); n=$(cut -d: -f2 <<<"$line");;
      *) f="${TARGETS[0]}"; n=$(cut -d: -f1 <<<"$line");;
    esac
    echo "  $f:$n"
    sed -n "${n}p" "$f" | sed 's/^\s*/    /'
    echo "    -> ACTION: name the domain-valid range this field can take; if the type"
    echo "       maximum is genuinely the contract, annotate the line with"
    echo "       /* dead-bound-lint:justify <reason> */"
  done
echo "(also check: comparisons against sys.maxsize in python, U?INT._MAX in C)"
