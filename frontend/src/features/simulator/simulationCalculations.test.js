import assert from 'node:assert/strict'
import test from 'node:test'
import { buildDailySimulation, buildMonthlyPreview } from './simulationCalculations.js'

const form = {
  initialBudget: 10000000,
  pricePerOrder: 90000,
  expectedDailyOrders: 2,
  operatingDays: 22,
  monthlyRent: 1359600,
  laborCost: 1500000,
  marketingCost: 500000,
  otherFixedCost: 500000,
  variableCostRate: 0.35,
}

test('daily simulation summary stays aligned with monthly preview totals', () => {
  const preview = buildMonthlyPreview(form)
  const simulation = buildDailySimulation(form)

  assert.equal(simulation.summary.totalRevenue, preview.revenue)
  assert.equal(simulation.summary.totalCost, preview.totalCost)
  assert.equal(simulation.summary.totalProfit, preview.profit)
  assert.equal(simulation.summary.breakEvenCount, preview.breakEvenCount)
  assert.equal(
    simulation.metrics.reduce((sum, item) => sum + item.revenue, 0),
    preview.revenue,
  )
  assert.equal(
    simulation.metrics.reduce((sum, item) => sum + item.variableCost + item.fixedCost, 0),
    preview.totalCost,
  )
})
