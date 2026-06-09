import { agents } from '../../shared/data/agents'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { BrandMark } from '../../shared/components/BrandMark'
import { Icon } from '../../shared/components/Icon'

export const Landing = ({ go }) => (
  <main className="landing">
    <header>
      <div><BrandMark /><b>StartMate AI</b></div>
      <button onClick={() => go('home')}>워크스페이스로 이동</button>
    </header>
    <section>
      <div className="hero-badge"><Icon name="sparkle" size={15} /> 7명의 AI Agent가 함께하는 창업 워크스페이스</div>
      <h1>창업 프로필 하나로<br /><span>아이디어부터 홍보까지</span> AI가 함께해요</h1>
      <p>아이템 추천, 수익 시뮬레이션, 지원사업, 사업계획서, 운영 피드백, SNS 홍보를 하나의 흐름으로 연결합니다.</p>
      <div className="hero-actions">
        <button onClick={() => go('onboarding')}>창업 시작하기 <Icon name="arrow" size={18} /></button>
        <button onClick={() => go('discuss')}>AI와 먼저 토론하기</button>
      </div>
      <div className="agent-strip">{Object.entries(agents).map(([id, a]) => <span key={id}><AgentAvatar id={id} size={26} />{a.name}</span>)}</div>
    </section>
  </main>
)
