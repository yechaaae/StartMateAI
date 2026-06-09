import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

const agents = {
  profile: { name: 'Profile Agent', label: '프로필 분석', icon: 'user', color: 'var(--a-profile)', tint: 'var(--a-profile-t)' },
  idea: { name: 'Idea Agent', label: '아이디어', icon: 'bulb', color: 'var(--a-idea)', tint: 'var(--a-idea-t)' },
  finance: { name: 'Finance Agent', label: '재무', icon: 'chart', color: 'var(--a-finance)', tint: 'var(--a-finance-t)' },
  policy: { name: 'Policy Agent', label: '정책', icon: 'doc', color: 'var(--a-policy)', tint: 'var(--a-policy-t)' },
  plan: { name: 'Plan Agent', label: '사업계획', icon: 'edit', color: 'var(--a-plan)', tint: 'var(--a-plan-t)' },
  operation: { name: 'Operation Agent', label: '운영', icon: 'pulse', color: 'var(--a-operation)', tint: 'var(--a-operation-t)' },
  marketing: { name: 'Marketing Agent', label: '마케팅', icon: 'megaphone', color: 'var(--a-marketing)', tint: 'var(--a-marketing-t)' },
}

const profile = {
  name: '김민서',
  role: '예비창업자',
  loc: '부산',
  major: '시각디자인',
  career: '카페 매니저 1년',
  interest: '브랜드, 로컬, 디저트',
  region: '부산 해운대구',
  capital: '100만 원',
  team: '1인 창업',
  tags: ['디자인 역량', 'SNS 운영 경험', '오프라인 중심'],
  fit: 78,
  strength: '디자인 감각과 SNS 운영 경험',
  weakness: '초기 자금 부족',
  recommend: '저비용 온라인 기반 창업',
}

const workspaces = [
  { id: 'cafe', emoji: '☕', name: '카페 브랜드 창업', desc: '해운대 구남로, 디저트 팝업', fit: 78, recommend: '저비용 온라인 기반 창업' },
  { id: 'goods', emoji: '🎁', name: '무재고 굿즈 커머스', desc: '온라인 POD 상품', fit: 71, recommend: '재고 없는 디자인 커머스' },
  { id: 'studio', emoji: '🎬', name: '콘텐츠 제작 스튜디오', desc: '부산 릴스, 숏폼 제작', fit: 74, recommend: 'SNS 콘텐츠 외주 스튜디오' },
]

const features = {
  item: {
    title: 'AI 창업 아이템 추천',
    sub: '프로필과 상권 조건을 바탕으로 현실적인 창업 아이템을 추천합니다.',
    card: '내 경험과 자금에 맞는 창업 아이템을 추천받아요.',
    flag: '아이디어가 없다면',
    agent: 'idea',
    icon: 'bulb',
  },
  simulator: {
    title: '창업 시뮬레이션',
    sub: '초기 자금, 판매가, 예상 주문 수로 매출과 수익을 예측합니다.',
    card: '초기 비용과 손익분기점을 미리 계산해요.',
    flag: '가능성을 보고 싶다면',
    agent: 'finance',
    icon: 'chart',
  },
  support: {
    title: '창업지원사업 추천',
    sub: '거주 지역, 희망 지역, 아이템에 맞는 지원사업을 찾아줍니다.',
    card: '신청 가능성이 높은 지원사업을 추천받아요.',
    flag: '지원금이 필요하다면',
    agent: 'policy',
    icon: 'doc',
  },
  plan: {
    title: '사업계획서 작성 보조',
    sub: '선택한 아이템과 지원사업 조건으로 사업계획서 초안을 작성합니다.',
    card: '공고 목적에 맞는 사업계획서 초안을 만들어요.',
    flag: '제출 문서가 필요하다면',
    agent: 'plan',
    icon: 'edit',
  },
  operation: {
    title: '운영 피드백',
    sub: '매출, 지출, 주문, 광고 전환율을 분석하고 개선 방향을 제안합니다.',
    card: '운영 데이터를 바탕으로 개선 포인트를 찾아요.',
    flag: '창업을 시작했다면',
    agent: 'operation',
    icon: 'pulse',
  },
  sns: {
    title: 'SNS 홍보 자동화',
    sub: '아이템과 운영 상황에 맞는 SNS 콘텐츠를 생성합니다.',
    card: '릴스, 카드뉴스, 해시태그를 빠르게 만들어요.',
    flag: '홍보가 필요하다면',
    agent: 'marketing',
    icon: 'megaphone',
  },
}

const featureOrder = ['item', 'simulator', 'support', 'plan', 'operation', 'sns']

const reportDefaults = {
  item: {
    location: '부산 해운대구 구남로',
    analysis: [
      ['유동 인구', '상위 12%'],
      ['카페 밀집도', '높음, 경쟁 강함'],
      ['평균 임대료', '월 48만 원/㎡'],
      ['주 연령대', '20-30대'],
    ],
    items: [
      { rank: 1, title: '로컬 카페 브랜드 키트', score: 92, reason: '카페 밀집 상권과 디자인 전공을 결합하기 좋습니다.' },
      { rank: 2, title: '디저트 예약 판매 팝업', score: 88, reason: '초기 고정비를 낮추고 SNS 운영 경험을 활용할 수 있습니다.' },
      { rank: 3, title: '무재고 굿즈 커머스', score: 81, reason: '자본 부담이 낮고 디자인 역량을 상품화하기 좋습니다.' },
    ],
  },
  simulator: {
    item: '수제 쿠키 온라인 판매',
    price: 7000,
    capital: 200,
    startOrders: 6,
    growthPct: 42,
    risks: ['생산 원가', '포장/배송', '재구매율'],
  },
  support: {
    list: [
      { title: '2026 청년 예비창업 패키지', score: 88, region: '전국', due: 'D-12', docs: ['사업계획서', '신분증', '졸업 증명서'] },
      { title: '부산 로컬크리에이터 육성', score: 81, region: '부산', due: 'D-23', docs: ['사업계획서', '지역 활용 증빙'] },
      { title: '1인 미디어 콘텐츠 창업 지원', score: 74, region: '전국', due: 'D-31', docs: ['포트폴리오', '사업계획서'] },
    ],
  },
  plan: {
    target: '청년 예비창업 패키지',
    sections: [
      ['1. 사업 개요', '부산 해운대 구남로 상권을 기반으로 로컬 카페와 디저트 브랜드를 위한 디자인 키트 및 온라인 홍보 패키지를 제공합니다.'],
      ['2. 문제 정의', '소규모 카페는 브랜딩과 SNS 운영 역량이 부족하지만, 전문 대행사를 이용하기에는 비용 부담이 큽니다.'],
      ['3. 해결 방안', '로고, 메뉴판, SNS 템플릿, 팝업 홍보물을 묶은 정액형 브랜딩 패키지를 제공합니다.'],
      ['4. 고객 및 시장', '1차 고객은 해운대 반경 1km 내 신규 카페와 디저트 팝업 운영자입니다.'],
      ['5. 수익 모델', '브랜드 키트 60만 원, SNS 운영 월 25만 원 구독형 상품으로 매출을 만듭니다.'],
    ],
  },
  operation: {
    kpis: [
      ['이번 달 매출', '2,780,000원', '+12%', true],
      ['지출', '1,410,000원', '+4%', null],
      ['주문 수', '842건', '+9%', true],
      ['광고 전환율', '1.8%', '-0.6%p', false],
    ],
    products: [
      ['아메리카노', 38],
      ['수제 라떼', 27],
      ['수제 쿠키', 21],
      ['굿즈', 14],
    ],
    suggestions: [
      ['광고 전환율 하락', '전환율이 떨어져 SNS 콘텐츠를 리뷰형으로 바꾸고 유입 키워드를 조정하는 것이 좋습니다.', 'sns'],
      ['수제 쿠키 성장', '수제 쿠키 비중이 빠르게 늘고 있어 팝업 세트 구성으로 객단가를 높일 수 있습니다.'],
    ],
  },
  sns: {
    topic: '수제 쿠키 팝업',
    hook: '해운대에서 제일 바삭한 쿠키, 주말에만 구워요.',
    beats: ['0-2초: 매장 입구와 로고 등장', '2-6초: 대표 메뉴 클로즈업', '6-11초: 제조 과정 슬로모션', '11-15초: 예약 안내와 위치 CTA'],
    tags: ['#해운대카페', '#구남로맛집', '#수제쿠키', '#부산디저트', '#주말팝업'],
    schedule: '토요일 오전 9시',
  },
}

const cloneReport = (id) => JSON.parse(JSON.stringify(reportDefaults[id]))

const Icon = ({ name, size = 20, stroke = 1.8 }) => {
  const paths = {
    discuss: <><path d="M21 11.5a8.5 8.5 0 0 1-12.2 7.7L3 21l1.8-5.3A8.5 8.5 0 1 1 21 11.5Z" /><path d="M8.5 11h.01M12 11h.01M15.5 11h.01" /></>,
    home: <><path d="M3 10.2 12 3l9 7.2" /><path d="M5 9.5V21h14V9.5" /><path d="M9.5 21v-6h5v6" /></>,
    user: <><circle cx="12" cy="8" r="3.4" /><path d="M5 20a7 7 0 0 1 14 0" /></>,
    bulb: <><path d="M9 18h6M10 21h4" /><path d="M12 3a6 6 0 0 0-3.6 10.8c.6.5 1 1.2 1.1 2h5c.1-.8.5-1.5 1.1-2A6 6 0 0 0 12 3Z" /></>,
    chart: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
    doc: <><path d="M7 3h7l4 4v14H7z" /><path d="M14 3v4h4M10 13h6M10 17h6" /></>,
    edit: <><path d="M5 19h14" /><path d="M14.5 5.5 18 9 8 19l-4 1 1-4z" /></>,
    pulse: <path d="M3 12h4l2-6 4 12 2-6h6" />,
    megaphone: <><path d="M4 10v4a1 1 0 0 0 1 1h2l8 4V5L7 9H5a1 1 0 0 0-1 1Z" /><path d="M18 8a4 4 0 0 1 0 8" /></>,
    bookmark: <path d="M6 3h12v18l-6-4-6 4z" />,
    plus: <path d="M12 5v14M5 12h14" />,
    arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
    send: <path d="M4 12 20 4l-7 16-2.5-6.5L4 12Z" />,
    check: <path d="M5 12.5 10 17l9-10" />,
    sparkle: <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" />,
    pin: <><path d="M12 21s7-6.3 7-11a7 7 0 0 0-14 0c0 4.7 7 11 7 11Z" /><circle cx="12" cy="10" r="2.5" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    refresh: <><path d="M3 12a9 9 0 0 1 15-6.7L21 8" /><path d="M21 3v5h-5" /><path d="M21 12a9 9 0 0 1-15 6.7L3 16" /><path d="M3 21v-5h5" /></>,
    chevron: <path d="M9 6l6 6-6 6" />,
    play: <path d="M7 4v16l13-8z" />,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>
}

const BrandMark = ({ size = 36 }) => <div className="brand-mark" style={{ width: size, height: size, fontSize: size * 0.5 }}>S</div>

const AgentAvatar = ({ id, size = 34, active = false }) => {
  const agent = agents[id] || agents.idea
  return (
    <div className={active ? 'agent-avatar active' : 'agent-avatar'} style={{ width: size, height: size, color: active ? '#fff' : agent.color, background: active ? agent.color : agent.tint }}>
      <Icon name={agent.icon} size={size * 0.56} />
    </div>
  )
}

const Card = ({ children, className = '' }) => <section className={`card ${className}`}>{children}</section>

const AgentBadge = ({ id }) => {
  const agent = agents[id]
  return (
    <div className="agent-badge">
      <span style={{ background: agent.color }}><Icon name={agent.icon} size={14} /></span>
      <b>{agent.name}</b>
    </div>
  )
}

const ChatRow = ({ message }) => {
  if (message.role === 'user') return <div className="chat-row user"><div>{message.text}</div></div>
  const agent = agents[message.agent] || agents.idea
  return (
    <div className="chat-row agent">
      <AgentAvatar id={message.agent} />
      <div className="chat-copy">
        <strong style={{ color: agent.color }}>{agent.name}</strong>
        <p>{message.text}</p>
      </div>
    </div>
  )
}

const TypingRow = ({ agent }) => (
  <div className="chat-row agent typing-row">
    <AgentAvatar id={agent} active />
    <div className="typing-dots"><span /><span /><span /></div>
  </div>
)

const ChatInput = ({ onSend, disabled, placeholder, suggestions = [], accent = 'var(--brand)' }) => {
  const [value, setValue] = useState('')
  const submit = (text = value) => {
    const next = text.trim()
    if (!next || disabled) return
    setValue('')
    onSend(next)
  }
  return (
    <div className="chat-input">
      {!!suggestions.length && <div className="suggestions">{suggestions.map((s) => <button key={s} onClick={() => submit(s)} disabled={disabled}>{s}</button>)}</div>}
      <div className="input-shell">
        <textarea value={value} onChange={(e) => setValue(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }} placeholder={placeholder} rows={1} />
        <button style={{ background: value.trim() && !disabled ? accent : '#dfe2ea' }} onClick={() => submit()} disabled={!value.trim() || disabled}>
          <Icon name={disabled ? 'clock' : 'send'} size={18} />
        </button>
      </div>
    </div>
  )
}

const Sidebar = ({ route, go, workspace, setWorkspace }) => {
  const [open, setOpen] = useState(false)
  return (
    <aside className="sidebar">
      <div className="workspace-switch">
        <button className="workspace-button" onClick={() => setOpen((v) => !v)}>
          <span>{workspace.emoji}</span>
          <b>{workspace.name}</b>
          <small>StartMate AI</small>
        </button>
        {open && (
          <div className="workspace-menu">
            {workspaces.map((ws) => (
              <button key={ws.id} onClick={() => { setWorkspace(ws); setOpen(false); go('home') }}>
                <span>{ws.emoji}</span>
                <b>{ws.name}</b>
                <small>{ws.desc}</small>
              </button>
            ))}
          </div>
        )}
      </div>

      <button className={route === 'discuss' ? 'discuss-btn on' : 'discuss-btn'} onClick={() => go('discuss')}>
        <Icon name="discuss" size={18} /> AI와 토론하기
      </button>

      <nav>
        <p>워크스페이스</p>
        <button className={route === 'home' ? 'on' : ''} onClick={() => go('home')}><Icon name="home" />워크스페이스</button>
        <p>AI 기능</p>
        {featureOrder.map((id) => {
          const feature = features[id]
          return <button key={id} className={route === id ? 'on' : ''} onClick={() => go(id)}><Icon name={feature.icon} />{feature.title}</button>
        })}
        <p>보관함</p>
        <button className={route === 'saved' ? 'on' : ''} onClick={() => go('saved')}><Icon name="bookmark" />저장한 결과</button>
      </nav>
      <div className="user-box">
        <span>{profile.name.slice(0, 1)}</span>
        <b>{profile.name}</b>
        <small>{profile.role} · {profile.loc}</small>
      </div>
    </aside>
  )
}

const Landing = ({ go }) => (
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

const Onboarding = ({ go }) => {
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const finish = () => {
    setLoading(true)
    window.setTimeout(() => go('home'), 1300)
  }
  const steps = [
    ['기본 역량과 경력', ['전공 또는 보유 역량', '경력', '강점 태그']],
    ['관심 분야와 지역', ['관심 분야', '거주 지역', '창업 희망 지역']],
    ['자금과 팀 구성', ['초기 자금', '팀 구성', '선호 창업 형태']],
  ]
  if (loading) return <main className="loading-page"><AgentAvatar id="profile" size={64} active /><h2>Profile Agent가 창업 적합도를 진단하고 있어요</h2><p>프로필을 분석해 강점, 리스크, 추천 방향을 정리합니다.</p></main>
  return (
    <main className="onboarding">
      <div className="onboarding-card">
        <div className="brand-line"><BrandMark /><b>창업 프로필 입력</b></div>
        <div className="progress">{[0, 1, 2].map((i) => <span key={i} className={i <= step ? 'on' : ''} />)}</div>
        <small>{step + 1} / 3 단계</small>
        <h1>{steps[step][0]}</h1>
        <p>AI가 개인화된 창업 분석을 할 수 있도록 기본 조건을 알려주세요.</p>
        <div className="form-grid">{steps[step][1].map((label) => <label key={label}>{label}<input defaultValue={label.includes('자금') ? profile.capital : label.includes('지역') ? profile.region : ''} placeholder={label} /></label>)}</div>
        <div className="form-actions">
          {step > 0 && <button onClick={() => setStep(step - 1)}>이전</button>}
          <button onClick={() => step < 2 ? setStep(step + 1) : finish()}>{step < 2 ? '다음' : '프로필 저장하고 진단받기'}</button>
        </div>
      </div>
    </main>
  )
}

const HomePage = ({ go, workspace }) => (
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

const FeatureCard = ({ id, go }) => {
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

const routeAgents = (question) => {
  const q = question.toLowerCase()
  const picked = []
  if (/아이템|아이디어|뭐.*하지|추천/.test(q)) picked.push('idea')
  if (/돈|자금|매출|수익|비용|손익|시뮬/.test(q)) picked.push('finance')
  if (/지원|정부|사업|공고|정책/.test(q)) picked.push('policy')
  if (/계획서|문서|제출|사업계획/.test(q)) picked.push('plan')
  if (/운영|주문|광고|전환|매장/.test(q)) picked.push('operation')
  if (/sns|홍보|마케팅|릴스|인스타/.test(q)) picked.push('marketing')
  if (!picked.length) picked.push('profile', 'idea')
  return [...new Set(picked)].slice(0, 3)
}

const agentReply = (agent, question) => {
  const replies = {
    profile: `현재 프로필 기준으로는 ${profile.strength}이 강점이고, ${profile.weakness}이 가장 큰 제약입니다. 먼저 고정비가 낮은 방식으로 검증하는 흐름이 좋아요.`,
    idea: '초기 자금이 적으니 오프라인 매장을 바로 여는 것보다 예약 판매, 팝업, 무재고 커머스처럼 작게 검증 가능한 아이템을 추천해요.',
    finance: '자금 100만 원 기준이면 재료비와 광고비를 분리해서 봐야 합니다. 첫 달 목표는 큰 매출보다 손익분기점에 가까워지는 주문 수를 찾는 쪽이 현실적이에요.',
    policy: '부산 지역과 예비창업자 조건을 보면 청년 예비창업 패키지, 로컬크리에이터 계열 공고를 우선 확인하는 게 좋습니다.',
    plan: '사업계획서에는 “왜 지금 이 지역에서 필요한지”와 “초기 비용을 어떻게 낮출지”를 분명하게 쓰는 것이 중요합니다.',
    operation: '운영 데이터가 생기면 매출보다 전환율, 재구매율, 상품별 기여도를 먼저 봐야 개선 방향이 명확해집니다.',
    marketing: 'SNS는 상품 소개보다 “왜 이번 주에 사야 하는지”가 드러나는 훅이 필요합니다. 릴스는 15초 안에 장소, 메뉴, 예약 CTA가 보여야 해요.',
  }
  return replies[agent] || question
}

const DiscussPage = () => {
  const [items, setItems] = useState([])
  const [busy, setBusy] = useState(false)
  const [typing, setTyping] = useState(null)
  const scroll = useRef(null)
  useEffect(() => { if (scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight }, [items, typing])

  const send = (text) => {
    if (busy) return
    const selected = routeAgents(text)
    setBusy(true)
    setItems((prev) => [...prev, { role: 'user', text }, { role: 'router', selected }])
    let delay = 500
    selected.forEach((agent) => {
      window.setTimeout(() => setTyping(agent), delay)
      delay += 700
      window.setTimeout(() => {
        setTyping(null)
        setItems((prev) => [...prev, { agent, text: agentReply(agent, text) }])
      }, delay)
      delay += 250
    })
    window.setTimeout(() => {
      setItems((prev) => [...prev, { role: 'conclusion', text: '정리하면, 토론에서는 방향을 먼저 잡고 정식 결과물이 필요할 때 기능 페이지로 넘어가는 흐름이 가장 자연스럽습니다.' }])
      setBusy(false)
    }, delay + 500)
  }

  return (
    <main className="discuss-page">
      <div className="page-title compact"><div><h1>AI와 토론하기</h1><p>질문에 맞는 Agent가 자동으로 모여 의견을 나눕니다.</p></div></div>
      <div className="chat-panel" ref={scroll}>
        {!items.length && <div className="empty-chat"><div className="agent-stack">{Object.keys(agents).map((id) => <AgentAvatar key={id} id={id} />)}</div><h2>무엇이든 물어보세요</h2><p>창업 아이템, 자금, 지원사업, 홍보까지 자유롭게 질문할 수 있어요.</p></div>}
        {items.map((item, index) => {
          if (item.role === 'router') return <div className="router-row" key={index}><Icon name="sparkle" /><div><b>Agent Router</b><p>{item.selected.map((id) => agents[id].name).join(', ')}가 이 질문에 적합해요.</p></div></div>
          if (item.role === 'conclusion') return <div className="conclusion" key={index}><b>종합 결론</b><p>{item.text}</p></div>
          return <ChatRow key={index} message={item} />
        })}
        {typing && <TypingRow agent={typing} />}
      </div>
      <ChatInput onSend={send} disabled={busy} placeholder="창업에 대한 고민을 물어보세요" suggestions={['자금 100만 원으로 가능한 창업 아이템 추천해줘', '지원사업 신청 가능성이 높은 방향을 알려줘', 'SNS 홍보 문구를 만들어줘']} />
    </main>
  )
}

const FeaturePage = ({ id, go }) => {
  const f = features[id]
  const agent = agents[f.agent]
  const [data, setData] = useState(() => cloneReport(id))
  const [messages, setMessages] = useState([{ agent: f.agent, text: `${f.title} 결과를 만들었어요. 오른쪽에서 원하는 방향을 말하면 이 리포트를 수정할 수 있어요.` }])
  const [busy, setBusy] = useState(false)
  const [typing, setTyping] = useState(null)
  const chatRef = useRef(null)
  useEffect(() => { if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight }, [messages, typing])

  const send = (text) => {
    setMessages((prev) => [...prev, { role: 'user', text }])
    setBusy(true)
    setTyping(f.agent)
    window.setTimeout(() => {
      setTyping(null)
      setMessages((prev) => [...prev, { agent: f.agent, text: `${agent.name}가 요청을 반영했어요. 실제 서비스에서는 이 지점에서 백엔드 AI API가 결과 JSON을 갱신합니다.` }])
      setBusy(false)
    }, 900)
  }

  return (
    <main className="feature-page">
      <section className="report-area">
        <div className="page-title"><div><h1>{f.title}</h1><p>{f.sub}</p></div><AgentBadge id={f.agent} /></div>
        <Report id={id} data={data} setData={setData} go={go} />
      </section>
      <aside className="feature-chat">
        <header style={{ color: agent.color }}><AgentAvatar id={f.agent} /><div><b>{agent.name}</b><small>이 리포트를 함께 수정해요</small></div></header>
        <div className="feature-chat-body" ref={chatRef}>
          {messages.map((m, i) => <ChatRow key={i} message={m} />)}
          {typing && <TypingRow agent={typing} />}
        </div>
        <ChatInput onSend={send} disabled={busy} placeholder="리포트를 어떻게 바꿀까요?" accent={agent.color} suggestions={['더 현실적인 방향으로 바꿔줘', '지원사업 신청 가능성이 높은 쪽으로', '20대 타깃 느낌으로 바꿔줘']} />
      </aside>
    </main>
  )
}

const Report = ({ id, data, go }) => {
  if (id === 'item') return <ItemReport data={data} go={go} />
  if (id === 'simulator') return <SimReport data={data} />
  if (id === 'support') return <SupportReport data={data} go={go} />
  if (id === 'plan') return <PlanReport data={data} />
  if (id === 'operation') return <OperationReport data={data} go={go} />
  return <SnsReport data={data} />
}

const ItemReport = ({ data, go }) => (
  <div className="report-stack">
    <Card><div className="map-box"><Icon name="pin" size={32} /></div><h3>{data.location} 상권 분석</h3><div className="metric-grid">{data.analysis.map(([k, v]) => <div key={k}><small>{k}</small><b>{v}</b></div>)}</div></Card>
    <Card><h3>상권 + 내 프로필 기반 추천</h3>{data.items.map((item) => <div className="idea-option" key={item.rank}><span>{item.rank}</span><div><b>{item.title}</b><p>{item.reason}</p></div><em>적합도 {item.score}</em></div>)}<button className="primary-wide" onClick={() => go('simulator')}>선택한 아이템으로 시뮬레이션 <Icon name="arrow" size={16} /></button></Card>
  </div>
)

const SimReport = ({ data }) => {
  const series = Array.from({ length: 4 }, (_, i) => {
    const day = [1, 7, 15, 30][i]
    const revenue = Math.round(data.startOrders * data.price * (1 + i * data.growthPct / 100))
    return [day, revenue]
  })
  return <Card><h3>첫 30일 시뮬레이션</h3><div className="sim-inputs"><span>{data.item}</span><span>판매가 {data.price.toLocaleString()}원</span><span>초기자금 {data.capital}만 원</span></div><div className="sim-chart">{series.map(([day, revenue]) => <div key={day}><i style={{ height: `${Math.max(22, revenue / 800)}px` }} /><b>Day {day}</b><span>{Math.round(revenue / 10000)}만 원</span></div>)}</div><div className="tags warn">{data.risks.map((r) => <span key={r}>{r}</span>)}</div></Card>
}

const SupportReport = ({ data, go }) => <Card><h3>신청 가능성이 높은 지원사업</h3>{data.list.map((p) => <div className="support-row" key={p.title}><div><b>{p.title}</b><p>{p.region} · 마감 {p.due}</p><small>필요서류: {p.docs.join(', ')}</small></div><em>{p.score}점</em></div>)}<button className="primary-wide" onClick={() => go('plan')}>이 공고로 사업계획서 작성</button></Card>

const PlanReport = ({ data }) => <Card><div className="card-head"><h3>사업계획서 초안 · {data.target}</h3><button>초안 저장</button></div>{data.sections.map(([title, body]) => <details key={title} open={title.startsWith('1')}><summary>{title}</summary><p>{body}</p></details>)}</Card>

const OperationReport = ({ data, go }) => <div className="report-stack"><Card><div className="kpi-grid">{data.kpis.map(([label, value, delta, good]) => <div key={label}><small>{label}</small><b>{value}</b><em className={good === false ? 'bad' : good ? 'good' : ''}>{delta}</em></div>)}</div>{data.products.map(([name, pct]) => <div className="bar-row" key={name}><span>{name}</span><b>{pct}%</b><i><em style={{ width: `${pct}%`, background: 'var(--a-operation)' }} /></i></div>)}</Card><Card><h3>개선 제안</h3>{data.suggestions.map(([title, body, link]) => <div className="suggest-card" key={title}><b>{title}</b><p>{body}</p>{link && <button onClick={() => go(link)}>SNS 홍보 자동화로 이동</button>}</div>)}</Card></div>

const SnsReport = ({ data }) => <Card><div className="sns-preview"><div><Icon name="play" /><h2>{data.topic}</h2><p>{data.hook}</p></div><section><h3>15초 영상 구성</h3>{data.beats.map((b) => <p key={b}>{b}</p>)}<div className="tags">{data.tags.map((t) => <span key={t}>{t}</span>)}</div><button className="primary-wide"><Icon name="clock" size={16} /> {data.schedule} 게시 예약</button></section></div></Card>

const SavedPage = () => {
  const saved = [
    ['idea', '로컬 카페 브랜드 키트', '적합도 92 · 구남로 상권'],
    ['finance', '30일 수익 시나리오', '예상 매출 236만 원'],
    ['policy', '청년 예비창업 패키지', '신청 가능성 88점 · D-12'],
  ]
  return <main className="page narrow"><div className="page-title"><div><h1>저장한 결과</h1><p>Agent와 함께 만든 결과물을 한곳에서 관리합니다.</p></div></div><div className="saved-grid">{saved.map(([agent, title, meta]) => <Card key={title}><AgentBadge id={agent} /><h3>{title}</h3><p>{meta}</p></Card>)}</div></main>
}

function App() {
  const [route, setRoute] = useState(() => localStorage.getItem('sm_route') || 'landing')
  const [workspace, setWorkspace] = useState(workspaces[0])
  useEffect(() => localStorage.setItem('sm_route', route), [route])
  const full = route === 'landing' || route === 'onboarding'
  const page = useMemo(() => {
    if (route === 'landing') return <Landing go={setRoute} />
    if (route === 'onboarding') return <Onboarding go={setRoute} />
    if (route === 'discuss') return <DiscussPage />
    if (route === 'saved') return <SavedPage />
    if (features[route]) return <FeaturePage key={route} id={route} go={setRoute} />
    return <HomePage go={setRoute} workspace={workspace} />
  }, [route, workspace])

  if (full) return <div className="app-root">{page}</div>
  return <div className="app-root"><Sidebar route={route} go={setRoute} workspace={workspace} setWorkspace={setWorkspace} />{page}</div>
}

export default App
