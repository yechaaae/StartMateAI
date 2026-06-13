import { useState } from 'react'
import { Card } from '../../shared/components/Card'
import { AgentReview } from './AgentReview'
import { PlanApplicationForm } from './PlanApplicationForm'

const PLAN_GOALS = [
  ['ALIGN_SUPPORT', '공고 맞춤 보완'],
  ['STRENGTHEN_SECTION', '문단 강화'],
  ['REWRITE_TONE', '문체 다듬기'],
  ['CHECK_GAPS', '빠진 항목 점검'],
]

// 공고문 붙여넣어 재생성하는 입력 블록(공고/신청서 모드 공통).
const AnnounceBlock = ({ announcement, onSubmitAnnouncement, announcementLoading, label }) => {
  const [draft, setDraft] = useState(announcement ?? '')
  const canSubmit = Boolean(draft.trim()) && !announcementLoading
  return (
    <details className="plan-announce-block" open={!announcement}>
      <summary>{label}</summary>
      <p className="plan-announce-help">
        지원사업 공고문을 그대로 붙여넣으면 모집대상·지원내용·평가 관점에 맞춰 답변을 다시 작성해요.
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
          {announcementLoading ? '답변을 다시 쓰는 중…' : '이 공고로 다시 작성'}
        </button>
      </div>
    </details>
  )
}

export const PlanReport = ({
  data,
  focusedSectionTitle,
  onFocusSection,
  planGoal,
  onChangePlanGoal,
  announcement = '',
  onSubmitAnnouncement,
  announcementLoading = false,
  applicationForm = null,
}) => {
  // 신청서 양식이 연결되면 plan UI가 '그 신청서 폼'으로 바뀐다.
  if (applicationForm) {
    return (
      <div className="report-stack">
        <AgentReview review={data.agentReview} />
        <Card>
          {onSubmitAnnouncement && (
            <AnnounceBlock
              announcement={announcement}
              onSubmitAnnouncement={onSubmitAnnouncement}
              announcementLoading={announcementLoading}
              label="공고문 수정해서 다시 작성"
            />
          )}
          <PlanApplicationForm
            form={applicationForm}
            sections={data.sections}
            loading={announcementLoading}
          />
        </Card>
      </div>
    )
  }

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
          <AnnounceBlock
            announcement={announcement}
            onSubmitAnnouncement={onSubmitAnnouncement}
            announcementLoading={announcementLoading}
            label="공고문 붙여넣어 맞춤 보완"
          />
        )}

        {data.sections.map(([title, body], index) => {
          const selected = focusedSectionTitle === title
          return (
            <details key={title} open={index === 0 || title.startsWith('1')}>
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
              <button
                type="button"
                className="plan-copy-btn"
                onClick={() => navigator.clipboard?.writeText(body)}
              >
                답변 복사
              </button>
            </details>
          )
        })}
      </Card>
    </div>
  )
}
