import { agents } from '../../shared/data/agents'
import { features, featureOrder } from '../../shared/data/features'
import { profile } from '../../shared/data/profile'
import { AgentBadge } from '../../shared/components/AgentBadge'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'

export const HomePage = ({ go, workspace }) => (
  <main className="page narrow">
    <div className="page-title">
      <div><h1>{workspace.emoji} {workspace.name}</h1><p>모든 AI 기능은 이 창업 프로필과 저장 결과를 참고합니다.</p></div>
      <AgentBadge id="profile" />
    </div>
    <div className="two-col">
      <Card>
        <div className="card-head"><h3>입력한 프로필</h3><button onClick={() => go('onboarding')}>수정</button></div>
        <div className="profile-grid">
          {[
            ['전공', profile.major],
            ['경력', profile.career],
            ['관심 분야', profile.interest],
            ['거주 지역', profile.region],
            ['초기 자금', profile.capital],
            ['팀 구성', profile.team],
          ].map(([k, v]) => <div key={k}><small>{k}</small><b>{v}</b></div>)}
        </div>
        <div className="tags">{profile.tags.map((t) => <span key={t}>{t}</span>)}</div>
      </Card>
      <Card>
        <div className="card-head"><h3>AI 창업 적합도 진단</h3><button>재진단</button></div>
        <div className="fit-row"><strong>{workspace.fit}</strong><div><p><b>강점</b>{profile.strength}</p><p><b>리스크</b>{profile.weakness}</p><p><b>추천</b>{workspace.recommend}</p></div></div>
        {[
          ['보유 역량', 86, 'var(--brand)'],
          ['실행 가능성', 74, 'var(--brand)'],
          ['자금 여유', 42, 'var(--warn)'],
          ['지역 기회', 80, 'var(--ok)'],
        ].map(([label, value, color]) => <div className="bar-row" key={label}><span>{label}</span><b>{value}</b><i><em style={{ width: `${value}%`, background: color }} /></i></div>)}
      </Card>
    </div>
    <h2 className="section-label">AI 기능</h2>
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
