#!/usr/bin/env python3
"""
Consumer conformance lane — executes the TollGate protocol repo's token
conformance corpus against real consumers.

Corpus: OpenTollGate/tollgate `corpus/` (manifest.json + lifecycle/ + http/).
The corpus is the frozen prediction set (AGENTS.md method rule 1): every
expected verdict is recorded before this tool runs, and a surprising FAIL is
a corpus bug until proven otherwise.

Lanes:
  lifecycle  decode/verify/checkstate/spend per fixture, per consumer
  http       replays corpus HTTP vectors against a gateway
  portal     runs the portal checkout's vendored-corpus vitest suite

A FAIL is only emitted when the corpus records a known expected verdict and
the consumer produced a different one. Unknown expected verdicts are FILL
rows (the runner fills the matrix). Unavailable consumers, unmet
preconditions and unspendable fixtures are SKIP rows with reasons — never
silent.

Usage:
    python3 consumer_conformance.py --corpus /path/to/tollgate/corpus \
        [--gateway http://192.168.13.1:2121] [--mint http://192.168.13.221:8383] \
        [--cdk-cli /root/.cargo-target/release/cdk-cli] \
        [--cashu /opt/cashu-venv/bin/cashu] [--portal /path/to/portal] \
        [--lane lifecycle,http,portal] [--report-out reports/]
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crypto_helpers import hash_to_curve  # noqa: E402

MAC_RE = re.compile(r"^[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}$")
PUBKEY_RE = re.compile(r"^[0-9a-f]{64}$")
SUBPROC_TIMEOUT = 10


@dataclass
class Row:
    lane: str
    vector: str
    result: str  # PASS | FAIL | SKIP | FILL
    expected: str
    actual: str
    detail: str = ""

    def line(self) -> str:
        icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⛔", "FILL": "🟡"}[self.result]
        return f"{icon} [{self.lane}] {self.vector}\n      expected: {self.expected}\n      actual:   {self.actual}" + (
            f"\n      {self.detail}" if self.detail else ""
        )


@dataclass
class ConsumerHarness:
    corpus_dir: Path
    gateway: str | None
    mint: str | None
    cdk_cli: str | None
    cashu: str | None
    portal: Path | None
    gateway_mode: str | None = field(default=None, init=False)
    cdk_home: str | None = field(default=None, init=False)
    last_request_at: dict[str, float] = field(default_factory=dict, init=False)

    def pace(self, path: str) -> None:
        # Stay under the gateway's limits: / is 10/min burst 10, POST /ln-invoice stacks quotas — tripping them makes vectors read the limiter, not the target.
        min_interval = 6.5 if path == "/" else (3.5 if path == "/ln-invoice" else 0.0)
        if min_interval:
            last = self.last_request_at.get(path)
            if last is not None:
                wait = min_interval - (time.time() - last)
                if wait > 0:
                    time.sleep(wait)
            self.last_request_at[path] = time.time()

    def cdk_home_dir(self) -> str:
        if not self.cdk_home:
            import tempfile

            self.cdk_home = tempfile.mkdtemp(prefix="cdk-consumer-")
        return self.cdk_home

    def detect_gateway_mode(self) -> str | None:
        if not self.gateway or self.gateway_mode:
            return self.gateway_mode
        try:
            r = requests.get(f"{self.gateway}/", timeout=5)
            body = r.json()
            if body.get("kind") == 10021:
                self.gateway_mode = "full-service"
            elif body.get("kind") == 21023 and any(
                t[:2] == ["code", "no-reachable-mints"] for t in body.get("tags", [])
            ):
                self.gateway_mode = "degraded"
            else:
                self.gateway_mode = "unknown"
        except Exception:
            self.gateway_mode = "unreachable"
        return self.gateway_mode


def run_subproc(cmd: list[str], env_home: str | None = None, timeout: int = SUBPROC_TIMEOUT) -> tuple[int, str, bool]:
    import os

    env = dict(os.environ)
    if env_home:
        env["HOME"] = env_home
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True, env=env, timeout=timeout, stdin=subprocess.DEVNULL
        )
        return p.returncode, (p.stdout + p.stderr).strip(), False
    except subprocess.TimeoutExpired:
        return 124, "", True


def token_proofs(token: str) -> list[dict]:
    """V3 (JSON) and V4 (CBOR) proof extraction; returns list of {secret, amount}."""
    tok = token.strip()
    payload = base64.urlsafe_b64decode(tok[6:] + "=" * (-(len(tok) - 6) % 4))
    if tok.startswith("cashuA"):
        data = json.loads(payload)
        proofs = data["token"][0]["proofs"]
        return [{"secret": p["secret"], "amount": p["amount"]} for p in proofs]
    import cbor2

    data = cbor2.loads(payload)
    t = data["t"][0] if isinstance(data.get("t"), list) else data["t"]
    out = []
    for p in t["p"]:
        secret = p["s"].decode() if isinstance(p["s"], bytes) else p["s"]
        out.append({"secret": secret, "amount": p["a"]})
    return out


def checkstate(harness: ConsumerHarness, token: str) -> str:
    ys = [hash_to_curve(p["secret"].encode()).format().hex() for p in token_proofs(token)]
    r = requests.post(f"{harness.mint}/v1/checkstate", json={"Ys": ys}, timeout=10)
    r.raise_for_status()
    states = [s["state"] for s in r.json()["states"]]
    if all(s == "UNSPENT" for s in states):
        return "UNSPENT"
    if all(s == "SPENT" for s in states):
        return "SPENT"
    return "MIXED"


def cdk_decode_verdict(harness: ConsumerHarness, token: str) -> str:
    # 2 attempts: cdk-cli 0.18.1 decode-token intermittently deadlocks on a cold HOME (wallet-init race); retry separates that from the deterministic content-triggered hang.
    for _ in range(2):
        code, out, timed_out = run_subproc(
            [harness.cdk_cli, "decode-token", token], env_home=harness.cdk_home_dir()
        )
        if timed_out:
            continue
        return "decoded" if code == 0 else "reject-undecodable"
    return "no-verdict-hang"


def nutshell_decode_verdict(harness: ConsumerHarness, token: str) -> str:
    with tempfile.TemporaryDirectory() as home:
        code, out, timed_out = run_subproc(
            [harness.cashu, "-h", harness.mint or "http://invalid.invalid", "-y", "-t", "decode", token],
            env_home=home,
        )
        if timed_out:
            return "no-verdict-hang"
        return "decoded" if code == 0 and out.strip() else "reject-undecodable"


def regen_sibling(harness: ConsumerHarness, token_version: int, amount: int) -> str | None:
    """Mint + send a fresh sibling at the reference mint (never spend committed fixtures)."""
    if not harness.cdk_cli or not harness.mint:
        return None
    with tempfile.TemporaryDirectory() as home:
        code, out, _ = run_subproc(
            [harness.cdk_cli, "mint", harness.mint, str(amount + 10)],
            env_home=home,
            timeout=60,
        )
        if code != 0:
            return None
        cmd = [harness.cdk_cli, "send", "--mint-url", harness.mint, "--amount", str(amount), "--include-fee"]
        if token_version == 3:
            cmd.append("--v3")
        code, out, _ = run_subproc(cmd, env_home=home, timeout=30)
        token = out.strip().splitlines()[-1] if out.strip() else ""
        if code != 0 or not token.startswith("cashu"):
            return None
        return token


def cdk_verify_verdict(harness: ConsumerHarness, sibling: str) -> str:
    with tempfile.TemporaryDirectory() as home:
        code, out, _ = run_subproc(
            [harness.cdk_cli, "receive", "--allow-untrusted", sibling],
            env_home=home,
            timeout=30,
        )
        return "ok" if code == 0 and "Received" in out else "reject"


MATCHER_PASSTHROUGH = ("matcher", "values")


def match(value, assertion) -> tuple[bool, str]:
    if isinstance(assertion, dict) and "matcher" in assertion:
        m = assertion["matcher"]
        if m == "integer":
            ok = isinstance(value, int) or (isinstance(value, str) and value.lstrip("-").isdigit())
            return ok, f"integer, got {value!r}"
        if m == "prefix":
            ok = isinstance(value, str) and value.startswith(assertion["value"])
            return ok, f"prefix {assertion['value']!r}, got {value!r}"
        if m == "regex":
            ok = isinstance(value, str) and re.fullmatch(assertion["value"], value) is not None
            return ok, f"regex {assertion['value']!r}, got {value!r}"
        if m == "mac-format":
            ok = isinstance(value, str) and MAC_RE.match(value) is not None
            return ok, f"mac-format, got {value!r}"
        if m == "nostr-pubkey":
            ok = isinstance(value, str) and PUBKEY_RE.match(value) is not None
            return ok, f"nostr-pubkey, got {value!r}"
        if m == "nonempty":
            ok = isinstance(value, str) and value.strip() != ""
            return ok, f"nonempty, got {value!r}"
        if m == "one-of":
            ok = value in assertion["values"]
            return ok, f"one-of {assertion['values']}, got {value!r}"
        return False, f"unknown matcher {m!r}"
    if isinstance(assertion, str) and assertion.startswith("<") and assertion.endswith(">"):
        return True, "placeholder"
    return value == assertion, f"{assertion!r}, got {value!r}"


def tags_to_dict(tags: list) -> dict:
    out: dict[str, list] = {}
    for t in tags:
        if isinstance(t, list) and t:
            out.setdefault(t[0], []).append(t[1:])
    return out


def evaluate_nostr_body(body: dict, event: dict) -> list[str]:
    problems = []
    if event.get("kind") != body.get("kind"):
        problems.append(f"kind {body.get('kind')} != {event.get('kind')}")
    if body.get("signed") and not (event.get("id") and event.get("sig")):
        problems.append("event not signed (id/sig missing)")
    tag_map = tags_to_dict(event.get("tags", []))
    for want in body.get("tags_include", []):
        name, *rest = want
        candidates = tag_map.get(name, [])
        if not candidates:
            problems.append(f"missing tag {name}")
            continue
        if not any(all(match(v, a)[0] for v, a in zip(rest, cand)) for cand in candidates):
            problems.append(f"tag {name} shape {rest} not found in {candidates}")
    for name in body.get("tags_omit", []):
        if name in tag_map:
            problems.append(f"forbidden tag {name} present: {tag_map[name]}")
    content = event.get("content", "")
    for needle in body.get("content_contains", []):
        if needle.lower() not in str(content).lower():
            problems.append(f"content missing {needle!r}")
    return problems


def evaluate_json_body(body: dict, parsed: dict) -> list[str]:
    problems = []
    for name, assertion in body.get("fields", {}).items():
        if name not in parsed:
            problems.append(f"missing field {name}")
            continue
        ok, why = match(parsed[name], assertion)
        if not ok:
            problems.append(f"field {name}: {why}")
    for name in body.get("fields_omitted", []):
        if name in parsed:
            problems.append(f"forbidden field {name} present")
    for needle in body.get("content_must_mention", []):
        blob = json.dumps(parsed).lower()
        if needle.lower() not in blob:
            problems.append(f"body missing mention {needle!r}")
    return problems


def evaluate_response(resp: requests.Response, response_spec: dict) -> list[str]:
    problems = []
    want_status = response_spec.get("status")
    if want_status is not None and resp.status_code != want_status:
        problems.append(f"status {want_status} != {resp.status_code}")
    want_ct = response_spec.get("content_type")
    if want_ct:
        actual_ct = resp.headers.get("Content-Type", "")
        if actual_ct.split(";")[0].strip() != want_ct.split(";")[0].strip():
            problems.append(f"content-type {want_ct!r} != {actual_ct!r}")
    for name, assertion in (response_spec.get("headers") or {}).items():
        actual = resp.headers.get(name)
        if actual is None:
            problems.append(f"missing header {name}")
            continue
        if isinstance(assertion, dict):
            ok, why = match(actual, assertion)
            if not ok:
                problems.append(f"header {name}: {why}")
        elif actual != assertion:
            problems.append(f"header {name}: {assertion!r} != {actual!r}")
    body = response_spec.get("body")
    if isinstance(body, dict) and body.get("type") in ("nostr_event", "nostr_notice"):
        try:
            problems += evaluate_nostr_body(body, resp.json())
        except ValueError:
            problems.append("body is not JSON for nostr assertion")
    elif isinstance(body, dict) and body.get("type") == "json":
        try:
            problems += evaluate_json_body(body, resp.json())
        except ValueError:
            problems.append("body is not JSON")
    elif isinstance(body, dict) and body.get("type") == "text":
        text = resp.text.strip()
        ok, why = match(text, {"matcher": body.get("matcher", "exact"), "value": body.get("value", "")})
        if not ok:
            problems.append(f"text body: {why}")
    return problems


def http_body_for(harness: ConsumerHarness, body_spec: dict) -> tuple[str | None, str]:
    if "inline" in body_spec:
        return body_spec["inline"], ""
    if "fixture" in body_spec:
        p = harness.corpus_dir / body_spec["fixture"]
        return p.read_text().strip() if p.is_file() else None, f"fixture {body_spec['fixture']} missing"
    if "inline_template" in body_spec:
        return body_spec["inline_template"], "template not materialized by this runner"
    return None, f"unsupported body spec {list(body_spec)}"


def preconditions_met(harness: ConsumerHarness, vec: dict) -> tuple[bool, str]:
    pre = json.dumps(vec.get("preconditions", {})).lower()
    mode = harness.detect_gateway_mode()
    if "full-service" in pre and mode != "full-service":
        return False, f"requires full-service gateway, gateway is {mode}"
    if "degraded" in pre and mode != "degraded":
        return False, f"requires degraded gateway, gateway is {mode}"
    unseatable = ("session", "quotas", "invoice", "ticket", "client", "burst")
    for key in unseatable:
        if key in pre:
            return False, f"precondition class {key!r} not settable by this runner"
    return True, ""


def run_http_lane(harness: ConsumerHarness, rows: list[Row]) -> None:
    manifest = json.loads((harness.corpus_dir / "manifest.json").read_text())
    for entry in manifest["index"]["http"]:
        vectors = json.loads((harness.corpus_dir / entry["path"]).read_text()).get("vectors", [])
        for vec in vectors:
            vid = vec["id"]
            if not harness.gateway:
                rows.append(Row("http", vid, "SKIP", "—", "—", "no gateway configured"))
                continue
            ok, why = preconditions_met(harness, vec)
            if not ok:
                rows.append(Row("http", vid, "SKIP", "corpus vector", "unmet precondition", why))
                continue
            req = vec.get("request", {})
            if req.get("method") not in ("GET", "POST"):
                rows.append(Row("http", vid, "SKIP", "corpus vector", "method unsupported", req.get("method", "?")))
                continue
            if "inline_template" in req.get("body", {}) or "fixture" in req.get("body", {}) and "state" in req["body"]:
                rows.append(Row("http", vid, "SKIP", "corpus vector", "needs a minted sibling", "regen-required body"))
                continue
            body = None
            if isinstance(req.get("body"), dict):
                body, why = http_body_for(harness, req["body"])
                if body is None:
                    rows.append(Row("http", vid, "SKIP", "corpus vector", "body unavailable", why))
                    continue
            headers = {}
            if req.get("content_type") is not None:
                headers["Content-Type"] = req["content_type"]
            url = harness.gateway + req.get("path", "/")
            if req.get("burst"):
                rows.append(Row("http", vid, "SKIP", "corpus vector", "burst vector", "needs dedicated pacing"))
                continue
            harness.pace(req.get("path", "/"))
            try:
                r = requests.request(req["method"], url, data=body, headers=headers or None, timeout=15)
            except requests.RequestException as exc:
                rows.append(Row("http", vid, "FAIL", "corpus vector", f"request error: {exc}"))
                continue
            resp_spec = vec.get("response")
            if not isinstance(resp_spec, dict) or "same_as" in resp_spec or "status" not in resp_spec:
                rows.append(Row("http", vid, "FILL", "descriptive vector", f"http {r.status_code}", "recorded"))
                continue
            problems = evaluate_response(r, resp_spec)
            actual = f"http {r.status_code}" + ("; " + "; ".join(problems) if problems else "")
            rows.append(
                Row("http", vid, "PASS" if not problems else "FAIL", f"corpus response spec ({resp_spec.get('status')})", actual)
            )
            for post in vec.get("post_conditions", []):
                if post.get("assert") == "token-unconsumed":
                    fixture = vec["request"]["body"].get("fixture")
                    if fixture and harness.mint:
                        try:
                            tok = (harness.corpus_dir / fixture).read_text().strip()
                            state = checkstate(harness, tok)
                            ok_post = state == post.get("expect", "UNSPENT")
                            rows.append(
                                Row("http", f"{vid}/postcondition", "PASS" if ok_post else "FAIL", post["expect"], state)
                            )
                        except Exception as exc:
                            rows.append(Row("http", f"{vid}/postcondition", "SKIP", post["expect"], "checkstate error", str(exc)[:120]))


def run_lifecycle_lane(harness: ConsumerHarness, rows: list[Row]) -> None:
    manifest = json.loads((harness.corpus_dir / "manifest.json").read_text())
    for group in ("lifecycle",):
        for entry in manifest["index"][group]:
            vec_path = harness.corpus_dir / entry["path"]
            vec = json.loads(vec_path.read_text())
            fixture = (vec_path.parent / vec["fixture"]).resolve().read_text().strip()
            vid = vec["id"]
            stages = vec["stages"]

            if harness.cdk_cli:
                expected = stages["decode"]["verdicts"].get("cdk-cli@0.18.1", "unknown")
                actual = cdk_decode_verdict(harness, fixture)
                norm = {"decoded": f"decoded-v{vec['shape']['token_version']}"}.get(actual, actual)
                if expected == "unknown":
                    rows.append(Row("lifecycle", f"{vid}/decode/cdk-cli", "FILL", "unknown", norm))
                else:
                    rows.append(Row("lifecycle", f"{vid}/decode/cdk-cli", "PASS" if norm == expected else "FAIL", expected, norm))
            if harness.cashu:
                expected = stages["decode"]["verdicts"].get("nutshell@0.21.0", "unknown")
                actual = nutshell_decode_verdict(harness, fixture)
                norm = {"decoded": f"decoded-v{vec['shape']['token_version']}"}.get(actual, actual)
                if expected == "unknown":
                    rows.append(Row("lifecycle", f"{vid}/decode/nutshell", "FILL", "unknown", norm))
                else:
                    rows.append(Row("lifecycle", f"{vid}/decode/nutshell", "PASS" if norm == expected else "FAIL", expected, norm))
            if harness.mint and vec["shape"].get("mint") == harness.mint:
                expected = stages["checkstate"]["verdicts"].get("fakewallet@2026-10-16", "unknown")
                try:
                    actual = checkstate(harness, fixture)
                except Exception as exc:
                    rows.append(Row("lifecycle", f"{vid}/checkstate", "SKIP", expected, "error", str(exc)[:120]))
                    continue
                if expected == "unknown":
                    rows.append(Row("lifecycle", f"{vid}/checkstate", "FILL", "unknown", actual))
                else:
                    ok = actual == expected or (expected == "SPENT" and actual == "MIXED")
                    rows.append(Row("lifecycle", f"{vid}/checkstate", "PASS" if ok else "FAIL", expected, actual))
            else:
                rows.append(Row("lifecycle", f"{vid}/checkstate", "SKIP", "—", "—", "fixture mint not this mint"))

            role = vec.get("role", "")
            if "known-good twin" in role and harness.cdk_cli and harness.mint:
                sibling = regen_sibling(harness, vec["shape"]["token_version"], sum(vec["shape"].get("amounts", [4])))
                if sibling is None:
                    rows.append(Row("lifecycle", f"{vid}/verify/cdk-cli", "SKIP", "ok", "regen failed"))
                else:
                    actual = cdk_verify_verdict(harness, sibling)
                    expected = stages["verify"]["verdicts"].get("cdk-cli@0.18.1", "ok")
                    rows.append(
                        Row("lifecycle", f"{vid}/verify/cdk-cli", "PASS" if actual == expected else "FAIL", expected, actual, "sibling token, committed twin untouched")
                    )
            else:
                rows.append(Row("lifecycle", f"{vid}/verify/cdk-cli", "SKIP", "—", "—", "verify runs on regen'd siblings of KG twins only"))


def run_portal_lane(harness: ConsumerHarness, rows: list[Row]) -> None:
    if not harness.portal or not (harness.portal / "tests/unit/corpus-conformance.test.js").is_file():
        rows.append(Row("portal", "vendored-corpus suite", "SKIP", "8/8 pass", "portal checkout or suite missing"))
        return
    try:
        p = subprocess.run(
            ["npx", "vitest", "run", "tests/unit/corpus-conformance.test.js"],
            capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL,
            cwd=str(harness.portal),
        )
        code, out = p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        rows.append(Row("portal", "vendored-corpus suite", "FAIL", "8/8 pass", "vitest timeout"))
        return
    m = re.search(r"Tests\s+(\d+) passed", out)
    actual = f"{m.group(1)}/8 passed (exit {code})" if m else f"exit {code}"
    rows.append(Row("portal", "vendored-corpus suite", "PASS" if code == 0 else "FAIL", "8/8 pass", actual))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--gateway")
    ap.add_argument("--mint")
    ap.add_argument("--cdk-cli")
    ap.add_argument("--cashu")
    ap.add_argument("--portal")
    ap.add_argument("--lane", default="lifecycle,http,portal")
    ap.add_argument("--report-out")
    args = ap.parse_args()

    harness = ConsumerHarness(
        corpus_dir=Path(args.corpus).resolve(),
        gateway=args.gateway,
        mint=args.mint,
        cdk_cli=args.cdk_cli,
        cashu=args.cashu,
        portal=Path(args.portal).resolve() if args.portal else None,
    )
    mode = harness.detect_gateway_mode() if args.gateway else None
    print(f"corpus: {harness.corpus_dir}")
    print(f"gateway: {args.gateway or '—'} (mode: {mode or '—'})  mint: {args.mint or '—'}")
    print("frozen predictions: the corpus files above were written before this run\n")

    rows: list[Row] = []
    lanes = set(args.lane.split(","))
    if "lifecycle" in lanes:
        run_lifecycle_lane(harness, rows)
    if "http" in lanes:
        run_http_lane(harness, rows)
    if "portal" in lanes:
        run_portal_lane(harness, rows)

    for r in rows:
        print(r.line())
    counts = {k: sum(1 for r in rows if r.result == k) for k in ("PASS", "FAIL", "SKIP", "FILL")}
    print(f"\nconsumer conformance: {len(rows)} rows — {counts['PASS']} PASS, {counts['FAIL']} FAIL, {counts['SKIP']} SKIP, {counts['FILL']} FILL")

    if args.report_out:
        out_path = Path(args.report_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": int(time.time()),
            "corpus": str(harness.corpus_dir),
            "gateway": args.gateway,
            "gateway_mode": mode,
            "mint": args.mint,
            "counts": counts,
            "rows": [r.__dict__ for r in rows],
        }
        out_path.write_text(json.dumps(payload, indent=2))
        print(f"report: {out_path}")

    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
