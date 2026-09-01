# Restore Strategy Management menu

Production `fe-compat` refreshes often collapse the sidebar **Strategy** group
to IDE-only and drop the inventory page. This folder restores:

- menu group **策略管理**: 策略清单 / 开发 IDE / 回测中心
- route `/strategy-manage` embedding `strategy-manage.html`
- `GET /api/strategies/inventory` list (already on the production backend)

`docker-compose.hotfix.yml` currently mounts only `index.html` + `assets/`.
The HTML page is **not** visible unless it is bind-mounted separately. The
restore script patches the mounted JS and adds that volume when missing.

```bash
python3 ops/hotfixes/strategy-manage-restore/restore_strategy_manage_menu.py
docker compose -f docker-compose.yml -f docker-compose.production.yml \
  -f docker-compose.hotfix.yml up -d frontend
```

Hard-refresh the browser after recreate. Re-run after any `fe-compat/assets`
replacement.
