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

const SAVED_PAGE_SIZE = 3

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
  actionLabel,
  onAction,
  onSave,
  onDelete,
}) => {
  const amount = formatAmount(program.amount)
  const docs = getDocs(program)
  const dDay = getDDay(program)
  const meta = [program.region, dDay ? `마감 ${dDay}` : ''].filter(Boolean).join(' · ')

  return (
    <article className={selected ? 'support-program-card selected' : 'support-program-card'}>
      {onDelete && (
        <button
          className="support-card-delete"
          onClick={() => onDelete(program)}
          type="button"
          aria-label={`${program.title} 삭제`}
        >
          ×
        </button>
      )}
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
          {onSave && (
            <button type="button" className="support-save-btn" onClick={() => onSave(program)}>
              저장
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

const ResultBox = ({ title, description, programs, selectedSupportTitle, onSelectSupport, onSaveSupportProgram, onWritePlanFromProgram, go }) => (
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
        <b>해당하는 결과가 없어요</b>
        <p>조건을 바꿔 다시 추천을 받아보세요.</p>
      </div>
    ) : (
      <div className="support-program-list">
        {programs.map((program) => (
          <SupportProgramCard
            key={getProgramId(program)}
            program={program}
            selected={selectedSupportTitle === program.title}
            actionLabel="이 공고로 사업계획서 작성"
            onAction={() => {
              onSelectSupport?.(program.title)
              if (onWritePlanFromProgram) {
                onWritePlanFromProgram(program)
              } else {
                go('plan')
              }
            }}
            onSave={onSaveSupportProgram}
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
  savedSupportPrograms = [],
  onSaveSupportProgram,
  onDeleteSavedSupportProgram,
  onWritePlanFromProgram,
}) => {
  const [savedPage, setSavedPage] = useState(1)
  const [deleteTarget, setDeleteTarget] = useState(null)
  // 조건 선택 화면 ↔ 추천 결과 화면 (시뮬레이션처럼 페이지가 바뀐다)
  const [view, setView] = useState(supportHasSearched ? 'results' : 'condition')

  // 검색이 시작되면 결과 화면으로 전환(뒤로가기는 사용자가 명시적으로).
  useEffect(() => {
    if (supportSearchLoading) setView('results')
  }, [supportSearchLoading])

  const programs = withPinnedGyeongbukSocialProgram(data.list ?? [], { force: true })
  const fundingPrograms = programs.filter(isFundingProgram)
  const programPrograms = programs.filter((program) => !isFundingProgram(program))

  const runSearch = () => {
    setView('results')
    onRunSupportSearch?.()
  }

  const historicalPrograms = savedSupportPrograms
  const totalSavedPages = Math.max(1, Math.ceil(historicalPrograms.length / SAVED_PAGE_SIZE))
  const visibleSavedPage = Math.min(savedPage, totalSavedPages)
  const pagedSavedPrograms = historicalPrograms.slice(
    (visibleSavedPage - 1) * SAVED_PAGE_SIZE,
    visibleSavedPage * SAVED_PAGE_SIZE,
  )

  const closeDeleteAlert = () => setDeleteTarget(null)
  const confirmDelete = () => {
    if (!deleteTarget) {
      return
    }
    onDeleteSavedSupportProgram?.(getProgramId(deleteTarget))
    closeDeleteAlert()
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

          <Card className="support-results-card">
            <div className="support-results-head">
              <div>
                <h3>저장한 추천 목록</h3>
                <p>추천 결과에서 저장한 지원사업을 다시 볼 수 있습니다. 필요 없는 항목은 목록에서 삭제하세요.</p>
              </div>
              <span>{historicalPrograms.length}개</span>
            </div>

            {!historicalPrograms.length && (
              <div className="support-empty-state">
                <b>아직 보관된 추천사업이 없습니다</b>
                <p>추천 결과를 확인하면 다음에 다시 볼 수 있도록 이 목록에 남겨둘게요.</p>
              </div>
            )}

            {!!historicalPrograms.length && (
              <>
                <div className="support-program-list">
                  {pagedSavedPrograms.map((program) => (
                    <SupportProgramCard
                      key={getProgramId(program)}
                      program={program}
                      selected={selectedSupportTitle === program.title}
                      actionLabel="이 공고로 사업계획서 작성"
                      onAction={() => {
                        onSelectSupport?.(program.title)
                        if (onWritePlanFromProgram) {
                          onWritePlanFromProgram(program)
                        } else {
                          go('plan')
                        }
                      }}
                      onDelete={setDeleteTarget}
                    />
                  ))}
                </div>

                <div className="support-pagination">
                  <button
                    onClick={() => setSavedPage((page) => Math.max(1, page - 1))}
                    disabled={visibleSavedPage <= 1}
                    type="button"
                  >
                    이전
                  </button>
                  <span>{visibleSavedPage} / {totalSavedPages}</span>
                  <button
                    onClick={() => setSavedPage((page) => Math.min(totalSavedPages, page + 1))}
                    disabled={visibleSavedPage >= totalSavedPages}
                    type="button"
                  >
                    다음
                  </button>
                </div>
              </>
            )}
          </Card>
        </>
      )}

      {view === 'results' && (
        <>
          <div className="support-results-topbar">
            <button type="button" className="support-back-btn" onClick={() => setView('condition')}>
              <Icon name="arrow" size={15} style={{ transform: 'rotate(180deg)' }} /> 조건 다시 선택
            </button>
            <span className="support-results-title">추천 결과</span>
          </div>

          <AgentReview review={data.agentReview} />

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
                title="추천 지원사업"
                description="자금·사업화 등 직접 지원 위주의 공고입니다. 청년 대상 사업이 위로 정렬됩니다."
                programs={fundingPrograms}
                selectedSupportTitle={selectedSupportTitle}
                onSelectSupport={onSelectSupport}
                onSaveSupportProgram={onSaveSupportProgram}
                onWritePlanFromProgram={onWritePlanFromProgram}
                go={go}
              />
              <ResultBox
                title="추천 지원 프로그램"
                description="교육·멘토링·공간 등 역량/실행을 돕는 프로그램입니다."
                programs={programPrograms}
                selectedSupportTitle={selectedSupportTitle}
                onSelectSupport={onSelectSupport}
                onSaveSupportProgram={onSaveSupportProgram}
                onWritePlanFromProgram={onWritePlanFromProgram}
                go={go}
              />
            </>
          )}
        </>
      )}

      {deleteTarget && (
        <div className="support-alert-backdrop" role="presentation">
          <div className="support-alert" role="dialog" aria-modal="true" aria-labelledby="support-delete-title">
            <h3 id="support-delete-title">저장된 추천사업을 삭제할까요?</h3>
            <p>{deleteTarget.title} 항목이 지난 추천 목록에서 삭제됩니다.</p>
            <div>
              <button onClick={closeDeleteAlert} type="button">취소</button>
              <button onClick={confirmDelete} type="button">삭제</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
