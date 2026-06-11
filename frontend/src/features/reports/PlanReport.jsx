import { Card } from '../../shared/components/Card'
import { AgentReview } from './AgentReview'

const PLAN_GOALS = [
  ['ALIGN_SUPPORT', '공고 맞춤 보완'],
  ['STRENGTHEN_SECTION', '문단 강화'],
  ['REWRITE_TONE', '문체 다듬기'],
  ['CHECK_GAPS', '빠진 항목 점검'],
]

export const PlanReport = ({
  data,
  focusedSectionTitle,
  onFocusSection,
  planGoal,
  onChangePlanGoal,
}) => (
  <div className="report-stack">
    <AgentReview review={data.agentReview} />

    <Card>
      <div className="card-head">
        <h3>사업계획서 초안 · {data.target}</h3>
        <button type="button">초안 저장</button>
      </div>

      <div className="support-control-block">
        <small>작성 목표</small>
        <div className="support-control-row">
          {PLAN_GOALS.map(([value, label]) => (
            <button
              key={value}
              className={planGoal === value ? 'support-filter on' : 'support-filter'}
              onClick={() => onChangePlanGoal?.(value)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {data.sections.map(([title, body]) => {
        const selected = focusedSectionTitle === title
        return (
          <details key={title} open={title.startsWith('1')}>
            <summary>
              <button
                type="button"
                className={selected ? 'plan-section-trigger selected' : 'plan-section-trigger'}
                onClick={() => onFocusSection?.(title)}
              >
                {title}
              </button>
            </summary>
            <p>{body}</p>
          </details>
        )
      })}
    </Card>
  </div>
)
