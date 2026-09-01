/**
 * Call / Put GEX stacked by expiry month (strike distribution + history totals).
 */

const CALL_PALETTE = ['#237804', '#389e0d', '#52c41a', '#73d13d', '#95de64', '#b7eb8f', '#d9f7be']
const PUT_PALETTE = ['#a8071a', '#cf1322', '#f5222d', '#ff4d4f', '#ff7875', '#ffa39e', '#ffccc7']

export function sumGexField (rows, field) {
  return (rows || []).reduce((sum, row) => sum + (Number(row && row[field]) || 0), 0)
}

function monthSources (monthSeries, points) {
  const months = (monthSeries || []).filter(ms => (ms.gex_distribution || []).length)
  if (months.length) return months
  return [{ month: '', gex_distribution: points || [] }]
}

function collectStrikes (source) {
  const strikeNums = new Set()
  source.forEach(ms => {
    (ms.gex_distribution || []).forEach(p => {
      const k = Number(p.strike)
      if (Number.isFinite(k)) strikeNums.add(k)
    })
  })
  return Array.from(strikeNums).sort((a, b) => a - b).map(k => String(k))
}

function strikeKey (value) {
  const n = Number(value)
  return Number.isFinite(n) ? String(n) : ''
}

export function buildCallPutStackedGexSeries (monthSeries, points, buildMarks) {
  const source = monthSources(monthSeries, points)
  const strikes = collectStrikes(source)
  const series = []

  source.forEach((ms, idx) => {
    const byCall = new Map()
    const byPut = new Map()
    ;(ms.gex_distribution || []).forEach(p => {
      const k = strikeKey(p.strike)
      if (!k) return
      byCall.set(k, Number(p.call_gex) || 0)
      byPut.set(k, Number(p.put_gex) || 0)
    })
    const monthLabel = String(ms.month || '').trim()
    series.push({
      name: monthLabel ? `Call ${monthLabel}` : 'Call GEX',
      type: 'bar',
      stack: 'call',
      barMaxWidth: 18,
      data: strikes.map(k => byCall.get(k) || 0),
      itemStyle: { color: CALL_PALETTE[idx % CALL_PALETTE.length], opacity: 0.82 }
    })
    series.push({
      name: monthLabel ? `Put ${monthLabel}` : 'Put GEX',
      type: 'bar',
      stack: 'put',
      barMaxWidth: 18,
      data: strikes.map(k => byPut.get(k) || 0),
      itemStyle: { color: PUT_PALETTE[idx % PUT_PALETTE.length], opacity: 0.82 }
    })
  })

  const marks = typeof buildMarks === 'function' ? (buildMarks(strikes) || []) : []
  if (marks.length) {
    series.push({
      type: 'line',
      data: [],
      silent: true,
      tooltip: { show: false },
      itemStyle: { opacity: 0 },
      lineStyle: { opacity: 0 },
      markLine: { symbol: 'none', data: marks }
    })
  }

  return { strikes, series }
}

function sliceMonthTotal (slice, month, field) {
  const ms = (slice.month_series || []).find(item => String(item.month) === String(month))
  if (ms) return sumGexField(ms.gex_distribution, field)
  return 0
}

function sliceSummaryTotal (slice, field) {
  const summary = slice.gex_summary || {}
  if (summary[field] != null && Number.isFinite(Number(summary[field]))) {
    return Number(summary[field]) || 0
  }
  return sumGexField(slice.gex_distribution, field)
}

export function buildCallPutGexTrendSeries (slices) {
  const rows = slices || []
  const labels = rows.map(s => s.label || s.ts || s.date || '')
  const months = []
  rows.forEach(slice => {
    (slice.month_series || []).forEach(ms => {
      const month = String(ms.month || '').trim()
      if (month && !months.includes(month)) months.push(month)
    })
  })

  const series = []
  if (months.length) {
    months.forEach((month, idx) => {
      series.push({
        name: `Call ${month}`,
        type: 'bar',
        stack: 'call',
        data: rows.map(slice => sliceMonthTotal(slice, month, 'call_gex')),
        itemStyle: { color: CALL_PALETTE[idx % CALL_PALETTE.length], opacity: 0.82 }
      })
      series.push({
        name: `Put ${month}`,
        type: 'bar',
        stack: 'put',
        data: rows.map(slice => sliceMonthTotal(slice, month, 'put_gex')),
        itemStyle: { color: PUT_PALETTE[idx % PUT_PALETTE.length], opacity: 0.82 }
      })
    })
  } else {
    series.push({
      name: 'Call GEX',
      type: 'bar',
      stack: 'call',
      data: rows.map(slice => sliceSummaryTotal(slice, 'call_gex')),
      itemStyle: { color: '#52c41a', opacity: 0.82 }
    })
    series.push({
      name: 'Put GEX',
      type: 'bar',
      stack: 'put',
      data: rows.map(slice => sliceSummaryTotal(slice, 'put_gex')),
      itemStyle: { color: '#ff4d4f', opacity: 0.82 }
    })
  }

  series.push({
    name: 'Net GEX',
    type: 'line',
    data: rows.map(slice => sliceSummaryTotal(slice, 'net_gex')),
    itemStyle: { color: '#fa8c16' },
    lineStyle: { width: 2 }
  })

  return { labels, series }
}
