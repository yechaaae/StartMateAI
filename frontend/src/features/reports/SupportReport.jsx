import { useEffect, useState } from 'react'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'
import { AgentReview } from './AgentReview'
import { withPinnedGyeongbukSocialProgram } from './supportProgramSearch'

const SEARCH_MODES = [
  ['PROFILE_IDEA', '프로필 + 아이템'],
  ['PROFILE_ONLY', '프로필 기준'],
  ['IDEA_ONLY', '아이템 기준'],
]

const PRIORITIES = [
  ['HIGH_MATCH', '선정 가능성 우선'],
  ['EASY_PREP', '서류 준비 쉬운 순'],
  ['LARGE_SUPPORT', '지원 규모 우선'],
  ['FAST_DEADLINE', '마감 임박 우선'],
]

const REGION_BASES = [
  ['BUSINESS_REGISTRATION', '사업자등록 예정지'],
  ['RESIDENCE', '거주 지역'],
  ['TARGET_AREA', '창업 희망 지역'],
]

// 자금성 지원(사업) vs 비자금성 지원(프로그램) 분류
const FUNDING_TYPES = new Set(['grant', 'loan', 'voucher', 'fund'])
const PROGRAM_TYPES = new Set(['education', 'mentoring', 'space', 'consulting', 'program'])
const isFundingProgram = (program) => {
  const type = String(program.supportType ?? '').toLowerCase()
  if (FUNDING_TYPES.has(type)) return true
  if (PROGRAM_TYPES.has(type)) return false
  return /자금|보조금|융자|바우처|지원금|사업화/.test(program.title ?? '')
}

const formatAmount = (amount) => {
  if (!amount) {
    return null
  }
  if (typeof amount === 'string') {
    return amount.trim() || null
  }
  return amount >= 100000000
    ? `최대 ${amount / 100000000}억원`
    : `최대 ${amount / 10000}만원`
}

const getDocs = (program) => program.requiredDocs ?? program.docs ?? []
const getDDay = (program) => program.dDay ?? program.due
const getProgramId = (program) => program.id ?? program.title

const SupportProgramCard = ({
  program,
  selected,
  saved,
  actionLabel,
  onAction,
  onToggleSave,
}) => {
  const amount = formatAmount(program.amount)
  const docs = getDocs(program)
  const dDay = getDDay(program)
  const meta = [program.region, dDay ? `마감 ${dDay}` : ''].filter(Boolean).join(' · ')

  return (
    <article className={selected ? 'support-program-card selected' : 'support-program-card'}>
      <div className="support-program-top">
        <div>
          <h4>
            {program.isYouth && <span className="support-youth-badge">청년</span>}
            {program.title}
          </h4>
          {meta && <p>{meta}</p>}
        </div>
        <strong>{program.score}점</strong>
      </div>

      {program.reason && <p className="support-program-reason">{program.reason}</p>}

      {!!docs.length && (
        <div className="support-program-docs">
          <span>필요 서류</span>
          <p>{docs.join(', ')}</p>
        </div>
      )}

      <div className="support-program-bottom">
        <div className="support-program-tags">
          {amount && <span>{amount}</span>}
          {(program.tags ?? []).map((tag) => <span key={tag}>{tag}</span>)}
        </div>
        <div className="support-program-buttons">
          {onToggleSave && (
            <button
              type="button"
              className={saved ? 'support-save-btn saved' : 'support-save-btn'}
              aria-pressed={saved}
              onClick={() => onToggleSave(program, saved)}
            >
              {saved ? '저장됨' : '저장'}
            </button>
          )}
          <button onClick={onAction} type="button">
            {actionLabel}
          </button>
        </div>
      </div>
    </article>
  )
}

const ResultBox = ({
  title,
  description,
  programs,
  selectedSupportTitle,
  onSelectSupport,
  savedIdSet,
  onToggleSave,
  onWritePlanFromProgram,
  emptyTitle = '해당하는 결과가 없어요',
  emptyDescription = '조건을 바꿔 다시 추천을 받아보세요.',
  go,
}) => (
  <Card className="support-results-card">
    <div className="support-results-head">
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      <span>{programs.length}개</span>
    </div>
    {programs.length === 0 ? (
      <div className="support-empty-state">
        <b>{emptyTitle}</b>
        <p>{emptyDescription}</p>
      </div>
    ) : (
      <div className="support-program-list">
        {programs.map((program) => (
          <SupportProgramCard
            key={getProgramId(program)}
            program={program}
            selected={selectedSupportTitle === program.title}
            saved={savedIdSet?.has(getProgramId(program))}
            actionLabel="이 공고로 사업계획서 작성"
            onAction={() => {
              onSelectSupport?.(program.title)
              if (onWritePlanFromProgram) {
                onWritePlanFromProgram(program)
              } else {
                go('plan')
              }
            }}
            onToggleSave={onToggleSave}
          />
        ))}
      </div>
    )}
  </Card>
)

export const SupportReport = ({
  data,
  go,
  selectedSupportTitle,
  onSelectSupport,
  supportSearchMode,
  onChangeSupportSearchMode,
  supportUserGoal,
  onChangeSupportUserGoal,
  supportRegionBasis,
  onChangeSupportRegionBasis,
  supportSearchLoading,
  supportHasSearched,
  onRunSupportSearch,
  onSaveSupportProgram,
  onDeleteSupportProgram,
  savedSupportPrograms = [],
  supportViewMode = 'all',
  onChangeSupportViewMode,
  onWritePlanFromProgram,
}) => {
  // 조건 선택 화면 ↔ 추천 결과 화면 (시뮬레이션처럼 페이지가 바뀐다)
  const [view, setView] = useState(supportHasSearched ? 'results' : 'condition')

  // 검색이 시작되면 결과 화면으로 전환(뒤로가기는 사용자가 명시적으로).
  useEffect(() => {
    if (supportSearchLoading) setView('results')
  }, [supportSearchLoading])

  // 헤더 드롭다운 등에서 '저장한 결과' 뷰로 전환되면 결과 화면을 보여준다.
  useEffect(() => {
    if (supportViewMode === 'saved') setView('results')
  }, [supportViewMode])

  // 'saved' 뷰에서는 사용자가 저장한 항목만 그대로 보여준다(자동 고정 핀 미적용).
  const isSavedView = supportViewMode === 'saved'
  const sourceList = isSavedView
    ? savedSupportPrograms
    : withPinnedGyeongbukSocialProgram(data.list ?? [], { force: true })
  const fundingPrograms = sourceList.filter(isFundingProgram)
  const programPrograms = sourceList.filter((program) => !isFundingProgram(program))

  // 저장 여부 판정용 id 집합(저장소의 toStableId = id ?? title 과 동일 기준).
  const savedIdSet = new Set((savedSupportPrograms ?? []).map((program) => program.id ?? program.title))

  // 카드의 저장 버튼: 저장돼 있으면 해제, 아니면 개별 저장.
  const handleToggleSave = (program, saved) => {
    if (saved) onDeleteSupportProgram?.(program)
    else onSaveSupportProgram?.(program)
  }

  const runSearch = () => {
    setView('results')
    onRunSupportSearch?.()
  }

  return (
    <div className="support-report-stack">
      {view === 'condition' && (
        <>
          <Card className="support-condition-card">
            <div className="support-condition-head">
              <div>
                <span>Policy Agent</span>
                <h3>맞춤 지원사업 찾기</h3>
                <p>내 창업 상황에 맞는 기준을 선택하면 적합한 지원사업을 모아볼 수 있습니다.</p>
              </div>
            </div>

            <div className="support-condition-grid">
              <div className="support-control-block">
                <small>추천 기준</small>
                <div className="support-control-row">
                  {SEARCH_MODES.map(([value, label]) => (
                    <button
                      key={value}
                      className={supportSearchMode === value ? 'support-filter on' : 'support-filter'}
                      onClick={() => onChangeSupportSearchMode?.(value)}
                      type="button"
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="support-control-block">
                <small>우선순위</small>
                <div className="support-control-row">
                  {PRIORITIES.map(([value, label]) => (
                    <button
                      key={value}
                      className={supportUserGoal === value ? 'support-filter on' : 'support-filter'}
                      onClick={() => onChangeSupportUserGoal?.(value)}
                      type="button"
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="support-control-block">
                <small>지역 기준</small>
                <div className="support-control-row">
                  {REGION_BASES.map(([value, label]) => (
                    <button
                      key={value}
                      className={supportRegionBasis === value ? 'support-filter on' : 'support-filter'}
                      onClick={() => onChangeSupportRegionBasis?.(value)}
                      type="button"
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <button
              className="support-search-button"
              onClick={runSearch}
              disabled={supportSearchLoading}
              type="button"
            >
              {supportSearchLoading ? '지원사업을 살펴보는 중...' : '추천 결과 확인하기'}
            </button>
          </Card>
        </>
      )}

      {view === 'results' && (
        <>
          <div className="support-results-topbar">
            <button type="button" className="support-back-btn" onClick={() => setView('condition')}>
              <Icon name="arrow" size={15} style={{ transform: 'rotate(180deg)' }} /> 조건 다시 선택
            </button>
            <span className="support-results-title">{isSavedView ? '저장한 결과' : '추천 결과'}</span>
            <div className="support-view-toggle">
              <button
                type="button"
                className={isSavedView ? 'support-filter' : 'support-filter on'}
                onClick={() => onChangeSupportViewMode?.('all')}
              >
                전체 추천
              </button>
              <button
                type="button"
                className={isSavedView ? 'support-filter on' : 'support-filter'}
                onClick={() => onChangeSupportViewMode?.('saved')}
              >
                저장한 결과{savedSupportPrograms.length ? ` ${savedSupportPrograms.length}` : ''}
              </button>
            </div>
          </div>

          {!isSavedView && <AgentReview review={data.agentReview} />}

          {supportSearchLoading ? (
            <Card className="support-results-card">
              <div className="support-loading-state">
                <b>조건에 맞는 지원사업을 찾고 있어요</b>
                <p>잠시 후 신청 가능성과 준비 난이도를 함께 확인할 수 있습니다.</p>
              </div>
            </Card>
          ) : (
            <>
              <ResultBox
                title={isSavedView ? '저장한 지원사업' : '추천 지원사업'}
                description="자금·사업화 등 직접 지원 위주의 공고입니다. 청년 대상 사업이 위로 정렬됩니다."
                programs={fundingPrograms}
                selectedSupportTitle={selectedSupportTitle}
                onSelectSupport={onSelectSupport}
                savedIdSet={savedIdSet}
                onToggleSave={handleToggleSave}
                onWritePlanFromProgram={onWritePlanFromProgram}
                emptyTitle={isSavedView ? '저장한 지원사업이 아직 없어요' : undefined}
                emptyDescription={isSavedView ? "추천 카드의 '저장'을 눌러 담아보세요." : undefined}
                go={go}
              />
              <ResultBox
                title={isSavedView ? '저장한 지원 프로그램' : '추천 지원 프로그램'}
                description="교육·멘토링·공간 등 역량/실행을 돕는 프로그램입니다."
                programs={programPrograms}
                selectedSupportTitle={selectedSupportTitle}
                onSelectSupport={onSelectSupport}
                savedIdSet={savedIdSet}
                onToggleSave={handleToggleSave}
                onWritePlanFromProgram={onWritePlanFromProgram}
                emptyTitle={isSavedView ? '저장한 지원 프로그램이 아직 없어요' : undefined}
                emptyDescription={isSavedView ? "추천 카드의 '저장'을 눌러 담아보세요." : undefined}
                go={go}
              />
            </>
          )}
        </>
      )}
    </div>
  )
}
