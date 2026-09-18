/**
 * Call / Put GEX stacked by expiry month (strike distribution + history totals).
 *
 * Call (positive) and Put (negative) share one ECharts stack. Mixed-sign values
 * in the same stack grow away from zero in one bar slot, so columns sit
 * back-to-back instead of side-by-side. Strike charts use [strike, value]
 * pairs on a numeric x-axis so Price / Flip marks can sit between strikes.
 */

import { pairPointField, pairStrikeData } from './strike-mark-lines.js'

const CALL_PALETTE = ['#237804', '#389e0d', '#52c41a', '#73d13d', '#95de64', '#b7eb8f', '#d9f7be']
const PUT_PALETTE = ['#a8071a', '#cf1322', '#f5222d', '#ff4d4f', '#ff7875', '#ffa39e', '#ffccc7']

export const CALL_PUT_STACK = 'gex'

export function sumGexField (rows, field) {
  return (rows || []).reduce((sum, row) => sum + (Number(row && row[field]) || 0), 0)
}

export function signedCallGex (value) {
  return Math.abs(Number(value) || 0)
}

export function signedPutGex (value) {
  return -Math.abs(Number(value) || 0)
}

function barProps () {
  return {
    stackStrategy: 'samesign',
    barCategoryGap: '28%',
    barMaxWidth: 22
  }
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

export function symmetricValueRange (seriesList, paddingRatio = 0.08) {
  const positive = []
  const negative = []
  let maxAbs = 0
  ;(seriesList || []).forEach(item => {
    const values = item && item.data
    if (!Array.isArray(values)) return
    const numericY = (value) => {
      if (Array.isArray(value)) return Number(value[1]) || 0
      return Number(value) || 0
    }
    if (item.type === 'bar') {
      values.forEach((value, index) => {
        const number = numericY(value)
        if (number >= 0) positive[index] = (positive[index] || 0) + number
        else negative[index] = (negative[index] || 0) + number
      })
      return
    }
    values.forEach(value => {
      maxAbs = Math.max(maxAbs, Math.abs(numericY(value)))
    })
  })
  positive.forEach(value => {
    maxAbs = Math.max(maxAbs, Math.abs(value))
  })
  negative.forEach(value => {
    maxAbs = Math.max(maxAbs, Math.abs(value))
  })
  if (!maxAbs) maxAbs = 1
  const limit = maxAbs * (1 + paddingRatio)
  return { min: -limit, max: limit }
}

export function callPutValueAxis (valueRange, extras = {}) {
  return {
    type: 'value',
    name: 'GEX',
    min: valueRange.min,
    max: valueRange.max,
    alignTicks: true,
    ...extras
  }
}

function monthMaps (ms) {
  const byCall = new Map()
  const byPut = new Map()
  ;(ms.gex_distribution || []).forEach(p => {
    const k = strikeKey(p.strike)
    if (!k) return
    byCall.set(k, signedCallGex(p.call_gex))
    byPut.set(k, signedPutGex(p.put_gex))
  })
  return { byCall, byPut, monthLabel: String(ms.month || '').trim() }
}

export function buildCallPutStackedGexSeries (monthSeries, points, buildMarks) {
  const source = monthSources(monthSeries, points)
  const strikes = collectStrikes(source)
  const series = []
  const props = barProps()
  const mapped = source.map(monthMaps)

  mapped.forEach((item, idx) => {
    series.push({
      name: item.monthLabel ? `Call ${item.monthLabel}` : 'Call GEX',
      type: 'bar',
      stack: CALL_PUT_STACK,
      ...props,
      data: pairStrikeData(strikes, strikes.map(k => item.byCall.get(k) || 0)),
      itemStyle: { color: CALL_PALETTE[idx % CALL_PALETTE.length], opacity: 0.88 }
    })
  })
  mapped.forEach((item, idx) => {
    series.push({
      name: item.monthLabel ? `Put ${item.monthLabel}` : 'Put GEX',
      type: 'bar',
      stack: CALL_PUT_STACK,
      ...props,
      data: pairStrikeData(strikes, strikes.map(k => item.byPut.get(k) || 0)),
      itemStyle: { color: PUT_PALETTE[idx % PUT_PALETTE.length], opacity: 0.88 }
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

  return { strikes, series, valueRange: symmetricValueRange(series) }
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
  const props = barProps()
  if (months.length) {
    months.forEach((month, idx) => {
      series.push({
        name: `Call ${month}`,
        type: 'bar',
        stack: CALL_PUT_STACK,
        ...props,
        data: rows.map(slice => signedCallGex(sliceMonthTotal(slice, month, 'call_gex'))),
        itemStyle: { color: CALL_PALETTE[idx % CALL_PALETTE.length], opacity: 0.88 }
      })
    })
    months.forEach((month, idx) => {
      series.push({
        name: `Put ${month}`,
        type: 'bar',
        stack: CALL_PUT_STACK,
        ...props,
        data: rows.map(slice => signedPutGex(sliceMonthTotal(slice, month, 'put_gex'))),
        itemStyle: { color: PUT_PALETTE[idx % PUT_PALETTE.length], opacity: 0.88 }
      })
    })
  } else {
    series.push({
      name: 'Call GEX',
      type: 'bar',
      stack: CALL_PUT_STACK,
      ...props,
      data: rows.map(slice => signedCallGex(sliceSummaryTotal(slice, 'call_gex'))),
      itemStyle: { color: '#52c41a', opacity: 0.88 }
    })
    series.push({
      name: 'Put GEX',
      type: 'bar',
      stack: CALL_PUT_STACK,
      ...props,
      data: rows.map(slice => signedPutGex(sliceSummaryTotal(slice, 'put_gex'))),
      itemStyle: { color: '#ff4d4f', opacity: 0.88 }
    })
  }

  series.push({
    name: 'Net GEX',
    type: 'line',
    data: rows.map(slice => sliceSummaryTotal(slice, 'net_gex')),
    itemStyle: { color: '#fa8c16' },
    lineStyle: { width: 2 }
  })

  return { labels, series, valueRange: symmetricValueRange(series) }
}

export function buildStackedNetGexSeries (monthSeries, points, palette, buildMarks) {
  const months = (monthSeries || []).filter(ms => (ms.gex_distribution || []).length)
  if (months.length > 1) {
    const strikeNums = new Set()
    months.forEach(ms => {
      (ms.gex_distribution || []).forEach(p => {
        const k = Number(p.strike)
        if (Number.isFinite(k)) strikeNums.add(k)
      })
    })
    const strikes = Array.from(strikeNums).sort((a, b) => a - b).map(k => String(k))
    const series = months.map((ms, idx) => {
      const byK = new Map(
        (ms.gex_distribution || []).map(p => [String(Number(p.strike)), Number(p.net_gex) || 0])
      )
      return {
        name: String(ms.month || `M${idx + 1}`),
        type: 'bar',
        stack: 'gex',
        barMaxWidth: 18,
        data: pairStrikeData(strikes, strikes.map(k => byK.get(k) || 0)),
        itemStyle: { color: palette[idx % palette.length], opacity: 0.78 }
      }
    })
    const aggByK = new Map(
      (points || []).map(p => [String(Number(p.strike)), Number(p.net_gex) || 0])
    )
    const netValues = strikes.map((k, i) => {
      if (aggByK.has(k)) return aggByK.get(k)
      return series.reduce((sum, ser) => sum + (Number(ser.data[i] && ser.data[i][1]) || 0), 0)
    })
    series.push({
      name: 'Net GEX',
      type: 'line',
      data: pairStrikeData(strikes, netValues),
      itemStyle: { color: '#fa8c16' },
      markLine: { symbol: 'none', data: buildMarks(strikes) }
    })
    return { strikes, series }
  }
  const strikes = (points || []).map(p => String(p.strike))
  return {
    strikes,
    series: [
      { name: 'Call GEX', type: 'bar', stack: 'gex', barMaxWidth: 18, data: pairPointField(points, 'call_gex'), itemStyle: { color: '#52c41a', opacity: 0.55 } },
      { name: 'Put GEX', type: 'bar', stack: 'gex', barMaxWidth: 18, data: pairPointField(points, 'put_gex'), itemStyle: { color: '#ff4d4f', opacity: 0.55 } },
      { name: 'Net GEX', type: 'line', data: pairPointField(points, 'net_gex'), itemStyle: { color: '#fa8c16' }, markLine: { symbol: 'none', data: buildMarks(strikes) } }
    ]
  }
}

export function buildOiStrikeSeries (points, strikeMarks) {
  return [
    { name: 'Call OI', type: 'bar', stack: 'oi', barMaxWidth: 18, data: pairPointField(points, 'call_oi'), itemStyle: { color: '#52c41a', opacity: 0.7 } },
    { name: 'Put OI', type: 'bar', stack: 'oi', barMaxWidth: 18, data: pairPointField(points, 'put_oi', -1), itemStyle: { color: '#ff4d4f', opacity: 0.7 } },
    {
      name: 'Net OI',
      type: 'line',
      data: pairPointField(points, 'net_oi'),
      itemStyle: { color: '#2f54eb' },
      markLine: strikeMarks && strikeMarks.length ? { symbol: 'none', data: strikeMarks } : undefined
    }
  ]
}
