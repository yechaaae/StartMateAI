const toNumber = (value, fallback = 0) => {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))

const splitIntegerTotal = (total, weights) => {
  const safeTotal = Math.max(0, Math.round(toNumber(total)))
  if (!weights.length) return []

  const safeWeights = weights.map((weight) => Math.max(0, toNumber(weight)))
  const weightSum = safeWeights.reduce((sum, weight) => sum + weight, 0)
  const normalizedWeights = weightSum > 0 ? safeWeights : weights.map(() => 1)
  const normalizedSum = weightSum > 0 ? weightSum : weights.length
  const rawParts = normalizedWeights.map((weight) => (safeTotal * weight) / normalizedSum)
  const parts = rawParts.map(Math.floor)
  let remaining = safeTotal - parts.reduce((sum, value) => sum + value, 0)

  rawParts
    .map((value, index) => ({ index, fraction: value - Math.floor(value) }))
    .sort((a, b) => b.fraction - a.fraction)
    .forEach(({ index }) => {
      if (remaining <= 0) return
      parts[index] += 1
      remaining -= 1
    })

  return parts
}

const operatingDayNumbers = (operatingDays) => {
  const count = clamp(Math.round(toNumber(operatingDays, 1)), 1, 30)
  const days = new Set()

  for (let index = 0; index < count; index += 1) {
    days.add(Math.min(30, Math.floor((index * 30) / count) + 1))
  }

  for (let day = 1; days.size < count && day <= 30; day += 1) {
    days.add(day)
  }

  return [...days].sort((a, b) => a - b)
}

export const buildMonthlyPreview = (form) => {
  const pricePerOrder = toNumber(form.pricePerOrder)
  const expectedDailyOrders = toNumber(form.expectedDailyOrders)
  const operatingDays = Math.max(1, Math.round(toNumber(form.operatingDays, 1)))
  const variableCostRate = clamp(toNumber(form.variableCostRate), 0, 1)
  const fixedCost = Math.round(
    toNumber(form.monthlyRent)
    + toNumber(form.laborCost)
    + toNumber(form.marketingCost)
    + toNumber(form.otherFixedCost),
  )
  const revenue = Math.round(pricePerOrder * expectedDailyOrders * operatingDays)
  const variableCost = Math.round(revenue * variableCostRate)
  const totalCost = variableCost + fixedCost
  const profit = revenue - totalCost
  const contributionPerOrder = pricePerOrder * (1 - variableCostRate)

  return {
    revenue,
    variableCost,
    fixedCost,
    totalCost,
    profit,
    breakEvenCount: Math.ceil(fixedCost / Math.max(1, contributionPerOrder)),
    operatingDays,
  }
}

export const buildDailySimulation = (form) => {
  const preview = buildMonthlyPreview(form)
  const pricePerOrder = toNumber(form.pricePerOrder)
  const initialBudget = toNumber(form.initialBudget)
  const totalOrders = Math.round(toNumber(form.expectedDailyOrders) * preview.operatingDays)
  const openDays = operatingDayNumbers(preview.operatingDays)
  const openDaySet = new Set(openDays)
  const orderWeights = openDays.map((day) => {
    const progress = day / 30
    const weekdayFactor = [0.9, 1, 1, 1, 1.04, 1.12, 1.16][day % 7]
    return (0.72 + 0.56 * progress) * weekdayFactor
  })
  const dailyOrders = splitIntegerTotal(totalOrders, orderWeights)
  const dailyRevenue = dailyOrders.map((orders) => orders * pricePerOrder)
  const dailyVariableCost = splitIntegerTotal(preview.variableCost, dailyRevenue.map((revenue) => Math.max(1, revenue)))
  const dailyFixedCost = splitIntegerTotal(preview.fixedCost, Array.from({ length: 30 }, () => 1))

  let cumulativeProfit = 0
  let bepDay = null

  const metrics = Array.from({ length: 30 }, (_, index) => {
    const day = index + 1
    const openIndex = openDays.indexOf(day)
    const orders = openDaySet.has(day) ? dailyOrders[openIndex] : 0
    const revenue = openDaySet.has(day) ? dailyRevenue[openIndex] : 0
    const variableCost = openDaySet.has(day) ? dailyVariableCost[openIndex] : 0
    const fixedCost = dailyFixedCost[index]
    const profit = revenue - variableCost - fixedCost

    cumulativeProfit += profit
    if (!bepDay && cumulativeProfit >= 0) bepDay = day

    return {
      day,
      orders,
      revenue,
      variableCost,
      fixedCost,
      profit,
      cumulativeProfit,
      cashBalance: initialBudget + cumulativeProfit,
    }
  })

  return {
    metrics,
    summary: {
      totalRevenue: preview.revenue,
      totalCost: preview.totalCost,
      totalProfit: preview.profit,
      bepDay,
      breakEvenCount: preview.breakEvenCount,
      cashShortageRisk: initialBudget + cumulativeProfit < toNumber(form.monthlyRent) ? '높음' : '낮음',
    },
  }
}
