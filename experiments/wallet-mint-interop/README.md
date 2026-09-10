# wallet x mint interop experiment

Ansible-orchestrated, detached, docker-only. Edit `matrix.yml` (mints /
wallets / flows — pure variables), then:

    ansible-playbook -i ansible/inventory.ini ansible/deploy.yml    # fire
    ansible-playbook -i ansible/inventory.ini ansible/collect.yml   # collect when DONE

Local (no ansible): `python3 runner.py`. Artifacts per run:
`artifacts/<run>/{grid.json, grid.md, status.json, DONE}` + per-cell
`output.txt` / `wire.ndjson` (every HTTP body via fetch interceptor) /
`result.json`. Driver contract (QIR pattern): env MINT_URL/TESTCASE/
ARTIFACT_DIR; exit 0 PASS / 1 FAIL / 127 SKIP — unsupported is a verdict,
never an experiment error. Design sources: quic-interop-runner (registry +
env/exit contract + per-cell logs), grpc interop_matrix (version axis),
mcpbench (declarative N x N). Token-efficient by construction: nothing to
watch; collect once when DONE exists.
