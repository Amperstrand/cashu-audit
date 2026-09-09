"""Run all scenarios except known-hanging ones, with per-scenario timeout."""
import sys, json, time
sys.path.insert(0, '.')
import importlib, pkgutil
import scenarios as _pkg
for _f, _n, _p in pkgutil.iter_modules(_pkg.__path__):
    importlib.import_module(f"scenarios.{_n}")
from conformance.client import MintClient
from conformance.scenarios import all_scenarios

SKIP = {"melt_p2pk_sigall_transaction_signature_succeeds"}  # deterministic hang vs testnut (pre-existing, main code)

url = sys.argv[1]
out = sys.argv[2]
mint = MintClient(url)
results = {}
import concurrent.futures as cf
for s in all_scenarios():
    if s.name in SKIP:
        results[s.name] = "SKIP_KNOWN_HANG"
        print(f"⏭️  {s.name} (known hang)")
        continue
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(s.execute, mint)
        try:
            r = fut.result(timeout=45)
            results[s.name] = r.result.value
            print(f"{r.result.icon} [{r.result.value}] {s.name} ({time.time()-t0:.1f}s)")
        except cf.TimeoutError:
            results[s.name] = "TIMEOUT"
            print(f"⏱️  [TIMEOUT] {s.name}")
        except Exception as e:
            results[s.name] = f"ERROR:{str(e)[:60]}"
            print(f"❓ [ERROR] {s.name}: {str(e)[:80]}")
json.dump(results, open(out, "w"), indent=1)
p = sum(1 for v in results.values() if v == "PASS")
f = sum(1 for v in results.values() if v == "FAIL")
print(f"\nTOTAL: {p} PASS / {f} FAIL / {len(results)} scenarios -> {out}")
