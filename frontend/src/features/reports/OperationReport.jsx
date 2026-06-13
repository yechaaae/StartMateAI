import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'
import { savedResultApi } from '../../shared/api/client'
import {
  addProduct,
  applyPreviousFromSavedReport,
  calculateChangePercent,
  normalizeOperationReport,
  normalizeProductShares,
  parseNumberInput,
  removeProduct,
  roundOneDecimal,
} from './operationFeedbackLogic'

const KPI_FIELDS = [
  { key: 'totalSales', label: '이번 달 매출', unit: '원', goodWhenUp: true, max: null, step: 1 },
  { key: 'totalCost', label: '이번 달 지출', unit: '원', goodWhenUp: false, max: null, step: 1 },
  { key: 'orderCount', label: '주문 수', unit: '건', goodWhenUp: true, max: null, step: 1 },
  { key: 'adConversionRate', label: '광고 전환율', unit: '%', goodWhenUp: true, max: 100, step: 0.1 },
]

const formatKpiValue = (value, unit) => {
  const parsed = parseNumberInput(value)
  if (unit === '%') {
    return `${roundOneDecimal(parsed)}%`
  }
  return `${parsed.toLocaleString('ko-KR')}${unit ?? ''}`
}

const formatDateLabel = (value) => {
  if (!value) {
    return ''
  }
  return String(value).slice(0, 10)
}

export const OperationReport = ({
  data,
  setData,
  go,
  selectedOperationSuggestionTitle,
  onSelectOperationSuggestion,
  onRequestOperationFeedback,
  operationFeedbackSaving,
}) => {
  const report = normalizeOperationReport(data)

  const period = data?.period ?? ''
  const kpis = useMemo(() => data?.kpis ?? [], [data])
  // 저장된 리포트를 다시 불러오면 id가 없을 수 있어 렌더 key용 id를 보강한다.
  const products = useMemo(
    () => (data?.products ?? []).map((product, index) => ({
      ...product,
      id: product.id ?? `product-${index + 1}`,
    })),
    [data],
  )

  const lockedIndexes = useMemo(
    () => new Set(products.map((product, index) => (product.locked ? index : -1)).filter((index) => index >= 0)),
    [products],
  )

  const shareTotal = useMemo(
    () => roundOneDecimal(products.reduce((sum, product) => sum + parseNumberInput(product.share ?? product.pct), 0)),
    [products],
  )
  // 상품이 있을 때만 비중 합계 100%를 강제한다(상품이 없으면 KPI만 저장 가능).
  const shareInvalid = products.length > 0 && Math.abs(shareTotal - 100) >= 0.05

  const [history, setHistory] = useState([])
  const [historyOpen, setHistoryOpen] = useState(false)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const prevSavingRef = useRef(operationFeedbackSaving)

  const loadHistory = useCallback(async () => {
    try {
      const response = await savedResultApi.list()
      const items = (response?.results ?? response?.savedResults ?? response ?? [])
        .filter((item) => (item.sourceFeature ?? '').toLowerCase() === 'operation'
          || item.resultType === 'OPERATION_REPORT')
      setHistory(items)
      return items
    } catch {
      setHistory([])
      return []
    }
  }, [])

  // 최초 진입 시 직전 저장 리포트의 current를 이번 입력의 previous 기준으로 채운다.
  // 의존성이 모두 안정적이라 1회만 실행된다(StrictMode dev에서는 첫 실행이 cancel되고 두 번째가 적용).
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      // 기준 월이 비어 있으면 이번 달로 기본 설정한다.
      if (!cancelled) {
        setData((current) => (
          /^\d{4}-\d{2}$/.test(current?.period ?? '')
            ? current
            : { ...current, period: new Date().toISOString().slice(0, 7) }
        ))
      }
      await loadHistory()
      try {
        const latest = await savedResultApi.latest('operation')
        const savedReportData = latest?.payload?.reportData
        if (!cancelled && savedReportData) {
          setData((current) => ({
            ...current,
            kpis: applyPreviousFromSavedReport(current?.kpis ?? [], savedReportData),
          }))
        }
      } catch {
        /* 직전 기록이 없으면 기본 previous를 그대로 사용한다. */
      }
    })()

    return () => {
      cancelled = true
    }
  }, [loadHistory, setData])

  // 저장이 끝나면 이력을 새로고침한다.
  useEffect(() => {
    if (prevSavingRef.current && !operationFeedbackSaving) {
      loadHistory()
    }
    prevSavingRef.current = operationFeedbackSaving
  }, [operationFeedbackSaving, loadHistory])

  // 입력값은 가공 없이 그대로 저장한다(매 키 입력마다 반올림/클램프하면 타이핑이 끊긴다).
  // data.kpis에 해당 key가 없으면(빈 배열·튜플 형태 등) 새 항목을 만들어 입력이 항상 반영되게 한다.
  const updateKpi = (key, raw) => {
    const field = KPI_FIELDS.find((item) => item.key === key)
    if (!field) {
      return
    }
    setData((current) => {
      const list = current?.kpis ?? []
      const exists = list.some((kpi) => kpi && !Array.isArray(kpi) && kpi.key === key)
      const nextKpis = exists
        ? list.map((kpi) => (
          kpi && !Array.isArray(kpi) && kpi.key === key ? { ...kpi, current: raw } : kpi
        ))
        : [...list, { key, label: field.label, unit: field.unit, current: raw, previous: null }]
      return { ...current, kpis: nextKpis }
    })
  }

  const updateProductName = (index, name) => {
    setData((current) => ({
      ...current,
      products: (current?.products ?? []).map((product, productIndex) => (
        productIndex === index ? { ...product, name } : product
      )),
    }))
  }

  const updateProductShare = (index, value) => {
    setData((current) => {
      const list = (current?.products ?? []).map((product) => ({
        ...product,
        share: product.share ?? product.pct ?? 0,
      }))
      const locks = new Set(list.map((product, productIndex) => (product.locked ? productIndex : -1)).filter((i) => i >= 0))
      const next = normalizeProductShares(list, index, value, { lockedIndexes: locks })
      return { ...current, products: next }
    })
  }

  const toggleProductLock = (index) => {
    setData((current) => ({
      ...current,
      products: (current?.products ?? []).map((product, productIndex) => (
        productIndex === index ? { ...product, locked: !product.locked } : product
      )),
    }))
  }

  const handleAddProduct = () => {
    setData((current) => ({ ...current, products: addProduct(current?.products ?? []) }))
  }

  const handleRemoveProduct = (index) => {
    setData((current) => ({ ...current, products: removeProduct(current?.products ?? [], index) }))
  }

  const updateNotes = (notes) => {
    setData((current) => ({ ...current, notes }))
  }

  const updatePeriod = (nextPeriod) => {
    setData((current) => ({ ...current, period: nextPeriod }))
  }

  const openDetail = async (savedResultId) => {
    setDetailLoading(true)
    try {
      const response = await savedResultApi.get(savedResultId)
      setDetail({
        title: response?.title ?? '운영 피드백',
        createdAt: response?.createdAt ?? null,
        report: normalizeOperationReport(response?.payload?.reportData ?? {}),
      })
    } catch {
      setDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <div className="report-stack">
      <Card className="op-card">
        <div className="card-head op-head">
          <div>
            <h3>운영 진단 리포트</h3>
            <p>이번 달 지표를 직접 입력하면 직전 저장값과 비교해 변화율을 계산해요.</p>
          </div>
          <label className="op-period">
            <span>기준 월</span>
            <input
              type="month"
              value={/^\d{4}-\d{2}$/.test(period) ? period : ''}
              onChange={(event) => updatePeriod(event.target.value)}
            />
          </label>
        </div>

        <div className="op-kpi-grid">
          {KPI_FIELDS.map((field) => {
            const kpi = kpis.find((item) => item && !Array.isArray(item) && item.key === field.key) ?? { key: field.key }
            const previous = kpi.previous
            const hasPrevious = previous !== null && previous !== undefined
            const change = hasPrevious ? calculateChangePercent(kpi.current, previous) : null
            const good = change === null ? null : field.goodWhenUp ? change >= 0 : change <= 0

            return (
              <div className="op-kpi op-kpi-edit" key={field.key}>
                <span className="op-kpi-label">{field.label}</span>
                <div className="op-kpi-input">
                  <input
                    type="number"
                    min={0}
                    max={field.max ?? undefined}
                    step={field.step}
                    placeholder="0"
                    value={kpi.current ?? ''}
                    onChange={(event) => updateKpi(field.key, event.target.value)}
                  />
                  <span className="op-kpi-unit">{field.unit}</span>
                </div>
                <div className="op-kpi-foot">
                  <span className="op-kpi-prev">
                    {hasPrevious ? `전월 ${formatKpiValue(previous, field.unit)}` : '직전 기록 없음'}
                  </span>
                  {change !== null && (
                    <span className={`op-kpi-delta ${good ? 'good' : 'bad'}`}>
                      {change > 0 ? '+' : ''}{change}%
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        <div className="op-section">
          <div className="op-section-title op-section-title-row">
            <span>상품별 판매 비중</span>
            {products.length > 0 && (
              <span className={`op-share-total ${Math.abs(shareTotal - 100) < 0.05 ? 'ok' : 'warn'}`}>
                합계 {shareTotal}%
              </span>
            )}
          </div>

          {products.map((product, index) => {
            const share = roundOneDecimal(parseNumberInput(product.share ?? product.pct))
            const locked = lockedIndexes.has(index)
            return (
              <div className={`op-product ${locked ? 'locked' : ''}`} key={product.id ?? `product-${index}`}>
                <div className="op-product-row">
                  <input
                    className="op-product-name"
                    type="text"
                    value={product.name ?? ''}
                    placeholder="상품명"
                    onChange={(event) => updateProductName(index, event.target.value)}
                  />
                  <div className="op-product-share">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step={0.1}
                      value={share}
                      disabled={locked}
                      onChange={(event) => updateProductShare(index, event.target.value)}
                    />
                    <span>%</span>
                  </div>
                  <button
                    type="button"
                    className={`op-icon-btn ${locked ? 'active' : ''}`}
                    onClick={() => toggleProductLock(index)}
                    title={locked ? '비중 고정 해제' : '비중 고정'}
                    aria-label={locked ? '비중 고정 해제' : '비중 고정'}
                  >
                    <Icon name={locked ? 'lock' : 'unlock'} size={16} />
                  </button>
                  <button
                    type="button"
                    className="op-icon-btn danger"
                    onClick={() => handleRemoveProduct(index)}
                    title="상품 삭제"
                    aria-label="상품 삭제"
                  >
                    <Icon name="trash" size={16} />
                  </button>
                </div>
                <div className="op-bar-track">
                  <div className="op-bar-fill" style={{ width: `${Math.min(100, Math.max(0, share))}%` }} />
                </div>
              </div>
            )
          })}

          {products.length === 0 && (
            <p className="op-empty op-product-empty">판매 상품을 추가하면 비중을 입력할 수 있어요.</p>
          )}

          <button type="button" className="op-add-product" onClick={handleAddProduct}>
            <Icon name="plus" size={15} /> 상품 추가
          </button>
        </div>

        <div className="op-section op-notes">
          <div className="op-section-title">운영 메모</div>
          <textarea
            className="op-notes-input"
            value={data?.notes ?? ''}
            placeholder="이번 달 운영에서 관찰한 내용을 적어두면 다음 입력 때 같은 기준으로 비교할 수 있어요."
            onChange={(event) => updateNotes(event.target.value)}
            rows={3}
          />
        </div>

        {report.channels.length > 0 && (
          <div className="op-section">
            <div className="op-section-title">채널 진단</div>
            <div className="op-channels">
              {report.channels.map((channel, index) => (
                <div className="op-channel" key={`${channel.name}-${index}`}>
                  {channel.name && <span className="op-channel-name">{channel.name}</span>}
                  <span className="op-channel-note">{channel.summary}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {onRequestOperationFeedback && (
          <div className="op-submit">
            <button
              type="button"
              className="op-save-button"
              onClick={onRequestOperationFeedback}
              disabled={operationFeedbackSaving || shareInvalid}
            >
              {operationFeedbackSaving ? '피드백 저장 중…' : '이 운영 피드백 저장'}
              {!operationFeedbackSaving && <Icon name="check" size={16} />}
            </button>
            {shareInvalid && (
              <span className="op-save-hint">상품 비중 합계가 100%일 때 저장할 수 있어요.</span>
            )}
          </div>
        )}
      </Card>

      <Card>
        <button
          type="button"
          className="op-history-toggle"
          onClick={() => setHistoryOpen((open) => !open)}
        >
          <span className="op-history-title">
            <Icon name="clock" size={16} /> 지난 운영 기록 {history.length > 0 ? `(${history.length})` : ''}
          </span>
          <Icon name="chevron" size={16} className={historyOpen ? 'op-chevron open' : 'op-chevron'} />
        </button>
        {historyOpen && (
          <div className="op-history-list">
            {history.length === 0 && <p className="op-empty">아직 저장된 운영 기록이 없어요.</p>}
            {history.map((item) => (
              <button
                type="button"
                className="op-history-item"
                key={item.id}
                onClick={() => openDetail(item.id)}
              >
                <span className="op-history-item-title">{item.title}</span>
                <span className="op-history-item-date">{formatDateLabel(item.createdAt)}</span>
              </button>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <div className="card-head">
          <div>
            <h3>개선 제안</h3>
          </div>
        </div>
        <div className="op-suggest-list">
          {report.suggestions.length === 0 && (
            <p className="op-empty">아직 도출된 개선 제안이 없어요.</p>
          )}
          {report.suggestions.map((suggestion, index) => {
            const selected = selectedOperationSuggestionTitle === suggestion.title

            return (
              <div className={selected ? 'op-suggest selected' : 'op-suggest'} key={`${suggestion.title}-${index}`}>
                <button
                  type="button"
                  className="op-suggest-select"
                  onClick={() => onSelectOperationSuggestion?.(suggestion.title)}
                >
                  <b>{suggestion.title}</b>
                  <p>{suggestion.body}</p>
                </button>
                {suggestion.link && (
                  <button type="button" className="op-suggest-link" onClick={() => go?.(suggestion.link)}>
                    {suggestion.linkLabel ?? 'SNS 홍보 초안으로'} <Icon name="arrow" size={14} />
                  </button>
                )}
              </div>
            )
          })}
        </div>
      </Card>

      {(detail || detailLoading) && (
        <div className="op-modal-backdrop" onClick={() => setDetail(null)} role="presentation">
          <div className="op-modal" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true">
            <div className="op-modal-head">
              <div>
                <h3>{detailLoading ? '기록 불러오는 중…' : detail?.title}</h3>
                {detail?.createdAt && <p>{formatDateLabel(detail.createdAt)} 저장</p>}
              </div>
              <button type="button" className="op-icon-btn" onClick={() => setDetail(null)} aria-label="닫기">
                <Icon name="close" size={18} />
              </button>
            </div>
            {detail && !detailLoading && (
              <div className="op-modal-body">
                {detail.report.kpis.length > 0 && (
                  <div className="op-kpi-grid">
                    {detail.report.kpis.map((kpi, index) => (
                      <div className="op-kpi" key={`${kpi.label}-${index}`}>
                        <span className="op-kpi-label">{kpi.label}</span>
                        <strong className="op-kpi-value">{kpi.value}</strong>
                        {kpi.delta && (
                          <span className={`op-kpi-delta ${kpi.good === true ? 'good' : kpi.good === false ? 'bad' : ''}`}>
                            {kpi.delta}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {detail.report.products.length > 0 && (
                  <div className="op-section">
                    <div className="op-section-title">상품별 판매 비중</div>
                    {detail.report.products.map((product, index) => (
                      <div className="op-bar" key={`${product.name}-${index}`}>
                        <div className="op-bar-head">
                          <span>{product.name}</span>
                          <span>{product.pct}%</span>
                        </div>
                        <div className="op-bar-track">
                          <div className="op-bar-fill" style={{ width: `${Math.min(100, Math.max(0, product.pct))}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {detail.report.notes && (
                  <div className="op-section op-notes">
                    <div className="op-section-title">운영 메모</div>
                    <p>{detail.report.notes}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
