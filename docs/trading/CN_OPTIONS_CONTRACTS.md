# China listed option contracts

QuantDinger catalogs **every listed CTP option** for search and on-demand
history. It does **not** subscribe the CTP market-data feed to the full chain
(exchange limits are typically on the order of 500 instruments) and does **not**
bulk-ingest per-contract history into `qd_market_bars`.

## Markets

| Market | Contents |
| --- | --- |
| `CNFuturesOptions` | Commodity futures options (SHFE / DCE / CZCE / INE / GFEX) plus static product roots |
| `CNIndexOptions` | CFFEX IO/HO/MO listed contracts, plus SSE/SZSE ETF options (8-digit codes) for search |

ETF options are search-only. CTP commodity/index option order ids are formatted
per exchange:

| Exchange | Example InstrumentID |
| --- | --- |
| DCE / GFEX | `m2609-C-2800` / `lc2610-C-100000` |
| SHFE / INE | `cu2609C100000` / `sc2610C350` |
| CFFEX | `HO2608-C-2500` |
| CZCE | `AP610C10000` |

Search symbols are stored hyphenated and uppercase (`M2609-C-2800`);
`format_instrument_id` converts them to the native CTP id at order time.

## Sync

```bash
cd backend_api_python
PYTHONPATH=. python scripts/sync_cn_option_contracts.py
# or
PYTHONPATH=. python scripts/sync_market_symbols.py --markets CNFutures CNFuturesOptions CNIndexFutures CNIndexOptions
```

`CN_OPTIONS_INCLUDE_ETF=false` skips SSE/SZSE numeric codes.
`CN_OPTIONS_CTP_SYNC=false` keeps static product roots only.

Source: AkShare `option_contract_info_ctp()` (listed rows, `合约状态=1`).
Delisted contracts with a non-empty `instrument_id` are deactivated on the next
successful listed-chain upsert; static roots (`instrument_id=''`) stay active.

## History

Daily/weekly: try `option_commodity_hist_sina`, then the underlying continuous
(`M0`, and `IF0`/`IH0`/`IM0` for IO/HO/MO). Minute bars always use the
underlying continuous series.

## Tests

```bash
cd backend_api_python
python -m pytest tests/test_cn_options_contracts.py tests/test_cffex_ctp_qmt_integration.py tests/test_cn_futures_history.py -q
```
