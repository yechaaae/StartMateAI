import { agents } from '../../shared/data/agents'
import { features, featureOrder } from '../../shared/data/features'
import { profile } from '../../shared/data/profile'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'

const profileItems = [
  ['전공', profile.major],
  ['경력', profile.career],
  ['관심 분야', profile.interest],
  ['거주 지역', profile.region],
  ['초기 자금', profile.capital],
  ['팀 구성', profile.team],
]

const fitSummary = [
  ['강점', profile.strength, 'good'],
  ['리스크', profile.weakness, 'warn'],
  ['추천', profile.recommend, 'brand'],
]

const fitBars = [
  ['보유 역량 (디자인·SNS)', 86, 'var(--brand)'],
  ['실행 가능성', 74, 'var(--brand)'],
  ['자금 수준', 42, 'var(--warn)'],
  ['지역 기반 기회', 80, 'var(--ok)'],
]

const ScoreGauge = ({ score }) => {
  const radius = 56
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - score / 100)

  return (
    <div className="score-gauge" aria-label={`창업 적합도 ${score}점`}>
      <svg width="152" height="152" viewBox="0 0 152 152">
        <defs>
          <linearGradient id="fitGaugeGradient" x1="22" x2="130" y1="24" y2="130" gradientUnits="userSpaceOnUse">
            <stop stopColor="#6f86f6" />
            <stop offset="1" stopColor="var(--brand-strong)" />
          </linearGradient>
        </defs>
        <circle className="score-gauge-track" cx="76" cy="76" r={radius} />
        <circle
          className="score-gauge-value"
          cx="76"
          cy="76"
          r={radius}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="score-gauge-label">
        <strong>{score}</strong>
        <span>/ 100</span>
      </div>
    </div>
  )
}

export const HomePage = ({ go, workspace }) => (
  <main className="page workspace-page">
    <div className="page-title">
      <div>
        <h1>{workspace.name}</h1>
        <p>모든 AI 기능은 이 창업 프로필과 저장 결과를 참고합니다.</p>
      </div>
    </div>

    <div className="workspace-summary-grid">
      <Card className="profile-summary-card">
        <div className="summary-card-head">
          <div className="summary-title">
            <span><Icon name="user" size={17} /></span>
            <h3>입력한 프로필</h3>
          </div>
          <button onClick={() => go('onboarding')}>
            <Icon name="edit" size={14} />
            수정
          </button>
        </div>

        <div className="profile-summary-grid">
          {profileItems.map(([label, value]) => (
            <div key={label}>
              <small>{label}</small>
              <b>{value}</b>
            </div>
          ))}
        </div>

        <div className="profile-tag-section">
          <small>선호 · 강점</small>
          <div className="profile-tags">
            {profile.tags.map((tag) => <span key={tag}>{tag}</span>)}
          </div>
        </div>
      </Card>

      <Card className="fit-summary-card">
        <div className="summary-card-head">
          <div className="summary-title">
            <span><Icon name="target" size={17} /></span>
            <h3>AI 창업 적합도 진단</h3>
          </div>
          <button>
            <Icon name="refresh" size={14} />
            재진단
          </button>
        </div>

        <div className="fit-score-row">
          <ScoreGauge score={workspace.fit} />
          <div className="fit-summary-list">
            {fitSummary.map(([label, value, tone]) => (
              <div key={label}>
                <span className={tone}>{label}</span>
                <b>{label === '추천' ? workspace.recommend : value}</b>
              </div>
            ))}
          </div>
        </div>

        <div className="fit-bar-list">
          {fitBars.map(([label, value, color]) => (
            <div className="fit-bar-item" key={label}>
              <div>
                <span>{label}</span>
                <b style={{ color }}>{value}</b>
              </div>
              <i><em style={{ width: `${value}%`, background: color }} /></i>
            </div>
          ))}
        </div>
      </Card>
    </div>

    <div className="feature-section-head">
      <span>AI 기능</span>
      <b>{featureOrder.length}</b>
      <i />
    </div>
    <div className="feature-grid">{featureOrder.map((id) => <FeatureCard key={id} id={id} go={go} />)}</div>
  </main>
)

export const FeatureCard = ({ id, go }) => {
  const f = features[id]
  const a = agents[f.agent]

  return (
    <button className="feature-card" onClick={() => go(id)} style={{ '--accent': a.color, '--tint': a.tint }}>
      <span><Icon name={f.icon} /></span>
      <small>{f.flag}</small>
      <h3>{f.title}</h3>
      <p>{f.card}</p>
      <b>기능 사용하기</b>
    </button>
  )
}
