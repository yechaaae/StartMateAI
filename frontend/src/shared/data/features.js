export const features = {
  item: {
    title: 'AI 창업 아이템 추천',
    sub: '프로필과 업계 조건을 바탕으로 현실적인 창업 아이템을 추천합니다.',
    card: '내 경험과 자금에 맞는 창업 아이템을 추천받아요.',
    flag: '아이디어가 없다면',
    agent: 'idea',
    icon: 'bulb',
  },
  simulator: {
    title: '창업 시뮬레이션',
    sub: '초기 자금, 판매가, 예상 주문 수로 매출과 손익을 예측합니다.',
    card: '초기 비용과 손익분기점을 미리 계산해요.',
    flag: '가능성을 보고 싶다면',
    agent: 'finance',
    icon: 'chart',
  },
  support: {
    title: '창업지원사업 추천',
    sub: '거주 지역, 연령, 지원 아이템에 맞는 지원사업을 찾아줍니다.',
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

export const featureOrder = ['item', 'simulator', 'support', 'plan', 'operation', 'sns']

// 메인(home) 하단 기능 메뉴 그룹. 워크스페이스가 곧 아이템이므로 'item'은 제외한다.
export const preStartupFeatures = ['simulator', 'support', 'plan'] // 창업 전 3
export const postStartupFeatures = ['operation', 'sns'] // 창업 후 2
