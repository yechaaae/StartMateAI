const clampPercent = (value) => Math.min(100, Math.max(0, value))

export const roundOneDecimal = (value) => Math.round(value * 10) / 10

export const parseNumberInput = (value) => {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : 0
  }

  const normalized = String(value ?? '').replace(/,/g, '').trim()
  if (!normalized) {
    return 0
  }

  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : 0
}

export const calculateChangePercent = (currentValue, previousValue) => {
  const current = parseNumberInput(currentValue)
  const previous = parseNumberInput(previousValue)

  if (previous <= 0) {
    return current > 0 ? 1000 : 0
  }

  return roundOneDecimal(Math.max(-1000, Math.min(1000, ((current - previous) / previous) * 100)))
}

export const normalizeProductShares = (products, changedIndex, nextShare, options = {}) => {
  const list = products.map((product, index) => ({
    ...product,
    share: roundOneDecimal(clampPercent(index === changedIndex ? parseNumberInput(nextShare) : parseNumberInput(product.share))),
  }))

  if (!list.length) {
    return list
  }

  const changed = list[changedIndex]
  if (!changed) {
    return list
  }

  const lockedIndexes = new Set(options.lockedIndexes ?? [])
  const otherLockedIndexes = list
    .map((_, index) => index)
    .filter((index) => index !== changedIndex && lockedIndexes.has(index))
  const otherLockedTotal = roundOneDecimal(otherLockedIndexes.reduce((sum, index) => sum + list[index].share, 0))
  changed.share = roundOneDecimal(clampPercent(Math.min(changed.share, 100 - otherLockedTotal)))

  const fixedIndexes = new Set([changedIndex, ...otherLockedIndexes])
  const remainingTotal = roundOneDecimal(100 - [...fixedIndexes].reduce((sum, index) => sum + list[index].share, 0))
  const otherIndexes = list.map((_, index) => index).filter((index) => !fixedIndexes.has(index))

  if (!otherIndexes.length) {
    changed.share = roundOneDecimal(clampPercent(100 - otherLockedTotal))
    return list
  }

  const previousOtherTotal = otherIndexes.reduce((sum, index) => sum + parseNumberInput(products[index]?.share), 0)
  let allocated = 0

  otherIndexes.forEach((index, order) => {
    const isLast = order === otherIndexes.length - 1
    const ratio = previousOtherTotal > 0 ? parseNumberInput(products[index]?.share) / previousOtherTotal : 1 / otherIndexes.length
    const share = isLast ? roundOneDecimal(remainingTotal - allocated) : roundOneDecimal(remainingTotal * ratio)
    list[index].share = clampPercent(share)
    allocated = roundOneDecimal(allocated + list[index].share)
  })

  const total = roundOneDecimal(list.reduce((sum, product) => sum + product.share, 0))
  const drift = roundOneDecimal(100 - total)
  if (Math.abs(drift) >= 0.1) {
    const targetIndex = otherIndexes[otherIndexes.length - 1] ?? changedIndex
    list[targetIndex].share = roundOneDecimal(clampPercent(list[targetIndex].share + drift))
  }

  return list
}

export const buildMockOperationSuggestions = ({ kpis, products, notes }) => {
  const conversion = kpis.find((item) => item.key === 'adConversionRate')
  const sales = kpis.find((item) => item.key === 'totalSales')
  const topProduct = [...products].sort((left, right) => right.share - left.share)[0]
  const conversionChange = calculateChangePercent(conversion?.current, conversion?.previous)
  const salesChange = calculateChangePercent(sales?.current, sales?.previous)

  const suggestions = []

  if (conversionChange < 0) {
    suggestions.push({
      title: '광고 전환율 회복',
      body: '전환율이 이전 기준보다 낮습니다. 광고 소재를 상품별로 분리하고, 랜딩 문구는 구매 혜택과 예약 동선을 먼저 보이게 조정해보세요.',
      link: 'sns',
    })
  }

  if (topProduct) {
    suggestions.push({
      title: `${topProduct.name} 비중 활용`,
      body: `${topProduct.name}의 매출 비중이 가장 큽니다. 세트 구성이나 재구매 쿠폰을 붙여 객단가를 올리는 실험을 추천합니다.`,
    })
  }

  suggestions.push({
    title: salesChange >= 0 ? '성장 흐름 유지' : '매출 방어 우선',
    body: salesChange >= 0
      ? '매출은 이전 기준보다 개선되었습니다. 지출 증가 폭을 함께 점검하면서 효과가 좋은 상품과 채널에 운영 시간을 더 배분해보세요.'
      : '매출이 이전 기준보다 줄었습니다. 고정 지출을 먼저 묶고, 주문 수를 회복할 수 있는 짧은 프로모션을 테스트해보세요.',
  })

  if (notes?.trim()) {
    suggestions.push({
      title: '메모 기반 점검',
      body: '입력한 운영 메모를 기준으로 이번 주 원인 가설을 하나만 정하고, 다음 입력 때 같은 기준으로 비교해보세요.',
    })
  }

  return suggestions.slice(0, 3)
}
