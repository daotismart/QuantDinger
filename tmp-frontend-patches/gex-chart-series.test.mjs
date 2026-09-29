import { buildCallPutStackedGexSeries, buildStackedNetGexSeries } from './gex-chart-series.js'

function assert (cond, msg) {
  if (!cond) throw new Error(msg)
}

const points = [
  { strike: 1.5, call_gex: 10, put_gex: -40, net_gex: -30 },
  { strike: 1.6, call_gex: 50, put_gex: -10, net_gex: 40 }
]
const oneMonth = [{ month: '202609', gex_distribution: points }]
const palette = ['#1677ff', '#52c41a']
const marks = () => [{ xAxis: 1.55, name: 'Price' }]

const gex = buildCallPutStackedGexSeries(oneMonth, points, marks)
const net = buildStackedNetGexSeries(oneMonth, points, palette, marks)

assert(gex.series.some(s => s.name.includes('Call')), 'GEX dist should keep Call series')
assert(gex.series.some(s => s.name.includes('Put')), 'GEX dist should keep Put series')
assert(gex.xAxis && gex.xAxis.type === 'value', 'Call/Put GEX x-axis must be numeric, not category')
assert(!Array.isArray(gex.xAxis.data), 'numeric x-axis must not carry category labels')
const callBar = gex.series.find(s => s.name.includes('Call'))
assert(Array.isArray(callBar.data[0]) && callBar.data[0][0] === 1.5, `call bars must be [strike, value], got ${JSON.stringify(callBar.data)}`)
assert(callBar.data[1][0] === 1.6, 'second call bar sits at strike 1.6')
const gexMarks = (gex.series.find(s => s.markLine) || {}).markLine || {}
assert(gexMarks.data && gexMarks.data[0].xAxis === 1.55, `Price mark must keep quoted x, got ${JSON.stringify(gexMarks.data)}`)

const wide = []
for (let k = 130; k <= 255; k += 5) wide.push({ strike: k / 100, call_gex: k === 140 ? 100 : 1, put_gex: k === 140 ? -80 : -1, net_gex: 0 })
const flipMarks = () => [{ xAxis: 1.503, name: 'Flip' }]
const piled = buildCallPutStackedGexSeries([{ month: '202610', gex_distribution: wide }], wide, flipMarks)
const piledCall = piled.series.find(s => s.name.includes('Call'))
const xs = piledCall.data.map(d => d[0])
assert(xs[0] === 1.3 && xs[xs.length - 1] === 2.55, `strikes must span listed K, got ${xs[0]}..${xs[xs.length - 1]}`)
assert(piled.xAxis.min < 1.3 && piled.xAxis.max > 2.55, 'value axis range must cover listed strikes')
const flip = (((piled.series.find(s => s.markLine) || {}).markLine || {}).data || []).find(m => m.name === 'Flip')
assert(flip && Math.abs(flip.xAxis - 1.503) < 1e-9, `Flip must sit at 1.503, not a category index, got ${flip && flip.xAxis}`)

const netNames = net.series.map(s => s.name)
assert(!netNames.some(n => /Call|Put/.test(n)), `Net GEX must not reuse Call/Put bars, got ${netNames}`)
assert(netNames.includes('Net GEX'), 'single-month Net GEX should be named Net GEX')
assert(net.series.filter(s => s.type === 'bar').length === 1, 'single-month Net GEX should be one bar series')

const bar = net.series.find(s => s.type === 'bar')
assert(JSON.stringify(bar.data) === JSON.stringify([[1.5, -30], [1.6, 40]]), `net bars ${JSON.stringify(bar.data)}`)

const twoMonths = [
  { month: '202609', gex_distribution: [{ strike: 1.5, net_gex: -10 }] },
  { month: '202610', gex_distribution: [{ strike: 1.5, net_gex: 25 }] }
]
const stacked = buildStackedNetGexSeries(twoMonths, [{ strike: 1.5, net_gex: 15 }], palette, marks)
assert(stacked.series.filter(s => s.type === 'bar').length === 2, 'all-months Net GEX stacks per month')
assert(stacked.series.some(s => s.type === 'line' && s.name === 'Net GEX'), 'all-months keep Net GEX line')

console.log('gex-chart-series.test.mjs ok')
