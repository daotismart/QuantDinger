import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildCallPutGexTrendSeries,
  buildCallPutStackedGexSeries,
  sumGexField
} from '../../src/views/market-composite-analysis/gex-chart-series.js'

test('stacks call and put GEX by expiry month at each strike', () => {
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
  assert.equal(callMay.stack, 'call')
  assert.equal(putJun.stack, 'put')
  assert.deepEqual(callMay.data, [10, 8, 0])
  assert.deepEqual(putJun.data, [-1, 0, -2])
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
  const net = trend.series.find(s => s.name === 'Net GEX')
  assert.deepEqual(call.data, [10, 12])
  assert.deepEqual(net.data, [6, 7])
  assert.equal(sumGexField([{ call_gex: 1 }, { call_gex: 2 }], 'call_gex'), 3)
})
