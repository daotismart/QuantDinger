# K-line candle color switch (red-up / green-up)

QuantDinger's chart UI lives in [QuantDinger-Vue](https://github.com/OpenByteInc/QuantDinger-Vue).
This folder is the matching frontend patch for `GET/PUT /api/users/chart-preferences`.

## What users see

On the indicator chart drawing toolbar (left of the candles), a two-tone swatch
toggles:

- **red_up** — A-share convention, red up / green down
- **green_up** — Western convention, green up / red down (previous default)

Chinese browsers default to `red_up` on first visit; others default to `green_up`.
The choice is stored in `localStorage` (`qd_candle_color_scheme`) and synced to
the logged-in user's `qd_users.chart_preferences`.

## Apply to QuantDinger-Vue

```bash
cd QuantDinger-Vue
git apply ../QuantDinger/ops/quantdinger-vue-kline-color/kline-color.patch
cp ../QuantDinger/ops/quantdinger-vue-kline-color/src/utils/candleColorScheme.js \
   src/utils/candleColorScheme.js
```

Then rebuild the frontend image (`docker compose -f docker-compose.yml -f docker-compose.build.yml up --build frontend`).
