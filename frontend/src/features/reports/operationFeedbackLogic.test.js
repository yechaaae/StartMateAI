import test from 'node:test'
import assert from 'node:assert/strict'
import {
  addProduct,
  applyPreviousFromSavedReport,
  buildOperationFeedbackPayload,
  calculateChangePercent,
  normalizeOperationReport,
  normalizeProductShares,
  removeProduct,
  scaleSharesTo100,
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

test('normalizeOperationReport maps AI tuple shapes into display objects', () => {
  const report = normalizeOperationReport({
    period: '최근 30일',
    kpis: [['이번 달 매출', '₩2,780,000', '+12%', true]],
    products: [['대표 상품', 60], ['보조 상품', 40]],
    channels: [['AI 진단', '광고 효율 점검 필요']],
    suggestions: [['광고 전환율 회복', '소재를 분리하세요', 'sns']],
  })

  assert.deepEqual(report.kpis[0], { label: '이번 달 매출', value: '₩2,780,000', delta: '+12%', good: true })
  assert.deepEqual(
    report.products.map(({ name, pct }) => ({ name, pct })),
    [{ name: '대표 상품', pct: 60 }, { name: '보조 상품', pct: 40 }],
  )
  assert.equal(report.products[0].locked, false)
  assert.deepEqual(report.channels, [{ name: 'AI 진단', summary: '광고 효율 점검 필요' }])
  assert.equal(report.suggestions[0].title, '광고 전환율 회복')
  assert.equal(report.suggestions[0].link, 'sns')
  assert.equal(report.suggestions[0].linkLabel, 'SNS 홍보 초안으로')
})

test('normalizeOperationReport converts user-input KPI objects into deltas', () => {
  const report = normalizeOperationReport({
    kpis: [{ key: 'totalSales', label: '매출', unit: '원', current: 2780000, previous: 2480000 }],
  })

  assert.equal(report.kpis[0].label, '매출')
  assert.equal(report.kpis[0].value, '2,780,000원')
  assert.equal(report.kpis[0].delta, '+12.1%')
  assert.equal(report.kpis[0].good, true)
})

test('scaleSharesTo100 rescales arbitrary AI shares to total exactly 100', () => {
  const result = scaleSharesTo100([{ name: 'a', pct: 30 }, { name: 'b', pct: 30 }])
  assert.equal(result.reduce((sum, item) => sum + item.pct, 0), 100)
})

test('buildOperationFeedbackPayload drops non-YYYY-MM periods and normalizes shares', () => {
  const payload = buildOperationFeedbackPayload({
    period: '최근 30일',
    kpis: [['이번 달 매출', '₩2,780,000', '+12%', true]],
    products: [['대표 상품', 60], ['보조 상품', 30]],
    channels: [['AI 진단', '점검 필요']],
    suggestions: [['광고 전환율 회복', '소재 분리', 'sns']],
  }, '광고 전환율 회복')

  assert.equal(payload.period, null)
  assert.equal(payload.kpis[0].current, 2780000)
  assert.equal(payload.products.reduce((sum, item) => sum + item.share, 0), 100)
  assert.deepEqual(payload.channels, [['AI 진단', '점검 필요']])
  assert.equal(payload.selectedSuggestionTitle, '광고 전환율 회복')
})

test('buildOperationFeedbackPayload keeps valid YYYY-MM period and input KPI keys', () => {
  const payload = buildOperationFeedbackPayload({
    period: '2026-06',
    kpis: [{ key: 'totalSales', label: '매출', unit: '원', current: 2780000, previous: 2480000 }],
    products: [{ name: '아메리카노', share: 100 }],
  }, null)

  assert.equal(payload.period, '2026-06')
  assert.equal(payload.kpis[0].key, 'totalSales')
  assert.equal(payload.kpis[0].previous, 2480000)
  assert.equal(payload.products[0].share, 100)
})

test('buildOperationFeedbackPayload preserves locked flag per product', () => {
  const payload = buildOperationFeedbackPayload({
    period: '2026-06',
    kpis: [{ key: 'totalSales', label: '매출', unit: '원', current: 100, previous: 90 }],
    products: [
      { id: 'a', name: '아메리카노', share: 60, locked: true },
      { id: 'b', name: '쿠키', share: 40, locked: false },
    ],
  }, null)

  assert.equal(payload.products[0].locked, true)
  assert.equal(payload.products[1].locked, false)
})

test('addProduct appends a zero-share row without breaking the total', () => {
  const next = addProduct([
    { id: 'a', name: '아메리카노', share: 60 },
    { id: 'b', name: '쿠키', share: 40 },
  ])

  assert.equal(next.length, 3)
  assert.equal(next[2].share, 0)
  assert.equal(next[2].locked, false)
  assert.equal(next.reduce((sum, item) => sum + item.share, 0), 100)
})

test('removeProduct deletes a row by index and rescales the rest to total 100', () => {
  const next = removeProduct([
    { id: 'a', name: '아메리카노', share: 50 },
    { id: 'b', name: '쿠키', share: 30 },
    { id: 'c', name: '케이크', share: 20 },
  ], 2)

  assert.equal(next.length, 2)
  assert.ok(next.every((item) => item.id !== 'c'))
  assert.equal(Number(next.reduce((sum, item) => sum + item.share, 0).toFixed(1)), 100)
})

test('removeProduct without ids deletes only the targeted index', () => {
  const next = removeProduct([
    { name: '아메리카노', share: 50 },
    { name: '쿠키', share: 30 },
    { name: '케이크', share: 20 },
  ], 0)

  assert.equal(next.length, 2)
  assert.deepEqual(next.map((item) => item.name), ['쿠키', '케이크'])
  assert.equal(Number(next.reduce((sum, item) => sum + item.share, 0).toFixed(1)), 100)
})

test('applyPreviousFromSavedReport sets previous from the saved record current values', () => {
  const kpis = applyPreviousFromSavedReport(
    [
      { key: 'totalSales', current: 3000000, previous: 0 },
      { key: 'adConversionRate', current: 2.1, previous: 0 },
    ],
    {
      kpis: [
        { key: 'totalSales', current: 2480000 },
        { key: 'adConversionRate', current: 2.4 },
      ],
    },
  )

  assert.equal(kpis[0].previous, 2480000)
  assert.equal(kpis[1].previous, 2.4)
  assert.equal(kpis[0].current, 3000000)
})
