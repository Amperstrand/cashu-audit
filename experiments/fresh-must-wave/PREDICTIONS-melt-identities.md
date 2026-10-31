# FROZEN PREDICTIONS — melt-path error identities, pre-deploy baseline (2026-10-31)

Purpose: capture cf (deployed, OLD saga codes) melt identities now so the
post-deploy diff against fix/saga-error-codes is mechanical; compare
against ns/cdk arms for the family row.

| Leg | testnut (cf, deployed) | ns-0.21.0 | cdk-0.18.3 |
|---|---|---|---|
| M4 melt with unknown-quote id | 400 quote_not_found (saga 10002-class) | 400 detail | 400 50000 |
| M5 melt, inputs from UNKNOWN keyset | 400/403 unknown_keyset saga '10009'-class | 400 class | 400 12001? |
| M6 melt underfunded (insufficient inputs) | saga '10007'-class | 400 | 400 11001-class? |
| M7 melt witness-less P2PK proof | 403 30006 (pre-split) | ? | ? (30006-class or own) |

Any cell surprising = probe bug first. Melt requests need PAID melt
quotes: oracle invoice arm (ns fakewallet) provides them; local arms'
own fakewallets settle melts instantly.
