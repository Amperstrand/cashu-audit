# E2E Behavioral Testing — Layer 4

> **Purpose**: Runtime testing of Cashu mint implementations against spec-defined behavior.
> Complements Layer 1-3 (static analysis) by catching bugs that only manifest at runtime.

## What this catches that static audit can't

| Bug class | Example | How |
|---|---|---|
| Race conditions | Double proof invalidation (#683) | Concurrent HTTP requests |
| State machine bugs | SIG_ALL pathway rejection after locktime (#1009) | Constructed proofs per state |
| Error response format | HTTP 500 instead of protocol error | Submit invalid inputs |
| Interop divergence | Same proof accepted at mint A, rejected at B | Run same scenario across mints |

## Architecture

```
e2e/
├── scenarios/           # Human-readable test definitions
│   ├── nutshell-683-race-condition.md
│   ├── sigall-state-transitions.md
│   └── ...
├── lib/
│   ├── mint_client.py   # Cashu HTTP client
│   ├── proof_builder.py # Construct P2PK/HTLC/SIG_ALL proofs
│   └── concurrency.py   # Concurrent request helpers
└── README.md            # This file
```

## Test targets

| Implementation | URL | Backend |
|---|---|---|
| cashu-cf (local) | http://localhost:8787 | FakeWallet |
| cashu-cf (testnut) | https://testnut.cashu.exchange | FakeWallet |
| cashu-cf (signut) | https://signut.cashu.exchange | Blink |
| CDK experiment | Embedded or local cdk-mintd | FakeWallet |

## Running tests

```bash
# Start cashu-cf locally
cd ~/src/cashu-cf && npm run dev

# Run a scenario
python3 e2e/lib/mint_client.py --mint-url http://localhost:8787 --scenario race-condition

# Run the NUT-10 compatibility checker (58 scenarios)
~/src/nut10_compatibility_checker/compat-runner/target/release/compat-runner \
  --mint-url http://localhost:8787 --suite all
```

## Relationship to PRTA

This framework adapts concepts from [physical-router-test-automation](https://github.com/Amperstrand/physical-router-test-automation):
- QEMU VM management for isolated test environments
- Concurrent test execution for race conditions
- Result reporting with evidence

PRTA tests TollGate router behavior. This framework tests Cashu mint behavior. Same patterns, different protocol.
