import { agents } from '../../shared/data/agents'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { BrandMark } from '../../shared/components/BrandMark'
import { Icon } from '../../shared/components/Icon'

export const Landing = ({ go, user, onLogout }) => (
  <main className="landing">
    <header>
      <div><BrandMark /><b>StartMate AI</b></div>
      <nav className="landing-nav">
        {user ? (
          <>
            <button type="button" onClick={() => go('home')}>작업공간</button>
            <button type="button" onClick={onLogout}>로그아웃</button>
          </>
        ) : (
          <>
            <button type="button" onClick={() => go('login')}>로그인</button>
            <button type="button" className="nav-primary" onClick={() => go('signup')}>회원가입</button>
          </>
        )}
      </nav>
    </header>

    <section>
      <div className="hero-badge"><Icon name="sparkle" size={15} /> 창업 준비를 한 흐름으로 정리하는 AI 작업공간</div>
      <h1>아이디어부터 정책 추천까지<br /><span>창업 준비를 함께 정리해요</span></h1>
      <p>
        StartMate AI는 창업 프로필을 바탕으로 아이템 추천, 시뮬레이션,
        지원사업 탐색, 사업계획서 초안까지 이어주는 예비창업자용 도구입니다.
      </p>
      <div className="hero-actions">
        <button type="button" onClick={() => go(user ? 'home' : 'signup')}>
          {user ? '작업공간으로 이동' : '무료로 시작하기'} <Icon name="arrow" size={18} />
        </button>
        <button type="button" onClick={() => go(user ? 'discuss' : 'login')}>
          {user ? 'AI와 먼저 논의하기' : '로그인하고 이어가기'}
        </button>
      </div>
      <div className="agent-strip">
        {Object.entries(agents).map(([id, agent]) => (
          <span key={id}><AgentAvatar id={id} size={26} />{agent.label}</span>
        ))}
      </div>
    </section>
  </main>
)
