import { Card } from '../../shared/components/Card'

export const SupportReport = ({ data, go }) => <Card><h3>신청 가능성이 높은 지원사업</h3>{data.list.map((p) => <div className="support-row" key={p.title}><div><b>{p.title}</b><p>{p.region} · 마감 {p.due}</p><small>필요서류: {p.docs.join(', ')}</small></div><em>{p.score}점</em></div>)}<button className="primary-wide" onClick={() => go('plan')}>이 공고로 사업계획서 작성</button></Card>
