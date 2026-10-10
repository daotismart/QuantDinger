/**
 * ETF daily close → latest MA / Bollinger levels, plus strike-axis SMA overlays.
 *
 * Strike charts use a numeric x-axis (price). BOLL / MA of the underlying are
 * drawn as vertical markLines at those prices. Distribution MA5 is a line
 * across neighboring strikes.
 */

import { simpleMovingAverage } from './iv-kline-ma.js'

export const DIST_MA_PERIOD = 5
export const BOLL_PERIOD = 20
export const BOLL_K = 2

export const PRICE_BAND_STYLES = [
  { key: 'ma5', name: 'MA5', color: '#f59e0b', width: 1.2, type: 'dotted' },
  { key: 'ma10', name: 'MA10', color: '#3b82f6', width: 1.2, type: 'dotted' },
  { key: 'mid', name: 'BOLL Mid', color: '#a855f7', width: 1.4, type: 'dashed' },
  { key: 'upper', name: 'BOLL Up', color: '#14b8a6', width: 1.2, type: 'dashed' },
  { key: 'lower', name: 'BOLL Low', color: '#14b8a6', width: 1.2, type: 'dashed' }
]

function lastFinite (values) {
  for (let i = values.length - 1; i >= 0; i--) {
    const n = Number(values[i])
    if (Number.isFinite(n)) return n
  }
  return null
}

function windowStd (values, period) {
  const n = Math.max(1, Number(period) || 0)
  if (values.length < n) return null
  const slice = values.slice(values.length - n)
  if (slice.some(v => !Number.isFinite(Number(v)))) return null
  const mean = slice.reduce((sum, v) => sum + Number(v), 0) / n
  const varSum = slice.reduce((sum, v) => {
    const d = Number(v) - mean
    return sum + d * d
  }, 0)
  return Math.sqrt(varSum / n)
}

function pointDate (row) {
  return String((row && (row.date || row.ts || row.label)) || '').slice(0, 10)
}

function pointPrice (row) {
  if (!row || typeof row !== 'object') return null
  const raw = row.price != null ? row.price : row.close
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
}

export function closesThrough (points, asOf) {
  const rows = (points || [])
    .map(row => ({ date: pointDate(row), price: pointPrice(row) }))
    .filter(row => row.date && row.price != null)
    .sort((a, b) => a.date.localeCompare(b.date))
  const cutoff = asOf ? String(asOf).slice(0, 10) : ''
  const kept = cutoff ? rows.filter(row => row.date <= cutoff) : rows
  return kept.map(row => row.price)
}

export function latestPriceBands (points, options = {}) {
  const period = Number(options.period) > 0 ? Number(options.period) : BOLL_PERIOD
  const k = Number(options.k) > 0 ? Number(options.k) : BOLL_K
  const closes = closesThrough(points, options.asOf)
  const ma5 = lastFinite(simpleMovingAverage(closes, 5))
  const ma10 = lastFinite(simpleMovingAverage(closes, 10))
  const mid = lastFinite(simpleMovingAverage(closes, period))
  const std = windowStd(closes, period)
  const upper = mid != null && std != null ? mid + k * std : null
  const lower = mid != null && std != null ? mid - k * std : null
  return { ma5, ma10, mid, upper, lower, n: closes.length }
}

export function priceBandMarkDefs (bands) {
  return PRICE_BAND_STYLES
    .map(item => ({
      name: item.name,
      value: bands ? bands[item.key] : null,
      color: item.color,
      width: item.width,
      type: item.type
    }))
    .filter(item => item.value != null && Number.isFinite(Number(item.value)))
}

export function priceBandValueAxisMarks (bands, formatPrice) {
  const fmt = typeof formatPrice === 'function' ? formatPrice : (v => String(v))
  return priceBandMarkDefs(bands).map(item => ({
    name: item.name,
    xAxis: Number(item.value),
    lineStyle: {
      color: item.color,
      width: item.width,
      type: item.type || 'dashed'
    },
    label: {
      show: true,
      formatter: `${item.name} ${fmt(item.value)}`,
      color: item.color,
      position: 'insideEndTop',
      lineHeight: 14,
      fontSize: 11,
      backgroundColor: 'rgba(0,0,0,0.45)',
      padding: [2, 4],
      borderRadius: 2
    }
  }))
}

export function pairedYValues (paired) {
  return (paired || []).map(item => {
    if (Array.isArray(item)) return Number(item[1])
    return Number(item)
  }).map(n => (Number.isFinite(n) ? n : null))
}

export function strikeMovingAverageSeries (paired, period = DIST_MA_PERIOD, name = 'MA5', color = '#f59e0b') {
  const rows = paired || []
  const ma = simpleMovingAverage(pairedYValues(rows), period)
  return {
    name,
    type: 'line',
    showSymbol: false,
    z: 4,
    data: rows.map((item, index) => {
      const x = Array.isArray(item) ? item[0] : index
      return [x, ma[index]]
    }),
    itemStyle: { color },
    lineStyle: { width: 1.6, color }
  }
}

export function overlayTvYieldMovingAverages (series, period = DIST_MA_PERIOD) {
  const extra = []
  ;(series || []).forEach(item => {
    if (!item || item.type === 'bar' || !Array.isArray(item.data) || item.data.length < period) return
    if (item.markLine && !(item.data || []).length) return
    const isPut = String(item.name || '').toLowerCase().includes('put')
    extra.push(strikeMovingAverageSeries(
      item.data,
      period,
      `${item.name || 'MA'} MA${period}`.trim(),
      isPut ? '#fb7185' : '#f59e0b'
    ))
  })
  return extra
}
