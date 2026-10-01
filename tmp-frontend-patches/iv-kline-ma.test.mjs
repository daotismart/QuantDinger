import { simpleMovingAverage, ivKlineMaSeries, formatIvKlineTooltip } from './iv-kline-ma.js'

function assert (cond, msg) {
  if (!cond) throw new Error(msg)
}

const closes = [1, 2, 3, 4, 5, 6]
const ma3 = simpleMovingAverage(closes, 3)
assert(ma3[0] == null && ma3[1] == null, 'SMA needs a full window')
assert(ma3[2] === 2, `ma3[2]=${ma3[2]}`)
assert(ma3[5] === 5, `ma3[5]=${ma3[5]}`)

const gapped = simpleMovingAverage([1, null, 3, 4, 5], 3)
assert(gapped[2] == null, 'gap inside the window should skip')
assert(gapped[4] === 4, `gapped[4]=${gapped[4]}`)

const series = ivKlineMaSeries(closes, [5])
assert(series[0].name === 'MA5' && series[0].type === 'line', 'MA series name/type')
assert(series[0].data[3] == null && series[0].data[4] === 3, `MA5 data ${JSON.stringify(series[0].data)}`)

const tip = formatIvKlineTooltip([
  { axisValue: '2026-09-01', seriesType: 'candlestick', data: [0.2, 0.22, 0.18, 0.24] },
  { seriesName: 'MA5', seriesType: 'line', data: 0.21 }
])
assert(tip.includes('2026-09-01') && tip.includes('MA5 21.00%') && tip.includes('O 20.00%'), tip)

console.log('iv-kline-ma.test.mjs ok')
