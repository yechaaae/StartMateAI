import { profile } from '../../shared/data/profile'

export const routeAgents = (question) => {
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

export const agentReply = (agent, question) => {
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
