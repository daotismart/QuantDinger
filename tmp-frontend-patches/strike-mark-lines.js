/**
 * Vertical marks on strike charts.
 *
 * OI / GEX strike charts use a numeric value x-axis. Price and Flip sit at the
 * exact quoted value; walls / pin snap to the nearest listed strike so they
 * stay on a bar center.
 */

export function nearestStrikeLabel (strikes, value) {
  if (value == null || !strikes.length) return null
  const num = Number(value)
  if (!Number.isFinite(num)) return null
  let best = strikes[0]
  let bestDist = Math.abs(Number(best) - num)
  strikes.forEach(s => {
    const dist = Math.abs(Number(s) - num)
    if (dist < bestDist) {
      best = s
      bestDist = dist
    }
  })
  return String(best)
}

export function minStrikeStep (strikes) {
  const nums = [...new Set((strikes || []).map(Number).filter(n => Number.isFinite(n)))].sort((a, b) => a - b)
  let min = Infinity
  for (let i = 1; i < nums.length; i++) {
    const d = nums[i] - nums[i - 1]
    if (d > 0 && d < min) min = d
  }
  if (Number.isFinite(min)) return min
  if (nums.length === 1) return Math.max(Math.abs(nums[0]) * 0.02, 0.05)
  return 0.05
}

export function formatStrikeLabel (value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return ''
  const abs = Math.abs(n)
  let s
  if (abs >= 100) s = n.toFixed(0)
  else if (abs >= 10) s = n.toFixed(1)
  else s = n.toFixed(3)
  return s.replace(/\.0+$/, '').replace(/(\.[0-9]*?)0+$/, '$1').replace(/\.$/, '')
}

export function pairStrikeData (strikes, values) {
  return (strikes || []).map((label, index) => {
    const x = Number(label)
    return [Number.isFinite(x) ? x : index, Number(values && values[index]) || 0]
  })
}

export function pairPointField (points, field, sign = 1) {
  return (points || []).map(p => {
    const x = Number(p && p.strike)
    const y = sign * (Number(p && p[field]) || 0)
    return [Number.isFinite(x) ? x : 0, y]
  })
}

export function markLineXValues (seriesOrMarks) {
  const out = []
  const push = (mark) => {
    if (!mark) return
    const n = Number(mark.xAxis)
    if (Number.isFinite(n)) out.push(n)
  }
  if (!Array.isArray(seriesOrMarks) || !seriesOrMarks.length) return out
  if (seriesOrMarks[0] && (seriesOrMarks[0].type || seriesOrMarks[0].markLine)) {
    seriesOrMarks.forEach(item => {
      const data = item && item.markLine && item.markLine.data
      if (Array.isArray(data)) data.forEach(push)
    })
    return out
  }
  seriesOrMarks.forEach(push)
  return out
}

export function strikeValueAxis (strikes, extraValues = [], extras = {}) {
  const nums = []
  ;(strikes || []).forEach(s => {
    const n = Number(s)
    if (Number.isFinite(n)) nums.push(n)
  })
  ;(extraValues || []).forEach(s => {
    const n = Number(s)
    if (Number.isFinite(n)) nums.push(n)
  })
  const step = minStrikeStep(strikes)
  const pad = step * 0.6
  const axis = {
    type: 'value',
    scale: true,
    ...extras
  }
  if (nums.length) {
    const lo = Math.min(...nums) - pad
    const hi = Math.max(...nums) + pad
    if (axis.min == null) axis.min = lo
    if (axis.max == null) axis.max = hi
  }
  if (!axis.axisLabel) axis.axisLabel = {}
  if (axis.axisLabel.formatter == null) {
    axis.axisLabel.formatter = formatStrikeLabel
  }
  return axis
}

function usesExactPrice (name) {
  return name === 'Price' || name === 'Flip'
}

function markLabel (item, fallback, formatPrice, formatStrike) {
  const raw = item.value != null ? item.value : fallback
  const formatted = usesExactPrice(item.name) ? formatPrice(raw) : formatStrike(raw)
  return formatted && formatted !== '-' ? `${item.name} ${formatted}` : item.name
}

function markEntry ({ name, xAxis, color, width, type, formatter, groupIdx }) {
  return {
    name,
    xAxis,
    lineStyle: {
      color,
      width,
      type
    },
    label: {
      show: true,
      formatter,
      color,
      position: 'end',
      distance: 8 + groupIdx * 4,
      lineHeight: 14,
      fontSize: 11,
      backgroundColor: 'rgba(0,0,0,0.45)',
      padding: [2, 4],
      borderRadius: 2
    }
  }
}

export function buildStrikeMarkLineData (markDefs, strikes, formatters = {}) {
  const formatPrice = formatters.formatPrice || (v => String(v))
  const formatStrike = formatters.formatStrike || (v => String(v))
  const groups = new Map()
  const exactPrice = []

  ;(markDefs || []).forEach((item) => {
    if (!item || item.value == null) return
    if (usesExactPrice(item.name)) {
      const x = Number(item.value)
      if (!Number.isFinite(x)) return
      exactPrice.push({ item, x })
      return
    }
    const snapped = nearestStrikeLabel(strikes, item.value)
    if (snapped == null) return
    const x = Number(snapped)
    if (!Number.isFinite(x)) return
    const key = String(x)
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push({ item, x })
  })

  const out = []
  let groupIdx = 0

  // Walls / pin first so Price and Flip paint on top when they share an x.
  groups.forEach((entries) => {
    const items = entries.map(entry => entry.item)
    const primary = items[0]
    out.push(markEntry({
      name: items.map(i => i.name).join('/'),
      xAxis: entries[0].x,
      color: primary.color,
      width: primary.width || 1.5,
      type: 'dashed',
      formatter: items.map(item => markLabel(item, entries[0].x, formatPrice, formatStrike)).join('\n'),
      groupIdx
    }))
    groupIdx += 1
  })

  exactPrice.forEach(({ item, x }) => {
    out.push(markEntry({
      name: item.name,
      xAxis: x,
      color: item.color || '#1890ff',
      width: item.width || (item.name === 'Price' ? 2 : 1.5),
      type: item.type || (item.name === 'Price' ? 'solid' : 'dashed'),
      formatter: markLabel(item, item.value, formatPrice, formatStrike),
      groupIdx
    }))
    groupIdx += 1
  })

  return out
}
