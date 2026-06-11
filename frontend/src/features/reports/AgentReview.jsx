import { Card } from '../../shared/components/Card'

const asTextList = (value) => (Array.isArray(value) ? value.filter(Boolean).map(String) : [])

export const AgentReview = ({ review }) => {
  const summary = review?.summary ? String(review.summary) : ''
  const checks = asTextList(review?.checks)
  const revisions = asTextList(review?.revisions)

  if (!summary && !checks.length && !revisions.length) {
    return null
  }

  return (
    <Card className="agent-review-card">
      <div className="agent-review-head">
        <span>Agent Review</span>
        <h3>Agent 검토 반영</h3>
      </div>
      {summary && <p className="agent-review-summary">{summary}</p>}
      {!!checks.length && (
        <div className="agent-review-section">
          <small>검토 기준</small>
          <div className="agent-review-tags">
            {checks.map((item) => <span key={item}>{item}</span>)}
          </div>
        </div>
      )}
      {!!revisions.length && (
        <div className="agent-review-section">
          <small>반영 내용</small>
          <ul>
            {revisions.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      )}
    </Card>
  )
}
