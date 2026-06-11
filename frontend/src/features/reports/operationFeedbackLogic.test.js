import test from 'node:test'
import assert from 'node:assert/strict'
import {
  calculateChangePercent,
  normalizeProductShares,
} from './operationFeedbackLogic.js'

test('calculateChangePercent compares current value against previous value with one decimal', () => {
  assert.equal(calculateChangePercent(1250, 1000), 25)
  assert.equal(calculateChangePercent(333, 300), 11)
  assert.equal(calculateChangePercent(1.8, 2.4), -25)
})

test('calculateChangePercent caps the change at 1000 percent', () => {
  assert.equal(calculateChangePercent(1200, 100), 1000)
  assert.equal(calculateChangePercent(0, 100), -100)
  assert.equal(calculateChangePercent(50, 0), 1000)
})

test('normalizeProductShares keeps total at 100 while reducing other products proportionally', () => {
  const result = normalizeProductShares([
    { id: 'a', name: 'Americano', share: 40 },
    { id: 'b', name: 'Cookie', share: 30 },
    { id: 'c', name: 'Cake', share: 30 },
  ], 0, 60)

  assert.deepEqual(result.map((item) => item.share), [60, 20, 20])
  assert.equal(result.reduce((sum, item) => sum + item.share, 0), 100)
})

test('normalizeProductShares allows one decimal and fixes rounding drift', () => {
  const result = normalizeProductShares([
    { id: 'a', name: 'Americano', share: 33.3 },
    { id: 'b', name: 'Cookie', share: 33.3 },
    { id: 'c', name: 'Cake', share: 33.4 },
  ], 1, 44.4)

  assert.equal(result[1].share, 44.4)
  assert.equal(Number(result.reduce((sum, item) => sum + item.share, 0).toFixed(1)), 100)
  assert.ok(result.every((item) => item.share >= 0 && item.share <= 100))
})

test('normalizeProductShares preserves manually locked product shares when another product changes', () => {
  const result = normalizeProductShares([
    { id: 'a', name: 'Americano', share: 50 },
    { id: 'b', name: 'Cookie', share: 20 },
    { id: 'c', name: 'Cake', share: 30 },
  ], 1, 25, { lockedIndexes: new Set([0]) })

  assert.deepEqual(result.map((item) => item.share), [50, 25, 25])
  assert.equal(result.reduce((sum, item) => sum + item.share, 0), 100)
})
