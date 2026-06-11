import { useState } from 'react'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'
import {
  calculateChangePercent,
  normalizeProductShares,
  parseNumberInput,
  roundOneDecimal,
} from './operationFeedbackLogic'

const KPI_LIMITS = {
  totalSales: { min: 0, step: 10000 },
  totalCost: { min: 0, step: 10000 },
  orderCount: { min: 0, step: 5 },
  adConversionRate: { min: 0, max: 100, step: 1 },
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
      const min = limits?.min ?? Number.NEGATIVE_INFINITY
      const max = limits?.max ?? Number.POSITIVE_INFINITY
      const limited = Math.min(max, Math.max(min, parsed))
      const value = item.key === 'adConversionRate' ? roundOneDecimal(limited) : Math.round(limited)
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

const updateProductShare = (setData, index, nextShare, lockedIndexes) => {
  setData((current) => ({
    ...current,
    products: normalizeProductShares(current.products, index, nextShare, { lockedIndexes }),
  }))
}

const addProduct = (setData, lockedIndexes) => {
  setData((current) => {
    const next = [
      ...current.products,
      { id: `product-${Date.now()}`, name: '새 상품', share: 0 },
    ]
    const lastIndex = next.length - 1
    return {
      ...current,
      products: normalizeProductShares(next, lastIndex, 10, { lockedIndexes }),
    }
  })
}

const removeProduct = (setData, index, lockedIndexes) => {
  setData((current) => {
    if (current.products.length <= 1) {
      return current
    }
    const next = current.products.filter((_, itemIndex) => itemIndex !== index)
    return {
      ...current,
      products: normalizeProductShares(next, 0, next[0]?.share ?? 100, { lockedIndexes }),
    }
  })
}

const equalizeProductShares = (setData) => {
  setData((current) => {
    const products = current.products ?? []
    if (!products.length) {
      return current
    }

    const baseShare = roundOneDecimal(100 / products.length)
    let allocated = 0
    return {
      ...current,
      products: products.map((product, index) => {
        const isLast = index === products.length - 1
        const share = isLast ? roundOneDecimal(100 - allocated) : baseShare
        allocated = roundOneDecimal(allocated + share)
        return { ...product, share }
      }),
    }
  })
}

const lockedIndexesAfterRemoval = (lockedIndexes, removedIndex) => {
  const nextLockedIndexes = new Set()
  lockedIndexes.forEach((lockedIndex) => {
    if (lockedIndex < removedIndex) {
      nextLockedIndexes.add(lockedIndex)
    } else if (lockedIndex > removedIndex) {
      nextLockedIndexes.add(lockedIndex - 1)
    }
  })
  return nextLockedIndexes
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
  const [lockedProductIndexes, setLockedProductIndexes] = useState(new Set())
  const productTotal = roundOneDecimal((data.products ?? []).reduce((sum, item) => sum + parseNumberInput(item.share), 0))

  const handleProductShareChange = (index, nextShare) => {
    if (lockedProductIndexes.has(index)) {
      return
    }
    updateProductShare(setData, index, nextShare, lockedProductIndexes)
  }

  const toggleProductLock = (index) => {
    setLockedProductIndexes((current) => {
      const next = new Set(current)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const handleRemoveProduct = (index) => {
    const nextLockedIndexes = lockedIndexesAfterRemoval(lockedProductIndexes, index)
    setLockedProductIndexes(nextLockedIndexes)
    removeProduct(setData, index, nextLockedIndexes)
  }

  const handleEqualizeProducts = () => {
    setLockedProductIndexes(new Set())
    equalizeProductShares(setData)
  }

  return (
    <div className="report-stack">
      <Card>
        <div className="card-head operation-card-head">
          <div>
            <h3>운영 입력 정보</h3>
            <p>현재값과 기존값을 비교해 개선 우선순위를 계산합니다.</p>
          </div>
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
                    step={limits.step ?? 1}
                    value={item.current}
                    onChange={(event) => updateKpiValue(setData, item.key, 'current', event.target.value)}
                  />
                </label>
                <div className="operation-previous-value">
                  <span>이전 기준</span>
                  <strong>{formatValue(item.previous, item.unit)}</strong>
                </div>
                <em className={good ? 'good' : 'bad'}>{change > 0 ? '+' : ''}{change}%</em>
              </div>
            )
          })}
        </div>

        <div className="operation-block">
          <div className="operation-block-title">
            <small>상품 비중</small>
            <span>총합 {productTotal}%</span>
            <div className="operation-block-actions">
              <button type="button" onClick={handleEqualizeProducts}>균등 배분</button>
              <button type="button" onClick={() => addProduct(setData, lockedProductIndexes)}>상품 추가</button>
            </div>
          </div>
          {(data.products ?? []).map((product, index) => {
            const share = parseNumberInput(product.share)
            const locked = lockedProductIndexes.has(index)

            return (
              <div className={locked ? 'bar-row operation-edit-row locked' : 'bar-row operation-edit-row'} key={product.id ?? product.name}>
                <input
                  value={product.name}
                  onChange={(event) => updateProductName(setData, index, event.target.value)}
                  aria-label="상품명"
                />
                <label className="operation-share-input">
                  <input
                    className="operation-share-number"
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    value={product.share}
                    onChange={(event) => handleProductShareChange(index, event.target.value)}
                    disabled={locked}
                    aria-label="상품 비중"
                  />
                  <span>%</span>
                </label>
                <button
                  type="button"
                  className={locked ? 'operation-lock-button locked' : 'operation-lock-button'}
                  onClick={() => toggleProductLock(index)}
                  aria-label={`${product.name} 비중 ${locked ? '잠금 해제' : '잠금'}`}
                  title={locked ? '비중 잠금 해제' : '비중 잠금'}
                >
                  <Icon name={locked ? 'lock' : 'unlock'} size={16} />
                </button>
                <i><em style={{ width: `${share}%`, background: 'var(--a-operation)' }} /></i>
                <button type="button" className="operation-delete-button" onClick={() => handleRemoveProduct(index)}>삭제</button>
              </div>
            )
          })}
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

        <div className="operation-submit-row">
          <button
            type="button"
            className="operation-primary-button"
            onClick={onRequestOperationFeedback}
            disabled={operationFeedbackSaving}
          >
            {operationFeedbackSaving ? '피드백 저장 중' : '입력값으로 피드백 받기'}
          </button>
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
