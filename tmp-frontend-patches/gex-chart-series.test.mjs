import test from 'node:test'
import assert from 'node:assert/strict'

import {
  CALL_PUT_STACK,
  buildCallPutGexTrendSeries,
  buildCallPutStackedGexSeries,
  buildStackedNetGexSeries,
  signedPutGex,
  sumGexField
} from '../../src/views/market-composite-analysis/gex-chart-series.js'

test('stacks call and put GEX back-to-back in one bar slot', () => {
  const stacked = buildCallPutStackedGexSeries(
    [
      {
        month: '2026-05',
        gex_distribution: [
          { strike: 2.8, call_gex: 10, put_gex: -4, net_gex: 6 },
          { strike: 3.0, call_gex: 8, put_gex: -6, net_gex: 2 }
        ]
      },
      {
        month: '2026-06',
        gex_distribution: [
          { strike: 2.8, call_gex: 3, put_gex: -1, net_gex: 2 },
          { strike: 3.1, call_gex: 5, put_gex: -2, net_gex: 3 }
        ]
      }
    ],
    [],
    () => []
  )

  assert.deepEqual(stacked.strikes, ['2.8', '3', '3.1'])
  const callMay = stacked.series.find(s => s.name === 'Call 2026-05')
  const putJun = stacked.series.find(s => s.name === 'Put 2026-06')
  assert.equal(callMay.stack, CALL_PUT_STACK)
  assert.equal(putJun.stack, CALL_PUT_STACK)
  assert.equal(callMay.stackStrategy, 'samesign')
  assert.equal(putJun.stackStrategy, 'samesign')
  assert.deepEqual(callMay.data, [[2.8, 10], [3, 8], [3.1, 0]])
  assert.deepEqual(putJun.data, [[2.8, -1], [3, 0], [3.1, -2]])
  assert.equal(stacked.valueRange.max, -stacked.valueRange.min)
  assert.ok(stacked.valueRange.max >= 13)
})

test('history trend stacks monthly call/put totals over slices', () => {
  const trend = buildCallPutGexTrendSeries([
    {
      label: 't1',
      month_series: [
        { month: '2026-05', gex_distribution: [{ call_gex: 10, put_gex: -4 }] }
      ],
      gex_summary: { net_gex: 6 }
    },
    {
      label: 't2',
      month_series: [
        { month: '2026-05', gex_distribution: [{ call_gex: 12, put_gex: -5 }] }
      ],
      gex_summary: { net_gex: 7 }
    }
  ])

  assert.deepEqual(trend.labels, ['t1', 't2'])
  const call = trend.series.find(s => s.name === 'Call 2026-05')
  const put = trend.series.find(s => s.name === 'Put 2026-05')
  const net = trend.series.find(s => s.name === 'Net GEX')
  assert.deepEqual(call.data, [10, 12])
  assert.deepEqual(put.data, [-4, -5])
  assert.equal(call.stack, CALL_PUT_STACK)
  assert.equal(put.stack, CALL_PUT_STACK)
  assert.deepEqual(net.data, [6, 7])
  assert.equal(trend.valueRange.max, -trend.valueRange.min)
  assert.equal(signedPutGex(4), -4)
  assert.equal(sumGexField([{ call_gex: 1 }, { call_gex: 2 }], 'call_gex'), 3)
})

test('net GEX bars use strike/value pairs so price marks sit at the quoted price', () => {
  const stacked = buildStackedNetGexSeries(
    [],
    [
      { strike: 2.95, call_gex: 4, put_gex: -1, net_gex: 3 },
      { strike: 3, call_gex: 2, put_gex: -3, net_gex: -1 }
    ],
    ['#1677ff'],
    (strikes) => [{ name: 'Price', xAxis: 2.993, strikes }]
  )
  const call = stacked.series.find(s => s.name === 'Call GEX')
  const net = stacked.series.find(s => s.name === 'Net GEX')
  assert.deepEqual(call.data, [[2.95, 4], [3, 2]])
  assert.equal(net.markLine.data[0].xAxis, 2.993)
})
