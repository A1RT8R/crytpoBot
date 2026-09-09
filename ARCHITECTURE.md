# Architecture v2

```text
Telegram Bot API
      │
      ├── Rich UI / admin / subscriptions / alerts
      │
      ▼
   BotApp ─────────────── PostgreSQL
      │                    users / plans / subscriptions
      │                    payments / alerts / history
      │
      ├─────────────── Redis
      │                transient input states
      │
      ▼
MarketEngine
      │
      ├── continuous bulk ticker refresh
      ├── fresh hot orderbooks
      ├── TTL + timestamp skew validation
      ├── VWAP / slippage / objective sorting
      ├── circuit breaker + per-exchange concurrency
      └── 30s interactive deadline
      │
      ▼
AssetRegistry
      ├── KuCoin public chains
      ├── HTX public chains
      └── Bitget public chains

Read-only API vault
      └── encrypted credentials, private enrichment adapter next

External Billing Adapter
      └── signed checkout params + HMAC webhook
```

## Design rules

1. No per-user full market scanner.
2. No stale opportunity returned as current.
3. Same ticker is not enough when network/contract data proves a mismatch.
4. Unknown withdrawal fee is never silently treated as confirmed clean profit.
5. A slow/broken exchange cannot block the bot forever.
6. Plans/features live in the database and are changed through the admin UI.
7. Secrets never belong in source archives.
