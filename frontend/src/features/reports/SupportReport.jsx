import { useState } from 'react'
import { Card } from '../../shared/components/Card'
import { AgentReview } from './AgentReview'

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
          <h4>{program.title}</h4>
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
        <button onClick={onAction} type="button">
          {actionLabel}
        </button>
      </div>
    </article>
  )
}

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
  onDeleteSavedSupportProgram,
}) => {
  const [savedPage, setSavedPage] = useState(1)
  const [deleteTarget, setDeleteTarget] = useState(null)
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
      <AgentReview review={data.agentReview} />

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
          onClick={onRunSupportSearch}
          disabled={supportSearchLoading}
          type="button"
        >
          {supportSearchLoading ? '지원사업을 살펴보는 중...' : '추천 결과 확인하기'}
        </button>
      </Card>

      {(supportSearchLoading || supportHasSearched) && (
        <Card className="support-results-card">
          <div className="support-results-head">
            <div>
              <h3>최근 추천 결과</h3>
              <p>{supportSearchLoading ? '선택한 조건에 맞는 사업을 찾고 있습니다.' : '이번에 선택한 조건으로 정리한 추천 지원사업입니다.'}</p>
            </div>
            {supportSearchLoading && <span>확인 중</span>}
          </div>

          {supportSearchLoading && (
            <div className="support-loading-state">
              <b>조건에 맞는 지원사업을 찾고 있어요</b>
              <p>잠시 후 신청 가능성과 준비 난이도를 함께 확인할 수 있습니다.</p>
            </div>
          )}

          {!supportSearchLoading && supportHasSearched && (
            <div className="support-program-list">
              {(data.list ?? []).map((program) => (
                <SupportProgramCard
                  key={getProgramId(program)}
                  program={program}
                  selected={selectedSupportTitle === program.title}
                  actionLabel="이 공고로 사업계획서 작성"
                  onAction={() => {
                    onSelectSupport?.(program.title)
                    go('plan')
                  }}
                />
              ))}
            </div>
          )}
        </Card>
      )}

      <Card className="support-results-card">
        <div className="support-results-head">
          <div>
            <h3>지난 추천 목록</h3>
            <p>이전에 확인한 추천 지원사업을 다시 볼 수 있습니다. 필요 없는 항목은 목록에서 삭제하세요.</p>
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
                    go('plan')
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
