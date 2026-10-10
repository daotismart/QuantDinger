import {
  latestPriceBands,
  priceBandMarkDefs,
  priceBandValueAxisMarks,
  strikeMovingAverageSeries,
  overlayTvYieldMovingAverages
} from './price-bands.js'
import { buildStrikeMarkLineData } from './strike-mark-lines.js'

function assert (cond, msg) {
  if (!cond) throw new Error(msg)
}

const closes = []
for (let i = 0; i < 20; i++) closes.push({ date: `2026-09-${String(i + 1).padStart(2, '0')}`, price: 10 + i * 0.1 })
const bands = latestPriceBands(closes)
assert(Math.abs(bands.ma5 - 11.7) < 1e-9, `ma5=${bands.ma5}`)
assert(Math.abs(bands.mid - 10.95) < 1e-9, `mid=${bands.mid}`)
assert(bands.upper > bands.mid && bands.lower < bands.mid, 'BOLL envelope around mid')

const asOf = latestPriceBands(closes.concat([{ date: '2026-10-01', price: 20 }]), { asOf: '2026-09-20' })
assert(Math.abs(asOf.mid - bands.mid) < 1e-9, 'asOf ignores later closes')

const defs = priceBandMarkDefs(bands)
assert(defs.some(d => d.name === 'MA5' && d.value === bands.ma5), 'MA5 mark def')
assert(defs.some(d => d.name === 'BOLL Up' && d.value === bands.upper), 'BOLL Up mark def')

const axisMarks = priceBandValueAxisMarks(bands, v => Number(v).toFixed(3))
assert(axisMarks.every(m => Number.isFinite(m.xAxis)), 'value-axis marks keep numeric x')

const strikes = ['1.4', '1.5', '1.6', '1.7']
const drawn = buildStrikeMarkLineData(
  [{ name: 'Price', value: 1.541, color: '#1890ff' }, ...defs],
  strikes
)
const boll = drawn.find(m => String(m.name).includes('BOLL Mid'))
assert(boll && Math.abs(boll.xAxis - bands.mid) < 1e-9, `BOLL Mid must sit at exact price, got ${boll && boll.xAxis}`)
const ma5 = drawn.find(m => m.name === 'MA5')
assert(ma5 && Math.abs(ma5.xAxis - bands.ma5) < 1e-9, `MA5 must sit at exact price, got ${ma5 && ma5.xAxis}`)

const ma = strikeMovingAverageSeries([[1, 1], [2, 2], [3, 3], [4, 4], [5, 5]], 3, 'Net MA3')
assert(ma.data[1][1] == null && ma.data[2][1] === 2, `strike MA ${JSON.stringify(ma.data)}`)

const tvExtra = overlayTvYieldMovingAverages([
  { name: 'Call 202610', type: 'line', data: [[1.4, 0.1], [1.5, 0.2], [1.6, 0.3], [1.7, 0.4], [1.8, 0.5]] }
])
assert(tvExtra[0] && tvExtra[0].name.includes('MA5'), 'TV overlay keeps series name + MA5')

console.log('price-bands.test.mjs ok')
