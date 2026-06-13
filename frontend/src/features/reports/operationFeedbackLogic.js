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

export const parseDisplayNumber = (value) => {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : 0
  }

  const normalized = String(value ?? '').replace(/[^0-9.-]/g, '')
  if (!normalized || normalized === '-' || normalized === '.') {
    return 0
  }

  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : 0
}

const toText = (value, fallback = '') => {
  if (value === null || value === undefined) {
    return fallback
  }
  const text = String(value).trim()
  return text || fallback
}

const formatKpiValue = (value, unit) => {
  const parsed = parseNumberInput(value)
  if (unit === '원') {
    return `${parsed.toLocaleString('ko-KR')}원`
  }
  if (unit === '%') {
    return `${roundOneDecimal(parsed)}%`
  }
  return `${parsed.toLocaleString('ko-KR')}${unit ?? ''}`
}

const normalizeKpi = (item) => {
  if (Array.isArray(item)) {
    return { label: toText(item[0]), value: toText(item[1]), delta: toText(item[2]), good: item[3] ?? null }
  }
  if (item && typeof item === 'object') {
    // 사용자 입력 형태: { key, label, unit, current, previous }
    if ('current' in item || 'previous' in item) {
      const change = calculateChangePercent(item.current, item.previous)
      const good = item.key === 'totalCost' ? change <= 0 : change >= 0
      return {
        label: toText(item.label, toText(item.key)),
        value: formatKpiValue(item.current, item.unit),
        delta: `${change > 0 ? '+' : ''}${change}%`,
        good,
      }
    }
    // 표시 형태: { label, value, delta, good }
    return {
      label: toText(item.label),
      value: toText(item.value),
      delta: toText(item.delta),
      good: item.good ?? null,
    }
  }
  return { label: '', value: toText(item), delta: '', good: null }
}

const normalizeProduct = (item, index = 0) => {
  if (Array.isArray(item)) {
    return {
      id: `product-${index + 1}`,
      name: toText(item[0]),
      pct: roundOneDecimal(clampPercent(parseNumberInput(item[1]))),
      locked: false,
    }
  }
  const pctSource = item?.pct ?? item?.share ?? 0
  return {
    id: toText(item?.id, `product-${index + 1}`),
    name: toText(item?.name),
    pct: roundOneDecimal(clampPercent(parseNumberInput(pctSource))),
    locked: Boolean(item?.locked),
  }
}

const normalizeChannel = (item) => {
  if (Array.isArray(item)) {
    return { name: toText(item[0]), summary: toText(item[1]) }
  }
  if (item && typeof item === 'object') {
    return { name: toText(item.name), summary: toText(item.summary ?? item.note) }
  }
  return { name: '', summary: toText(item) }
}

const normalizeSuggestion = (item) => {
  const base = Array.isArray(item)
    ? { title: toText(item[0]), body: toText(item[1]), link: item[2] ?? null }
    : { title: toText(item?.title), body: toText(item?.body), link: item?.link ?? null }
  return { ...base, linkLabel: base.link ? 'SNS 홍보 초안으로' : null }
}

export const normalizeOperationReport = (data) => ({
  period: toText(data?.period),
  notes: toText(data?.notes),
  kpis: (data?.kpis ?? []).map(normalizeKpi),
  products: (data?.products ?? []).map(normalizeProduct),
  channels: (data?.channels ?? []).map(normalizeChannel).filter((channel) => channel.name || channel.summary),
  suggestions: (data?.suggestions ?? []).map(normalizeSuggestion).filter((suggestion) => suggestion.title),
})

export const scaleSharesTo100 = (products) => {
  const list = products.map((product, index) => ({
    id: toText(product.id, `product-${index + 1}`),
    name: product.name,
    locked: Boolean(product.locked),
    pct: roundOneDecimal(clampPercent(parseNumberInput(product.pct ?? product.share))),
  }))
  if (!list.length) {
    return list
  }

  const total = list.reduce((sum, product) => sum + product.pct, 0)
  let allocated = 0
  return list.map((product, index) => {
    const isLast = index === list.length - 1
    const ratio = total > 0 ? product.pct / total : 1 / list.length
    const pct = isLast ? roundOneDecimal(100 - allocated) : roundOneDecimal(100 * ratio)
    allocated = roundOneDecimal(allocated + pct)
    return { ...product, pct: clampPercent(pct) }
  })
}

export const buildOperationFeedbackPayload = (data, selectedSuggestionTitle) => {
  const report = normalizeOperationReport(data)
  const period = /^\d{4}-\d{2}$/.test(report.period) ? report.period : null
  const products = scaleSharesTo100(report.products)

  const kpis = (data?.kpis ?? []).map((item) => {
    if (item && !Array.isArray(item) && item.key) {
      return {
        key: item.key,
        label: toText(item.label, toText(item.key)),
        unit: toText(item.unit),
        current: parseNumberInput(item.current),
        previous: item.previous === null || item.previous === undefined ? null : parseNumberInput(item.previous),
      }
    }
    const kpi = normalizeKpi(item)
    return { key: null, label: kpi.label, unit: '', current: parseDisplayNumber(kpi.value), previous: null }
  })

  return {
    period,
    kpis,
    products: products.map((product) => ({
      name: product.name,
      share: product.pct,
      locked: Boolean(product.locked),
    })),
    channels: report.channels.map((channel) => [channel.name, channel.summary]),
    notes: report.notes,
    suggestions: report.suggestions.map((suggestion) => ({
      title: suggestion.title,
      body: suggestion.body,
      link: suggestion.link ?? null,
    })),
    selectedSuggestionTitle: selectedSuggestionTitle ?? report.suggestions[0]?.title ?? null,
  }
}

let productIdCounter = 0

export const createProductRow = (name = '', share = 0) => {
  productIdCounter += 1
  return {
    id: `product-new-${productIdCounter}`,
    name: toText(name),
    share: roundOneDecimal(clampPercent(parseNumberInput(share))),
    locked: false,
  }
}

export const addProduct = (products, name = '', share = 0) => [
  ...(products ?? []).map((product) => ({ ...product })),
  createProductRow(name, share),
]

// 상품을 인덱스로 삭제하고 남은 비중을 100으로 다시 정규화한다(잠금/이름/id 보존).
// 인덱스 기준으로 지우는 이유: 저장된 리포트를 다시 불러오면 product.id가 없을 수 있어
// id 매칭으로 지우면 전체가 삭제될 수 있다.
export const removeProduct = (products, index) => {
  const remaining = (products ?? []).filter((_, productIndex) => productIndex !== index)
  if (!remaining.length) {
    return remaining
  }
  return scaleSharesTo100(remaining).map((product) => ({
    id: product.id,
    name: product.name,
    locked: Boolean(product.locked),
    share: product.pct,
  }))
}

// 직전 저장 리포트의 current 값을 이번 입력의 previous 기준으로 삼는다.
export const applyPreviousFromSavedReport = (kpis, savedReportData) => {
  const savedKpis = savedReportData?.kpis ?? []
  const previousByKey = new Map()
  savedKpis.forEach((item) => {
    if (item && !Array.isArray(item) && item.key != null) {
      previousByKey.set(item.key, parseNumberInput(item.current))
    }
  })

  return (kpis ?? []).map((kpi) => {
    if (kpi && kpi.key != null && previousByKey.has(kpi.key)) {
      return { ...kpi, previous: previousByKey.get(kpi.key) }
    }
    return { ...kpi }
  })
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
