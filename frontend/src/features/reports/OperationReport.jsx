import { Card } from '../../shared/components/Card'
import {
  calculateChangePercent,
  normalizeProductShares,
  parseNumberInput,
  roundOneDecimal,
} from './operationFeedbackLogic'

const KPI_LIMITS = {
  adConversionRate: { min: 0, max: 100, step: '0.1' },
}

const formatValue = (value, unit) => {
  const parsed = parseNumberInput(value)
  if (unit === '원') {
    return `${parsed.toLocaleString('ko-KR')}원`
  }
  if (unit === '%') {
    return `${roundOneDecimal(parsed)}%`
  }
  return `${parsed.toLocaleString('ko-KR')}${unit}`
}

const updateKpiValue = (setData, key, field, nextValue) => {
  setData((current) => ({
    ...current,
    kpis: current.kpis.map((item) => {
      if (item.key !== key) return item
      const limits = KPI_LIMITS[item.key]
      const parsed = parseNumberInput(nextValue)
      const value = limits
        ? roundOneDecimal(Math.min(limits.max, Math.max(limits.min, parsed)))
        : parsed
      return { ...item, [field]: value }
    }),
  }))
}

const updateProductName = (setData, index, nextName) => {
  setData((current) => ({
    ...current,
    products: current.products.map((item, itemIndex) => (
      itemIndex === index ? { ...item, name: nextName } : item
    )),
  }))
}

const updateProductShare = (setData, index, nextShare) => {
  setData((current) => ({
    ...current,
    products: normalizeProductShares(current.products, index, nextShare),
  }))
}

const addProduct = (setData) => {
  setData((current) => {
    const next = [
      ...current.products,
      { id: `product-${Date.now()}`, name: '새 상품', share: 0 },
    ]
    const lastIndex = next.length - 1
    return {
      ...current,
      products: normalizeProductShares(next, lastIndex, 10),
    }
  })
}

const removeProduct = (setData, index) => {
  setData((current) => {
    if (current.products.length <= 1) {
      return current
    }
    const next = current.products.filter((_, itemIndex) => itemIndex !== index)
    return {
      ...current,
      products: normalizeProductShares(next, 0, next[0]?.share ?? 100),
    }
  })
}

const updateChannelValue = (setData, index, nextValue) => {
  setData((current) => ({
    ...current,
    channels: current.channels.map((item, itemIndex) => (
      itemIndex === index ? [item[0], nextValue] : item
    )),
  }))
}

const suggestionTitle = (suggestion) => Array.isArray(suggestion) ? suggestion[0] : suggestion.title
const suggestionBody = (suggestion) => Array.isArray(suggestion) ? suggestion[1] : suggestion.body
const suggestionLink = (suggestion) => Array.isArray(suggestion) ? suggestion[2] : suggestion.link

export const OperationReport = ({
  data,
  setData,
  go,
  selectedOperationSuggestionTitle,
  onSelectOperationSuggestion,
  onRequestOperationFeedback,
  operationFeedbackSaving,
}) => {
  const productTotal = roundOneDecimal((data.products ?? []).reduce((sum, item) => sum + parseNumberInput(item.share), 0))

  return (
    <div className="report-stack">
      <Card>
        <div className="card-head operation-card-head">
          <div>
            <h3>운영 입력 정보</h3>
            <p>현재값과 기존값을 비교해 개선 우선순위를 계산합니다.</p>
          </div>
          <button
            type="button"
            className="operation-primary-button"
            onClick={onRequestOperationFeedback}
            disabled={operationFeedbackSaving}
          >
            {operationFeedbackSaving ? '피드백 저장 중' : '입력값으로 피드백 받기'}
          </button>
        </div>

        <div className="operation-meta-grid">
          <label className="operation-field">
            <small>집계 기간</small>
            <input
              value={data.period ?? ''}
              onChange={(event) => setData((current) => ({ ...current, period: event.target.value }))}
              placeholder="예: 2026-06"
            />
          </label>
          <label className="operation-field">
            <small>운영 메모</small>
            <textarea
              value={data.notes ?? ''}
              onChange={(event) => setData((current) => ({ ...current, notes: event.target.value }))}
              placeholder="예: 이번 주 광고 효율이 급감했고, 쿠키 상품 주문은 유지됨"
              rows="3"
            />
          </label>
        </div>

        <div className="operation-kpi-table">
          {(data.kpis ?? []).map((item) => {
            const change = calculateChangePercent(item.current, item.previous)
            const good = item.key === 'totalCost' ? change <= 0 : change >= 0
            const limits = KPI_LIMITS[item.key] ?? {}

            return (
              <div className="operation-kpi-row" key={item.key}>
                <div>
                  <small>{item.label}</small>
                  <b>{formatValue(item.current, item.unit)}</b>
                </div>
                <label>
                  <span>현재값</span>
                  <input
                    type="number"
                    min={limits.min}
                    max={limits.max}
                    step={limits.step ?? '1'}
                    value={item.current}
                    onChange={(event) => updateKpiValue(setData, item.key, 'current', event.target.value)}
                  />
                </label>
                <label>
                  <span>기존값</span>
                  <input
                    type="number"
                    min={limits.min}
                    max={limits.max}
                    step={limits.step ?? '1'}
                    value={item.previous}
                    onChange={(event) => updateKpiValue(setData, item.key, 'previous', event.target.value)}
                  />
                </label>
                <em className={good ? 'good' : 'bad'}>{change > 0 ? '+' : ''}{change}%</em>
              </div>
            )
          })}
        </div>

        <div className="operation-block">
          <div className="operation-block-title">
            <small>상품 비중</small>
            <span>총합 {productTotal}%</span>
            <button type="button" onClick={() => addProduct(setData)}>상품 추가</button>
          </div>
          {(data.products ?? []).map((product, index) => (
            <div className="bar-row operation-edit-row" key={product.id ?? product.name}>
              <input
                value={product.name}
                onChange={(event) => updateProductName(setData, index, event.target.value)}
                aria-label="상품명"
              />
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={product.share}
                onChange={(event) => updateProductShare(setData, index, event.target.value)}
                aria-label="상품 비중"
              />
              <i><em style={{ width: `${product.share}%`, background: 'var(--a-operation)' }} /></i>
              <button type="button" onClick={() => removeProduct(setData, index)}>삭제</button>
            </div>
          ))}
        </div>

        <div className="operation-block">
          <small>채널 메모</small>
          <div className="operation-channel-list">
            {(data.channels ?? []).map(([name, summary], index) => (
              <label key={name} className="operation-field">
                <small>{name}</small>
                <input
                  value={summary}
                  onChange={(event) => updateChannelValue(setData, index, event.target.value)}
                />
              </label>
            ))}
          </div>
        </div>
      </Card>

      <Card>
        <h3>개선 제안</h3>
        {(data.suggestions ?? []).map((suggestion) => {
          const title = suggestionTitle(suggestion)
          const body = suggestionBody(suggestion)
          const link = suggestionLink(suggestion)
          const selected = selectedOperationSuggestionTitle === title

          return (
            <div key={title} className={selected ? 'suggest-card selected' : 'suggest-card'}>
              <button
                type="button"
                className="suggest-select"
                onClick={() => onSelectOperationSuggestion?.(title)}
              >
                <b>{title}</b>
                <p>{body}</p>
              </button>
              {link && <button type="button" onClick={() => go(link)}>SNS 홍보 초안으로 이동</button>}
            </div>
          )
        })}
      </Card>
    </div>
  )
}
