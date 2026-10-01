/** SMA overlays for the near-month IV smile history candlestick. */

export const IV_KLINE_MA_PERIODS = [5, 10, 20]

export const IV_KLINE_MA_COLORS = {
  5: '#f59e0b',
  10: '#3b82f6',
  20: '#a855f7'
}

export function simpleMovingAverage (values, period) {
  const n = Math.max(1, Number(period) || 0)
  const out = new Array(values.length).fill(null)
  if (n < 1) return out
  for (let i = 0; i < values.length; i++) {
    if (i + 1 < n) continue
    let sum = 0
    let ok = true
    for (let j = i - n + 1; j <= i; j++) {
      const raw = values[j]
      if (raw == null || raw === '') {
        ok = false
        break
      }
      const x = Number(raw)
      if (!Number.isFinite(x)) {
        ok = false
        break
      }
      sum += x
    }
    if (ok) out[i] = sum / n
  }
  return out
}

export function ivKlineMaSeries (closes, periods = IV_KLINE_MA_PERIODS) {
  return (periods || []).map(period => ({
    name: `MA${period}`,
    type: 'line',
    showSymbol: false,
    data: simpleMovingAverage(closes, period),
    itemStyle: { color: IV_KLINE_MA_COLORS[period] || '#8c8c8c' },
    lineStyle: { width: 1.5 },
    z: 3
  }))
}

export function formatIvKlineTooltip (params) {
  const list = Array.isArray(params) ? params : [params]
  if (!list.length) return ''
  const pct = v => (v == null || !Number.isFinite(Number(v)) ? '--' : `${(Number(v) * 100).toFixed(2)}%`)
  const lines = [String(list[0].axisValue || '')]
  list.forEach(item => {
    if (!item) return
    if (item.seriesType === 'candlestick') {
      const data = item.data
      if (!data || data[0] == null) {
        lines.push('--')
        return
      }
      const [o, c, l, h] = data
      lines.push(`O ${pct(o)} / C ${pct(c)}`)
      lines.push(`L ${pct(l)} / H ${pct(h)}`)
      return
    }
    lines.push(`${item.seriesName} ${pct(item.data)}`)
  })
  return lines.join('<br/>')
}
