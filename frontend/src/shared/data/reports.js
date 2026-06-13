export const reportDefaults = {
  item: {
    location: '부산 해운대구 구남로',
    analysis: [
      ['유동 인구', '상위 12%'],
      ['카페 밀집도', '높음, 경쟁 강함'],
      ['평균 임대료', '월 48만원대'],
      ['주요 연령대', '20-30대'],
    ],
    items: [
      { rank: 1, title: '로컬 카페 브랜드 스튜디오', score: 92, reason: '카페 밀집 상권과 사용자의 강점을 결합하기 좋습니다.' },
      { rank: 2, title: '구독형 디저트 예약 창업', score: 88, reason: '초기 고정비를 낮추고 SNS 운영 경험을 활용할 수 있습니다.' },
      { rank: 3, title: '무재고 굿즈 커머스', score: 81, reason: '자본 부담이 적고 사용자 취향을 상품화하기 좋습니다.' },
    ],
  },
  simulator: {
    item: '수제 쿠키 온라인 예약 판매',
    price: 7000,
    capital: 200,
    startOrders: 6,
    growthPct: 42,
    risks: ['생산 지연', '포장/배송', '재구매 저하'],
  },
  support: {
    list: [
      { title: '2026 청년 예비창업 패키지', score: 88, region: '전국', due: 'D-12', docs: ['사업계획서', '신분증', '졸업 증명서'] },
      { title: '부산 로컬크리에이터 육성', score: 81, region: '부산', due: 'D-23', docs: ['사업계획서', '지역 활동 증빙'] },
      { title: '1인 미디어 콘텐츠 창업 지원', score: 74, region: '전국', due: 'D-31', docs: ['포트폴리오', '사업계획서'] },
    ],
  },
  plan: {
    target: '청년 예비창업 패키지',
    sections: [
      ['1. 사업 개요', '부산 해운대 상권을 기반으로 로컬 카페와 소상공인을 위한 로고, 메뉴, SNS 패키지 서비스를 제공합니다.'],
      ['2. 문제 정의', '소규모 카페는 브랜드를 만들 SNS 운영 역량이 부족하지만 전문 대행사를 쓰기에는 비용 부담이 큽니다.'],
      ['3. 해결 방안', '로고, 메뉴판, SNS 템플릿, 홍보 문구를 묶은 저비용 브랜드 패키지를 제공합니다.'],
      ['4. 고객 및 시장', '1차 고객은 해운대 반경 1km 내 카페와 디저트 매장 운영자입니다.'],
      ['5. 수익 모델', '브랜드 세팅 60만원, SNS 운영 월 25만원 구독형 상품으로 매출을 만듭니다.'],
    ],
  },
  operation: {
    // 운영 피드백은 사용자가 직접 입력하는 실측 데이터라 기본값(목데이터)을 두지 않는다.
    // KPI는 입력 필드를 매핑하기 위한 빈 스캐폴딩만 유지한다.
    period: '',
    kpis: [
      { key: 'totalSales', label: '매출', unit: '원', current: '', previous: null },
      { key: 'totalCost', label: '지출', unit: '원', current: '', previous: null },
      { key: 'orderCount', label: '주문 수', unit: '건', current: '', previous: null },
      { key: 'adConversionRate', label: '광고 전환율', unit: '%', current: '', previous: null },
    ],
    products: [],
    channels: [],
    notes: '',
    suggestions: [],
  },
  sns: {
    topic: '수제 쿠키 예약',
    hook: '해운대에서 제일 빠르게 품절되는 쿠키, 주문 즉시 구워드려요.',
    beats: ['0-2초 매장 입구와 로고 클로즈업', '2-6초 대표 메뉴 클로즈업', '6-11초 제조 과정 프로모션', '11-15초 예약 안내와 위치 CTA'],
    tags: ['#해운대카페', '#구남로맛집', '#수제쿠키', '#부산디저트', '#주문예약'],
    channel: 'INSTAGRAM_REELS',
    tone: 'FRIENDLY',
    objective: 'CONVERSION',
    callToAction: '지금 예약 주문하기',
    schedule: '수요일 오전 9시',
  },
}

export const cloneReport = (id) => JSON.parse(JSON.stringify(reportDefaults[id]))
