import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildStrikeMarkLineData,
  nearestStrikeLabel,
  pairPointField,
  strikeValueAxis
} from '../../src/views/market-composite-analysis/strike-mark-lines.js'

test('price and flip marks use the exact numeric price on a value axis', () => {
  const marks = buildStrikeMarkLineData(
    [
      { name: 'Price', value: 2.993, color: '#1890ff', width: 2 },
      { name: 'Flip', value: 2.972, color: '#faad14', width: 1.5 },
      { name: 'Pin', value: 3, color: '#722ed1', width: 1.5 },
      { name: 'Call Wall', value: 3.1, color: '#52c41a', width: 1.5 }
    ],
    ['2.90', '2.95', '3', '3.1'],
    {
      formatPrice: v => Number(v).toFixed(3),
      formatStrike: v => String(v)
    }
  )
  const price = marks.find(m => m.name === 'Price')
  const flip = marks.find(m => m.name === 'Flip')
  const pin = marks.find(m => String(m.name).includes('Pin'))
  const wall = marks.find(m => String(m.name).includes('Call Wall'))
  assert.equal(price.xAxis, 2.993)
  assert.equal(price.label.formatter, 'Price 2.993')
  assert.equal(flip.xAxis, 2.972)
  assert.equal(flip.label.formatter, 'Flip 2.972')
  assert.equal(flip.lineStyle.type, 'dashed')
  assert.equal(pin.xAxis, 3)
  assert.equal(wall.xAxis, 3.1)
  assert.equal(nearestStrikeLabel(['2.90', '2.95', '3'], 2.993), '3')
  assert.ok(marks.indexOf(pin) < marks.indexOf(price))
  assert.ok(marks.indexOf(pin) < marks.indexOf(flip))
})

test('flip stays yellow and paints above pin when both sit on the same strike', () => {
  const marks = buildStrikeMarkLineData(
    [
      { name: 'Price', value: 3.024, color: '#1890ff', width: 2 },
      { name: 'Flip', value: 3, color: '#faad14', width: 1.5 },
      { name: 'Pin', value: 3, color: '#722ed1', width: 1.5 }
    ],
    ['2.95', '3', '3.1'],
    {
      formatPrice: v => Number(v).toFixed(3),
      formatStrike: v => String(v)
    }
  )
  const flip = marks.find(m => m.name === 'Flip')
  const pin = marks.find(m => String(m.name).includes('Pin'))
  assert.equal(flip.xAxis, 3)
  assert.equal(pin.xAxis, 3)
  assert.equal(flip.lineStyle.color, '#faad14')
  assert.equal(flip.lineStyle.type, 'dashed')
  assert.ok(marks.indexOf(pin) < marks.indexOf(flip))
})

test('strike value axis expands to include price between listed strikes', () => {
  const axis = strikeValueAxis(['2.90', '2.95', '3.00'], [2.993, 2.972])
  assert.equal(axis.type, 'value')
  assert.ok(axis.min < 2.90)
  assert.ok(axis.max > 3.00)
  assert.equal(axis.axisLabel.formatter(2.993), '2.993')
  assert.deepEqual(pairPointField([{ strike: 2.95, call_oi: 10 }], 'call_oi'), [[2.95, 10]])
})
