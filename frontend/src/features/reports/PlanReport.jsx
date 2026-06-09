import { Card } from '../../shared/components/Card'

export const PlanReport = ({ data }) => <Card><div className="card-head"><h3>사업계획서 초안 · {data.target}</h3><button>초안 저장</button></div>{data.sections.map(([title, body]) => <details key={title} open={title.startsWith('1')}><summary>{title}</summary><p>{body}</p></details>)}</Card>
