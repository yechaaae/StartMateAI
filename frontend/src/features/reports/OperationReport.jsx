import { Card } from '../../shared/components/Card'

const updateKpiValue = (setData, index, key, nextValue) => {
  setData((current) => ({
    ...current,
    kpis: current.kpis.map((item, itemIndex) => (
      itemIndex === index
        ? [
            item[0],
            key === 'value' ? nextValue : item[1],
            key === 'delta' ? nextValue : item[2],
            item[3],
          ]
        : item
    )),
  }))
}

const updateProductRatio = (setData, index, nextValue) => {
  const ratio = Number(nextValue)

  setData((current) => ({
    ...current,
    products: current.products.map((item, itemIndex) => (
      itemIndex === index ? [item[0], Number.isNaN(ratio) ? 0 : ratio] : item
    )),
  }))
}

const updateChannelValue = (setData, index, nextValue) => {
  setData((current) => ({
    ...current,
    channels: current.channels.map((item, itemIndex) => (
      itemIndex === index ? [item[0], nextValue] : item
    )),
  }))
}

export const OperationReport = ({
  data,
  setData,
  go,
  selectedOperationSuggestionTitle,
  onSelectOperationSuggestion,
}) => (
  <div className="report-stack">
    <Card>
      <div className="card-head">
        <h3>운영 입력 정보</h3>
        <button type="button">실데이터 기준</button>
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
            placeholder="예: 인스타 광고 효율이 이번 주 급감했고, 쿠키 단품 매출은 유지 중"
            rows="3"
          />
        </label>
      </div>

      <div className="kpi-grid operation-kpi-grid">
        {data.kpis.map(([label, value, delta, good], index) => (
          <div key={label}>
            <small>{label}</small>
            <input
              className="operation-mini-input"
              value={value}
              onChange={(event) => updateKpiValue(setData, index, 'value', event.target.value)}
            />
            <input
              className="operation-mini-input"
              value={delta}
              onChange={(event) => updateKpiValue(setData, index, 'delta', event.target.value)}
            />
            <em className={good === false ? 'bad' : good ? 'good' : ''}>{delta}</em>
          </div>
        ))}
      </div>

      <div className="operation-block">
        <small>상품 비중</small>
        {data.products.map(([name, pct], index) => (
          <div className="bar-row operation-edit-row" key={name}>
            <span>{name}</span>
            <input
              type="number"
              min="0"
              max="100"
              value={pct}
              onChange={(event) => updateProductRatio(setData, index, event.target.value)}
            />
            <i><em style={{ width: `${pct}%`, background: 'var(--a-operation)' }} /></i>
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
      {data.suggestions.map(([title, body, link]) => {
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
            {link && <button onClick={() => go(link)}>SNS 홍보 자동화로 이동</button>}
          </div>
        )
      })}
    </Card>
  </div>
)
