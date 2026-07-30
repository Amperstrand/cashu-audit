# Bark Multi-Wallet Pattern for High-Volume Lightning Testing

## Problem

The Ark protocol limits each VTXO chain to `max_vtxo_exit_depth` (100) OOR
(out-of-round) payments. Each Lightning payment via bark extends the chain by 1.
After ~20 payments from a single chain, further payments are rejected:

```
exit depth 100 meets or exceeds the maximum of 100
```

Refreshing requires waiting for an Ark server round (~5 minutes on signet).

## Solution: Multiple Wallet Folders with Round-Robin

### Setup (on inr2.cashu.exchange, user t4)

```bash
# 1. Create 5 wallets
for i in 1 2 3 4 5; do
  sudo -u t4 bark create \
    --signet \
    --ark https://ark.signet.2nd.dev/ \
    --esplora https://mempool.space/signet/api \
    --datadir /home/t4/.bark$i
done

# 2. Fund wallet1 (100k sats via Lightning or faucet)
sudo -u t4 bark --datadir /home/t4/.bark1 ln invoice '100000 sats'
# Pay the invoice externally...

# 3. Distribute to wallets 2-5 via instant Ark-to-Ark
for i in 2 3 4 5; do
  ADDR=$(sudo -u t4 bark --datadir /home/t4/.bark$i address | grep tark)
  sudo -u t4 bark --datadir /home/t4/.bark1 send "$ADDR" '19000 sats'
done
```

### Round-Robin Payment

```python
WALLETS = ['.bark1', '.bark2', '.bark3', '.bark4', '.bark5']
payment_idx = 0

def pay_via_bark(invoice):
    global payment_idx
    wallet = WALLETS[payment_idx % len(WALLETS)]
    payment_idx += 1
    subprocess.run(
        f"ssh root@inr2.cashu.exchange "
        f"'sudo -u t4 bark --datadir /home/t4/{wallet} "
        f"ln pay invoice --wait {invoice}'",
        shell=True, timeout=45, capture_output=True
    )
```

### Background Refresh

When a wallet hits exit depth 100, refresh it while others continue:

```bash
nohup sudo -u t4 bark --datadir /home/t4/.barkN maintain --delegated &
# Takes ~5 min for Ark round to complete
# Wallet is usable again after syncing: bark --datadir ... balance
```

### Capacity

- Each wallet: ~20 OOR Lightning payments before depth 100
- 5 wallets × 20 = **100 payments without any refresh**
- With background refresh: effectively unlimited

### When NOT Needed

- **Normal smoke testing**: 3 payments per run, single wallet lasts ~33 runs
- **FakeWallet environments**: no bark needed, invoices auto-paid

### Wallet Locations

| Wallet | Datadir | Notes |
|--------|---------|-------|
| 1 | /home/t4/.bark1 | Funded from faucet, distributes to others |
| 2-5 | /home/t4/.bark{2-5} | Funded via Ark-to-Ark from wallet 1 |
| (legacy) | /home/t4/.bark | Old single-wallet setup, stale VTXOs |

### Bark Version

bark 0.3.0 (`46e41188d9d355173a6eece9190866c2b4455002`)
