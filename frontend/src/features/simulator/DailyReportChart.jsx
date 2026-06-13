import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'

const formatWon = (value) => `${Math.round(Number(value || 0)).toLocaleString('ko-KR')}원`
const formatManwon = (value) => `${Math.round(Number(value || 0) / 10000).toLocaleString('ko-KR')}만`

const LineChart = ({ metrics }) => {
  const width = 820
  const height = 190
  const pad = 10
  const max = Math.max(...metrics.map((item) => item.revenue), 1)
  const points = metrics.map((item, index) => {
    const x = pad + (index / (metrics.length - 1)) * (width - pad * 2)
    const y = height - pad - (item.revenue / max) * (height - pad * 2)
    return [x, y]
  })
  const path = points.map(([x, y], index) => `${index ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
  const area = `${path} L ${points[points.length - 1][0].toFixed(1)} ${height - pad} L ${pad} ${height - pad} Z`
  const marks = [0, 6, 14, 29].map((index) => points[index]).filter(Boolean)

  return (
    <svg className="sim-line-chart" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id="simRevenueFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--a-finance)" stopOpacity="0.16" />
          <stop offset="1" stopColor="var(--a-finance)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#simRevenueFill)" />
      <path d={path} fill="none" stroke="var(--a-finance)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      {marks.map(([x, y], index) => <circle key={index} cx={x} cy={y} r="6" fill="#fff" stroke="var(--a-finance)" strokeWidth="3" />)}
    </svg>
  )
}

export const DailyReportChart = ({ data, assumption, location, onBack, onLocationEdit, onSave }) => {
  if (!data) return null

  const snapshots = [0, 6, 14, 29].map((index) => data.metrics[index]).filter(Boolean)
  const riskTags = [
    data.summary.cashShortageRisk === '높음' ? '자금 부족 가능성' : '자금 안정',
    assumption?.monthlyRent > 2500000 ? '임대료 부담' : '임대료 적정',
    assumption?.variableCostRate > 0.45 ? '비용률 관리 필요' : '비용률 양호',
  ]

  return (
    <section className="sim-step-panel step-in">
      <Card className="sim-location-summary">
        <div className="sim-location-icon"><Icon name="pin" size={20} /></div>
        <div>
          <b>{location?.address || '선택한 위치'}</b>
          <span>첫 30일 기준 · 예상 월세 {formatWon(assumption?.monthlyRent)}</span>
        </div>
        <button onClick={onLocationEdit}>위치 다시 선택</button>
      </Card>

      <div className="sim-kpi-grid">
        <Card><small>예상 매출</small><b>{formatWon(data.summary.totalRevenue)}</b></Card>
        <Card><small>예상 비용</small><b>{formatWon(data.summary.totalCost)}</b></Card>
        <Card><small>예상 손익</small><b className={data.summary.totalProfit >= 0 ? 'good' : 'bad'}>{formatWon(data.summary.totalProfit)}</b></Card>
        <Card><small>손익분기</small><b>{data.summary.bepDay ? `Day ${data.summary.bepDay}` : '미달'}</b></Card>
      </div>

      <Card className="sim-result-card">
        <div className="sim-result-head">
          <div>
            <h2>첫 30일 흐름</h2>
            <p>입력한 위치와 간단한 비용 가정을 기준으로 일별 매출 흐름을 가볍게 추정했습니다.</p>
          </div>
          <span className={data.summary.bepDay ? 'good' : 'warn'}>
            {data.summary.bepDay ? `손익분기 ${data.summary.bepDay}일차` : '30일 내 손익분기 미달'}
          </span>
        </div>

        <LineChart metrics={data.metrics} />

        <div className="sim-snapshot-grid">
          {snapshots.map((item) => (
            <div key={item.day} className={item.day === 30 ? 'highlight' : ''}>
              <span>Day {item.day}</span>
              <b>{formatManwon(item.revenue)}</b>
              <small>판매/이용 {item.orders}건 · 누적 {formatManwon(item.cumulativeProfit)}</small>
            </div>
          ))}
        </div>

        <div className="sim-risk-row">
          <div>
            <span>체크 포인트</span>
            {riskTags.map((tag) => <b key={tag}>{tag}</b>)}
          </div>
          <small>빠른 비교용 추정치라 실제 매출과 차이가 있을 수 있어요</small>
        </div>
      </Card>

      <div className="sim-actions">
        <button className="sim-secondary-btn" onClick={onBack}>
          <Icon name="arrow" size={16} /> 가정 다시 조정
        </button>
        <button className="sim-primary-btn" onClick={onSave}>
          결과 저장 <Icon name="arrow" size={17} />
        </button>
      </div>
    </section>
  )
}
