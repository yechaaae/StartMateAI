import { useEffect, useState } from 'react'
import { agents } from '../../shared/data/agents'
import { features, featureOrder } from '../../shared/data/features'
import { Icon } from '../../shared/components/Icon'
import { StartMateLogo } from '../../shared/components/StartMateLogo'

const landingSpecialists = [
  { id: 'profile', name: '창업 프로필 전문가', icon: 'user', description: '경력·자금·역량을 분석해 창업 적합도와 강·약점을 진단해요.' },
  { id: 'idea', name: '창업 아이템 전문가', icon: 'bulb', description: '프로필과 상권 데이터로 나에게 맞는 창업 아이템을 추천하고 다듬어요.' },
  { id: 'finance', name: '창업 자금 전문가', icon: 'coins', description: '초기비용·손익분기·30일 손익을 시뮬레이션해 자금 계획을 세워요.' },
  { id: 'policy', name: '지원사업 전문가', icon: 'doc', description: '조건에 맞는 정부·지자체 지원사업을 찾아 신청 전략을 알려줘요.' },
  { id: 'operation', name: '매장 운영 전문가', icon: 'pulse', description: '매출·지출·고객 반응을 분석해 운영 개선 포인트를 제안해요.' },
  { id: 'marketing', name: '홍보 마케팅 전문가', icon: 'megaphone', description: '타깃에 맞는 SNS 콘텐츠와 홍보 문구를 만들고 바로 게시해요.' },
  { id: 'commercial_area', name: '상권 분석 전문가', icon: 'pin', description: '로드뷰·유동인구로 후보 상권을 비교하고 입지를 평가해요.' },
  { id: 'legal', name: '창업 법률 전문가', icon: 'scales', description: '인허가·계약·세무 등 창업에 필요한 법률 리스크를 점검해요.' },
]

const teamInfo = {
  teamName: '구미청년들',
  hackathon: 'SSAFY X KAKAO TECH BOOTCAMP AI HACKATHON',
}

const FeaturePreview = ({ id, feature }) => (
  <div className={`feature-preview feature-preview-${id}`} aria-hidden="true">
    <div className="feature-preview-window">
      <div className="feature-preview-toolbar">
        <span />
        <span />
        <span />
      </div>
      <div className="feature-preview-content">
        <div className="feature-preview-heading">
          <span className="feature-preview-icon"><Icon name={feature.icon} size={19} /></span>
          <div>
            <b>{feature.title}</b>
            <small>StartMate AI 분석 결과</small>
          </div>
        </div>
        <div className="feature-preview-metrics">
          <span><small>추천 점수</small><b>86</b></span>
          <span><small>예상 가능성</small><b>74%</b></span>
          <span><small>준비 단계</small><b>3/5</b></span>
        </div>
        <div className="feature-preview-chart">
          {[52, 68, 46, 82, 72, 94].map((height, index) => (
            <span key={index} style={{ height: `${height}%` }} />
          ))}
        </div>
        <div className="feature-preview-rows">
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  </div>
)

const FeatureCarousel = ({ openFeature }) => {
  const [activeIndex, setActiveIndex] = useState(0)
  const [isPaused, setIsPaused] = useState(false)
  const previous = () => setActiveIndex((current) => (current - 1 + featureOrder.length) % featureOrder.length)
  const next = () => setActiveIndex((current) => (current + 1) % featureOrder.length)

  useEffect(() => {
    if (isPaused) return undefined
    const timer = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % featureOrder.length)
    }, 2000)
    return () => window.clearInterval(timer)
  }, [activeIndex, isPaused])

  return (
    <div
      className="feature-carousel"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      onFocus={() => setIsPaused(true)}
      onBlur={() => setIsPaused(false)}
    >
      <div className="feature-carousel-viewport">
        <div className="feature-carousel-track" style={{ transform: `translateX(-${activeIndex * 100}%)` }}>
          {featureOrder.map((id, index) => {
            const feature = features[id]
            const agent = agents[feature.agent]
            return (
              <article
                className="feature-carousel-slide"
                key={id}
                aria-hidden={index !== activeIndex}
                style={{ '--agent-color': agent.color, '--agent-tint': agent.tint }}
              >
                <div className="feature-carousel-copy">
                  <div className="feature-carousel-meta">
                    <span>{String(index + 1).padStart(2, '0')}</span>
                    <i />
                  </div>
                  <h3>{feature.title}</h3>
                  <p>{feature.sub}</p>
                  <button type="button" onClick={() => openFeature(id)} tabIndex={index === activeIndex ? 0 : -1}>
                    기능 살펴보기 <Icon name="arrow" size={16} />
                  </button>
                </div>
                <FeaturePreview id={id} feature={feature} />
              </article>
            )
          })}
        </div>
      </div>
      <button className="feature-carousel-arrow previous" type="button" aria-label="이전 기능" onClick={previous}>
        <Icon name="chevron" size={21} />
      </button>
      <button className="feature-carousel-arrow next" type="button" aria-label="다음 기능" onClick={next}>
        <Icon name="chevron" size={21} />
      </button>
      <div className="feature-carousel-status" aria-label={`${activeIndex + 1}번째 기능 표시 중`}>
        {featureOrder.map((id, index) => (
          <span
            className={index === activeIndex ? 'on' : ''}
            key={id}
            style={{
              '--agent-color': agents[features[id].agent].color,
              '--agent-tint': agents[features[id].agent].tint,
            }}
          >
            <i />
            {index === activeIndex && <b>{features[id].title}</b>}
          </span>
        ))}
      </div>
    </div>
  )
}

export const Landing = ({ go, user, onLogout }) => {
  const start = () => go(user ? 'home' : 'signup')
  const openFeature = (id) => go(user ? id : 'signup')
  const specialistEntries = landingSpecialists

  return (
    <main className="landing">
      <header className="landing-header">
        <div className="landing-header-inner">
          <button className="landing-brand" type="button" onClick={() => go('landing')}>
            <StartMateLogo size={36} />
            <b>StartMate AI</b>
          </button>
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
        </div>
      </header>

      <section className="landing-hero landing-snap">
        <div className="hero-badge">
          <Icon name="sparkle" size={15} />
          분야별 AI 전문가가 함께하는 창업 워크스페이스
        </div>
        <h1>
          혼자 고민하던 창업,<br />
          <span>전담 AI 전문가 팀</span>과 함께
        </h1>
        <p>
          프로필 진단부터 아이템, 자금, 상권, 지원사업과 홍보까지
          분야별 AI 전문가가 창업 준비의 모든 단계를 함께 정리합니다.
        </p>
        <div className="hero-actions">
          <button type="button" onClick={start}>
            {user ? '작업공간으로 이동' : '무료로 시작하기'}
            <Icon name="arrow" size={18} />
          </button>
          <button type="button" onClick={() => go(user ? 'discuss' : 'login')}>
            <Icon name="discuss" size={18} />
            {user ? 'AI 전문가와 상담하기' : '로그인하고 이어가기'}
          </button>
        </div>
      </section>

      <section className="landing-team landing-snap">
        <div className="landing-section-heading">
          <span>당신의 창업 전담팀</span>
          <h2>9명의 AI 전문가를 만나보세요</h2>
          <p>각 분야의 전문 Agent가 내 창업 데이터를 함께 보고 협업해요.</p>
        </div>

        <div className="manager-card">
          <div className="manager-profile">
            <div className="manager-avatar"><Icon name="compass" size={30} /></div>
            <div>
              <div className="manager-title">
                <h3>창업 총괄 매니저</h3>
                <span>팀 리더</span>
              </div>
              <p>전체 창업 여정을 설계하고 전문가들의 분석을 종합해 다음 할 일을 안내해요.</p>
            </div>
          </div>
          <div className="manager-specialists">
            <span>8명의 전문가를 조율합니다</span>
            <div>
              {specialistEntries.map((specialist) => (
                <span className="manager-specialist-avatar" key={specialist.id} title={specialist.name}>
                  <span style={{ background: agents[specialist.id].color }}>
                    <Icon name={specialist.icon} size={19} />
                  </span>
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="landing-agent-grid">
          {specialistEntries.map((specialist) => {
            const agent = agents[specialist.id]
            return (
            <article className="landing-agent-card" key={specialist.id} style={{ '--agent-color': agent.color, '--agent-tint': agent.tint }}>
              <span className="landing-agent-icon"><Icon name={specialist.icon} size={24} /></span>
              <h3>{specialist.name}</h3>
              <p>{specialist.description}</p>
            </article>
            )
          })}
        </div>
      </section>

      <section className="landing-features landing-snap">
        <div className="landing-section-heading">
          <span>WHAT YOU CAN DO</span>
          <h2>전문가와 함께 쓰는 6가지 AI 기능</h2>
          <p>각 기능을 자동으로 넘기며 미리 보여드려요.</p>
        </div>
        <FeatureCarousel openFeature={openFeature} />
      </section>

      <section className="landing-final landing-snap">
        <div className="landing-closing">
          <div>
            <h2>오늘, 창업 준비를 시작해요</h2>
            <p>프로필을 입력하면 AI 전문가 팀이 나에게 필요한 창업 데이터를 정리하기 시작합니다.</p>
            <button type="button" onClick={start}>
              {user ? '작업공간으로 이동' : '무료로 시작하기'}
              <Icon name="arrow" size={18} />
            </button>
          </div>
        </div>

        <footer className="landing-footer">
          <div className="landing-footer-brand">
            <StartMateLogo size={34} />
            <div>
              <b>StartMate AI</b>
              <span>분야별 AI 전문가가 함께하는 창업 워크스페이스</span>
            </div>
          </div>

          <div className="landing-footer-bottom">
            <span>{teamInfo.hackathon} · {teamInfo.teamName}</span>
            <span>© 2026 {teamInfo.teamName}. StartMate AI.</span>
          </div>
        </footer>
      </section>
    </main>
  )
}
