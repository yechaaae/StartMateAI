import { useState } from 'react'
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
  announcement = '',
  onSubmitAnnouncement,
  announcementLoading = false,
}) => {
  const [draft, setDraft] = useState(announcement ?? '')
  const canSubmit = Boolean(draft.trim()) && !announcementLoading

  return (
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

        {onSubmitAnnouncement && (
          <details className="plan-announce-block" open={Boolean(announcement)}>
            <summary>공고문 붙여넣어 맞춤 보완</summary>
            <p className="plan-announce-help">
              지원사업 공고문을 그대로 붙여넣으면 모집대상·지원내용·평가 관점에 맞춰 초안을 다시 작성해요.
            </p>
            <textarea
              className="onboarding-refine-input"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="예: [2026 경북형 사회적경제 창업학교] 참가자 모집 / 모집대상 ... / 지원내용 ..."
              rows={6}
            />
            <div className="onboarding-modal-actions">
              <button
                type="button"
                className="om-primary"
                disabled={!canSubmit}
                onClick={() => canSubmit && onSubmitAnnouncement(draft)}
              >
                {announcementLoading ? '초안을 다시 쓰는 중…' : '이 공고로 초안 다시 쓰기'}
              </button>
            </div>
          </details>
        )}

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
}
