import { useEffect, useMemo, useState } from 'react'
import { savedResultApi } from '../../shared/api/client'
import { AgentBadge } from '../../shared/components/AgentBadge'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'

const FEATURE_META = {
  item: { label: '창업 아이템', agent: 'idea' },
  simulator: { label: '시뮬레이션', agent: 'finance' },
  support: { label: '지원사업', agent: 'policy' },
  plan: { label: '사업계획서', agent: 'plan' },
  operation: { label: '운영 피드백', agent: 'operation' },
  sns: { label: 'SNS 홍보', agent: 'marketing' },
}

const formatDate = (value) => {
  if (!value) return ''
  return value.replace('T', ' ').slice(0, 16)
}

const renderPreview = (detail) => {
  const payload = detail?.payload?.reportData ?? detail?.payload ?? {}
  const feature = detail?.sourceFeature

  if (feature === 'item') {
    return (
      <div className="saved-preview-stack">
        <section className="saved-preview-section">
          <h4>추천 아이템</h4>
          <ul>
            {(payload.items ?? []).slice(0, 4).map((item) => (
              <li key={item.rank ?? item.title}>
                <b>{item.title}</b>
                <span>{item.score ? `${item.score}점` : item.reason}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    )
  }

  if (feature === 'simulator') {
    const report = payload.report ?? {}
    const summary = report.summary ?? {}
    return (
      <div className="saved-preview-stack">
        <section className="saved-preview-metrics">
          <div><small>총매출</small><b>{summary.totalRevenue?.toLocaleString?.() ?? '-'}</b></div>
          <div><small>총비용</small><b>{summary.totalCost?.toLocaleString?.() ?? '-'}</b></div>
          <div><small>예상순이익</small><b>{summary.totalProfit?.toLocaleString?.() ?? '-'}</b></div>
          <div><small>BEP</small><b>{summary.bepDay ? `${summary.bepDay}일` : '-'}</b></div>
        </section>
      </div>
    )
  }

  if (feature === 'support') {
    return (
      <section className="saved-preview-section">
        <h4>추천 지원사업</h4>
        <ul>
          {(payload.list ?? []).slice(0, 4).map((item) => (
            <li key={item.title}>
              <b>{item.title}</b>
              <span>{item.region} · {item.score}점</span>
            </li>
          ))}
        </ul>
      </section>
    )
  }

  if (feature === 'plan') {
    return (
      <section className="saved-preview-section">
        <h4>사업계획서 섹션</h4>
        <ul>
          {(payload.sections ?? []).slice(0, 5).map(([title, body]) => (
            <li key={title}>
              <b>{title}</b>
              <span>{body}</span>
            </li>
          ))}
        </ul>
      </section>
    )
  }

  if (feature === 'operation') {
    return (
      <div className="saved-preview-stack">
        <section className="saved-preview-metrics">
          {(payload.kpis ?? []).slice(0, 4).map(([label, value, delta]) => (
            <div key={label}>
              <small>{label}</small>
              <b>{value}</b>
              <span>{delta}</span>
            </div>
          ))}
        </section>
        <section className="saved-preview-section">
          <h4>개선 제안</h4>
          <ul>
            {(payload.suggestions ?? []).slice(0, 4).map(([title, body]) => (
              <li key={title}>
                <b>{title}</b>
                <span>{body}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    )
  }

  if (feature === 'sns') {
    return (
      <section className="saved-preview-section">
        <h4>{payload.topic ?? 'SNS 초안'}</h4>
        <p>{payload.hook}</p>
        <div className="saved-tag-row">
          {(payload.tags ?? []).slice(0, 8).map((tag) => <span key={tag}>{tag}</span>)}
        </div>
      </section>
    )
  }

  return (
    <pre className="saved-json-preview">
      {JSON.stringify(detail?.payload ?? {}, null, 2)}
    </pre>
  )
}

export const SavedPage = ({ go }) => {
  const [results, setResults] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState('')
  const [modalOpen, setModalOpen] = useState(false)

  useEffect(() => {
    let active = true

    const load = async () => {
      try {
        setLoading(true)
        setError('')
        const response = await savedResultApi.list()
        if (!active) return
        setResults(response.results ?? [])
      } catch (nextError) {
        if (!active) return
        setError(nextError.message ?? '저장한 결과를 불러오지 못했습니다.')
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!modalOpen) return undefined

    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setModalOpen(false)
      }
    }

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', handleEscape)

    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleEscape)
    }
  }, [modalOpen])

  const openDetail = async (savedResultId) => {
    try {
      setError('')
      setSelectedId(savedResultId)
      setDetailLoading(true)
      setModalOpen(true)
      const nextDetail = await savedResultApi.get(savedResultId)
      setDetail(nextDetail)
    } catch (nextError) {
      setModalOpen(false)
      setError(nextError.message ?? '저장한 리포트 상세를 불러오지 못했습니다.')
    } finally {
      setDetailLoading(false)
    }
  }

  const closeModal = () => {
    setModalOpen(false)
  }

  const selectedMeta = useMemo(
    () => FEATURE_META[detail?.sourceFeature] ?? { label: detail?.sourceFeature ?? '기타', agent: 'profile' },
    [detail?.sourceFeature],
  )

  return (
    <main className="page saved-page">
      <div className="page-title saved-page-title">
        <div>
          <h1>저장한 결과</h1>
          <p>AI와 함께 만든 초안, 추천, 피드백을 모아보고 필요할 때 다시 꺼내서 이어갈 수 있어요.</p>
        </div>
      </div>

      {!!error && <div className="chat-error-banner">{error}</div>}

      {loading && <div className="chat-loading">저장한 리포트를 불러오는 중입니다.</div>}

      {!loading && !results.length && (
        <Card className="saved-empty-card">
          <div className="saved-empty-icon">
            <Icon name="bookmark" size={22} />
          </div>
          <h3>아직 저장한 리포트가 없어요</h3>
          <p>기능 페이지에서 리포트를 저장하면 이곳에서 다시 열어볼 수 있습니다.</p>
        </Card>
      )}

      {!!results.length && (
        <section className="saved-gallery">
          {results.map((result) => {
            const meta = FEATURE_META[result.sourceFeature] ?? { label: result.sourceFeature, agent: 'profile' }
            const active = result.id === selectedId && modalOpen

            return (
              <button
                key={result.id}
                type="button"
                className={active ? 'saved-card-button active' : 'saved-card-button'}
                onClick={() => openDetail(result.id)}
              >
                <Card className="saved-card">
                  <div className="saved-card-top">
                    <span className="saved-feature-chip">{meta.label}</span>
                    <AgentBadge id={meta.agent} />
                  </div>
                  <div className="saved-card-copy">
                    <h3>{result.title}</h3>
                    <p>{result.summary || '요약이 없는 리포트입니다.'}</p>
                  </div>
                  <div className="saved-card-bottom">
                    <span>{formatDate(result.createdAt)}</span>
                    <span className="saved-card-link">
                      자세히 보기 <Icon name="arrow" size={14} />
                    </span>
                  </div>
                </Card>
              </button>
            )
          })}
        </section>
      )}

      {modalOpen && (
        <div className="saved-modal-backdrop" onClick={closeModal}>
          <div
            className="saved-modal-shell"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <button type="button" className="saved-modal-close" onClick={closeModal} aria-label="닫기">
              ×
            </button>

            {detailLoading && (
              <div className="saved-modal-loading">
                <div className="chat-loading">리포트 상세를 불러오는 중입니다.</div>
              </div>
            )}

            {!detailLoading && detail && (
              <Card className="saved-detail-card">
                <div className="saved-detail-head">
                  <div className="saved-detail-copy">
                    <div className="saved-detail-badges">
                      <span className="saved-feature-chip">{selectedMeta.label}</span>
                      <AgentBadge id={selectedMeta.agent} />
                      <span className="saved-detail-date">{formatDate(detail.createdAt)}</span>
                    </div>
                    <h2>{detail.title}</h2>
                    <p>{detail.summary || '저장 당시 요약이 없습니다.'}</p>
                  </div>
                </div>

                <div className="saved-detail-toolbar">
                  <button type="button" className="secondary-chip" onClick={() => go(detail.sourceFeature)}>
                    <Icon name="arrow" size={15} />
                    <span>원본 기능으로 이동</span>
                  </button>
                </div>

                {renderPreview(detail)}
              </Card>
            )}
          </div>
        </div>
      )}
    </main>
  )
}
