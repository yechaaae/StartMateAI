const MOCK_SUPPORT_PROGRAMS = [
  {
    id: 'youth-pre-startup-2026',
    title: '2026 청년 예비창업 패키지',
    region: '전국',
    dDay: 'D-12',
    score: 88,
    requiredDocs: ['사업계획서', '신분증', '졸업 증명서'],
    reason: '예비창업 단계와 브랜딩 기반 아이템이 잘 맞고, 초기 사업화 자금 활용도가 높습니다.',
    amount: 100000000,
    tags: ['예비창업', '청년', '사업화'],
    deadlineDate: '2026-06-22',
    prepEase: 76,
  },
  {
    id: 'busan-local-creator-2026',
    title: '부산 로컬크리에이터 육성',
    region: '부산',
    dDay: 'D-23',
    score: 81,
    requiredDocs: ['사업계획서', '지역 활용 증빙', '대표자 주민등록등본'],
    reason: '지역 자원과 스토리텔링을 연결하기 좋아 로컬 브랜드형 창업 아이템에 유리합니다.',
    amount: 50000000,
    tags: ['로컬', '지역특화', '브랜딩'],
    deadlineDate: '2026-07-03',
    prepEase: 68,
  },
  {
    id: 'one-person-media-contents-2026',
    title: '1인 미디어 콘텐츠 창업 지원',
    region: '전국',
    dDay: 'D-31',
    score: 74,
    requiredDocs: ['포트폴리오', '사업계획서'],
    reason: 'SNS 운영 경험과 콘텐츠 제작 역량을 증빙하기 쉬워 서류 준비 부담이 낮습니다.',
    amount: 30000000,
    tags: ['콘텐츠', '미디어', '마케팅'],
    deadlineDate: '2026-07-11',
    prepEase: 91,
  },
  {
    id: 'seoul-small-business-startup-2026',
    title: '서울 소상공인 창업 성장 지원',
    region: '서울',
    dDay: 'D-7',
    score: 83,
    requiredDocs: ['사업계획서', '주민등록등본', '창업 예정지 확인서'],
    reason: '상권 기반 실행 계획을 제시하기 좋고, 마감이 가까워 빠른 검토 가치가 있습니다.',
    amount: 40000000,
    tags: ['소상공인', '상권', '창업성장'],
    deadlineDate: '2026-06-17',
    prepEase: 72,
  },
]

const sorters = {
  HIGH_MATCH: (a, b) => b.score - a.score,
  EASY_PREP: (a, b) => b.prepEase - a.prepEase,
  LARGE_SUPPORT: (a, b) => b.amount - a.amount,
  FAST_DEADLINE: (a, b) => new Date(a.deadlineDate) - new Date(b.deadlineDate),
}

const wait = (ms) => new Promise((resolve) => {
  globalThis.setTimeout(resolve, ms)
})

export const runSupportProgramSearch = async (filters) => {
  await wait(filters.delayMs ?? 520)

  const sorter = sorters[filters.priority] ?? sorters.HIGH_MATCH
  return [...MOCK_SUPPORT_PROGRAMS]
    .sort(sorter)
}
