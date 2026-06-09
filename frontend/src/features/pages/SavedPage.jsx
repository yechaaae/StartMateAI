import { AgentBadge } from '../../shared/components/AgentBadge'
import { Card } from '../../shared/components/Card'

export const SavedPage = () => {
  const saved = [
    ['idea', '로컬 카페 브랜드 키트', '적합도 92 · 구남로 상권'],
    ['finance', '30일 수익 시나리오', '예상 매출 236만 원'],
    ['policy', '청년 예비창업 패키지', '신청 가능성 88점 · D-12'],
  ]
  return <main className="page narrow"><div className="page-title"><div><h1>저장한 결과</h1><p>Agent와 함께 만든 결과물을 한곳에서 관리합니다.</p></div></div><div className="saved-grid">{saved.map(([agent, title, meta]) => <Card key={title}><AgentBadge id={agent} /><h3>{title}</h3><p>{meta}</p></Card>)}</div></main>
}
