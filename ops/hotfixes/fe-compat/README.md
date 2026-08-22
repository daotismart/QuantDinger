# Frontend login redirect compat

Production hotfix for hashed-asset rollback that left browsers requesting
`QuickTradePanel-B0Dq_CAe.js` (404), which blocked navigation after login.

## Contents

- `index.html` — same build entry as the `datasvc` image, with `Cache-Control: no-store` meta
- `assets/QuickTradePanel-B0Dq_CAe.js` — alias of current `QuickTradePanel-B0Dq_CAeR2.js`
  (imports `index-CVDEz7sD`, not the removed `index-CNkhJNEQ`)

## Mounts (docker-compose.hotfix.yml)

```yaml
volumes:
  - ./ops/hotfixes/nginx-docker.conf.template:/etc/nginx/templates/default.conf.template:ro
  - ./ops/hotfixes/fe-compat/index.html:/usr/share/nginx/html/index.html:ro
  - ./ops/hotfixes/fe-compat/assets/QuickTradePanel-B0Dq_CAe.js:/usr/share/nginx/html/assets/QuickTradePanel-B0Dq_CAe.js:ro
```

Do **not** add `?v=` query busting on the entry `type="module"` script — that
loads the app module twice and throws `Cannot redefine property: $dialog`.

Prefer a fresh frontend image with new content hashes when convenient.
