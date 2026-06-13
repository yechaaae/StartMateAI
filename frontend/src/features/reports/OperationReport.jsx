import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'
import { normalizeOperationReport } from './operationFeedbackLogic'

export const OperationReport = ({
  data,
  go,
  selectedOperationSuggestionTitle,
  onSelectOperationSuggestion,
  onRequestOperationFeedback,
  operationFeedbackSaving,
}) => {
  const report = normalizeOperationReport(data)

  return (
    <div className="report-stack">
      <Card className="op-card">
        <div className="card-head op-head">
          <div>
            <h3>운영 진단 리포트</h3>
            <p>{report.period ? `${report.period} 기준 · ` : ''}AI가 운영 지표를 분석한 결과예요.</p>
          </div>
        </div>

        {report.kpis.length > 0 && (
          <div className="op-kpi-grid">
            {report.kpis.map((kpi, index) => (
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

        {report.products.length > 0 && (
          <div className="op-section">
            <div className="op-section-title">상품별 판매 비중</div>
            {report.products.map((product, index) => (
              <div className="op-bar" key={`${product.name}-${index}`}>
                <div className="op-bar-head">
                  <span>{product.name}</span>
                  <span>{product.pct}%</span>
                </div>
                <div className="op-bar-track">
                  <div
                    className="op-bar-fill"
                    style={{ width: `${Math.min(100, Math.max(0, product.pct))}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

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

        {report.notes && (
          <div className="op-section op-notes">
            <div className="op-section-title">운영 메모</div>
            <p>{report.notes}</p>
          </div>
        )}

        {onRequestOperationFeedback && (
          <div className="op-submit">
            <button
              type="button"
              className="op-save-button"
              onClick={onRequestOperationFeedback}
              disabled={operationFeedbackSaving}
            >
              {operationFeedbackSaving ? '피드백 저장 중…' : '이 운영 피드백 저장'}
              {!operationFeedbackSaving && <Icon name="check" size={16} />}
            </button>
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
    </div>
  )
}
