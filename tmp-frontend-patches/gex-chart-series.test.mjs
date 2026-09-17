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
