export const reportDefaults = {
  item: {
    location: '',
    analysis: [],
    items: [],
  },
  simulator: {
    item: '',
    price: 0,
    capital: 0,
    startOrders: 0,
    growthPct: 0,
    risks: [],
  },
  support: {
    list: [],
  },
  plan: {
    target: '',
    sections: [],
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
    topic: '',
    hook: '',
    beats: [],
    tags: [],
    channel: 'INSTAGRAM_REELS',
    tone: 'FRIENDLY',
    objective: 'CONVERSION',
    callToAction: '',
    schedule: '',
  },
}

export const cloneReport = (id) => JSON.parse(JSON.stringify(reportDefaults[id]))
