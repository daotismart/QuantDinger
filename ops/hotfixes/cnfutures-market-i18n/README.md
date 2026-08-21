# CNFutures market label i18n hotfix

## Symptom

On the Indicator IDE "add watchlist" dialog, market tabs sometimes show the raw
key `dashboard.indicator.market.CNFutures` and sometimes the Chinese label
`国内期货`.

## Root cause

CN futures / options markets (`CNFutures`, `CNFuturesOptions`,
`CNIndexFutures`, `CNIndexOptions`) were enabled in the backend, but the Vue
locale packs still only defined the older markets. The dialog used:

```js
$t('dashboard.indicator.market.' + m)
```

When the key is missing, vue-i18n returns the full key path. A production-only
`ops/hotfixes/zh-CN.js` locale chunk that *did* contain `国内期货` existed on
the host but was not always mounted over the runtime `assets/zh-CN-*.js`
hashes, so labels looked intermittent depending on cache / which chunk loaded.

## Immediate production mitigation

Bind-mount the patched zh-CN locale chunk over both runtime hashes via
`docker-compose.hotfix.yml` on the host:

- `./ops/hotfixes/fe-compat/assets/zh-CN-Ce6XGYyl.js`
- `./ops/hotfixes/fe-compat/assets/zh-CN-DbXCGMSb.js`

(content sourced from `ops/hotfixes/zh-CN.js` on the host)

## Durable fix

Apply `0001-fix-cnfutures-market-i18n.patch` in the private `QuantDinger-Vue`
repo (branch suggestion: `cursor/fix-cnfutures-market-i18n-c137`), rebuild
`quantdinger-frontend`, then remove the zh-CN asset bind-mounts.

The patch:

- Adds locale keys for the four CN markets under
  `dashboard.indicator.market.*`, `dashboard.analysis.market.*`, and
  `settings.market.desc.*`
- Adds `resolveMarketLabel()` with static zh/en fallbacks so missing keys
  never leak raw i18n paths
- Switches Indicator IDE / AI Analysis / Settings / Strategy IDE market
  labels to that helper
