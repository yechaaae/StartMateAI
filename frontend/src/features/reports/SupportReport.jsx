import { Card } from '../../shared/components/Card'

const SEARCH_MODES = [
  ['PROFILE_IDEA', '프로필 + 아이템'],
  ['PROFILE_ONLY', '프로필 기준'],
  ['IDEA_ONLY', '아이템 기준'],
]

const GOALS = [
  ['HIGH_MATCH', '선정 가능성 우선'],
  ['EASY_PREP', '준비 쉬운 순'],
  ['LARGE_SUPPORT', '지원 규모 우선'],
  ['FAST_DEADLINE', '마감 임박 우선'],
]

export const SupportReport = ({
  data,
  go,
  selectedSupportTitle,
  onSelectSupport,
  supportSearchMode,
  onChangeSupportSearchMode,
  supportUserGoal,
  onChangeSupportUserGoal,
}) => (
  <Card>
    <h3>신청 가능성 높은 지원사업</h3>

    <div className="support-control-block">
      <small>추천 기준</small>
      <div className="support-control-row">
        {SEARCH_MODES.map(([value, label]) => (
          <button
            key={value}
            className={supportSearchMode === value ? 'support-filter on' : 'support-filter'}
            onClick={() => onChangeSupportSearchMode?.(value)}
          >
            {label}
          </button>
        ))}
      </div>
    </div>

    <div className="support-control-block">
      <small>현재 목표</small>
      <div className="support-control-row">
        {GOALS.map(([value, label]) => (
          <button
            key={value}
            className={supportUserGoal === value ? 'support-filter on' : 'support-filter'}
            onClick={() => onChangeSupportUserGoal?.(value)}
          >
            {label}
          </button>
        ))}
      </div>
    </div>

    {data.list.map((program) => {
      const selected = selectedSupportTitle === program.title
      return (
        <button
          key={program.title}
          className={selected ? 'support-row selected' : 'support-row'}
          onClick={() => onSelectSupport?.(program.title)}
        >
          <div>
            <b>{program.title}</b>
            <p>{program.region} · 마감 {program.due}</p>
            <small>필요 서류: {program.docs.join(', ')}</small>
          </div>
          <em>{program.score}점</em>
        </button>
      )
    })}

    <button className="primary-wide" onClick={() => go('plan')}>
      이 공고로 사업계획서 작성
    </button>
  </Card>
)
