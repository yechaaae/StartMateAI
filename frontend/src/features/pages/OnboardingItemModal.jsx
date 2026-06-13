import { useEffect, useRef, useState } from 'react'
import { Icon } from '../../shared/components/Icon'
import { ItemEntryChoice } from '../reports/ItemEntryChoice'
import { ItemInputForm } from '../reports/ItemInputForm'
import {
  createChatEventSource,
  getChatMessages,
  getFeatureChatRoom,
  sendChatMessage,
} from '../chat/chatApi'
import { normalizeChatMessage, reportDataFromMessage } from '../chat/chatMappers'
import { buildCurrentResult, buildFeatureSeed } from './featureChatContext'

const GENERATE_REPORT_PROMPT = '현재 기능 페이지에 표시할 최종 리포트를 각 Agent가 함께 검토해서 생성해줘.'

const LOADING_STEPS = [
  '입력하신 정보를 정리하고 있어요',
  '창업 프로필을 분석하고 있어요',
  'Agent들이 어울리는 아이템을 찾고 있어요',
  '추천 결과를 다듬고 있어요',
]

const TIMEOUT_MS = 45000

// 온보딩 직후 모달 흐름: 선택(추천/직접입력) → (추천) 생성 로딩 → 추천 목록 → 최종 선택.
// 최종 선택 시 onSelect(item)으로 워크스페이스를 만든다.
export const OnboardingItemModal = ({ stage, user, startupProfile, onSelect, onClose }) => {
  const [step, setStep] = useState('choice') // choice | loading | list | input | refine
  const [items, setItems] = useState([])
  const [report, setReport] = useState(null) // 선택 시 자동 저장에 쓸 전체 reportData
  const [error, setError] = useState('')
  const [loadingStep, setLoadingStep] = useState(0)
  const [refineText, setRefineText] = useState('') // 재추천 방향 입력값
  const sentRef = useRef(false)
  const directionRef = useRef('') // 다음 생성에 반영할 재추천 방향
  const forceFreshRef = useRef(false) // true면 히스토리 재사용 없이 새로 생성

  // 추천 생성: 아이템 채팅방 → SSE → 생성 요청 → reportData 도착 시 목록으로.
  useEffect(() => {
    if (step !== 'loading') {
      return undefined
    }
    let cancelled = false
    let eventSource = null

    const finishWith = (reportData) => {
      if (cancelled) return
      setReport(reportData ?? null)
      setItems(reportData?.items ?? [])
      setStep('list')
    }

    const run = async () => {
      const room = await getFeatureChatRoom('ITEM')
      if (cancelled) return
      const roomId = room.roomId

      // 재추천(forceFresh)일 땐 과거 결과를 재사용하지 않고 항상 새로 생성한다.
      if (!forceFreshRef.current) {
        try {
          const history = await getChatMessages(roomId)
          if (cancelled) return
          const existing = (history.messages ?? [])
            .map(normalizeChatMessage)
            .map((message) => reportDataFromMessage(message, 'item'))
            .find(Boolean)
          if (existing) {
            finishWith(existing)
            return
          }
        } catch {
          /* 히스토리 조회 실패는 무시 */
        }
      }

      eventSource = createChatEventSource(roomId)
      eventSource.addEventListener('chat-message', (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (!payload.message) return
          const reportData = reportDataFromMessage(normalizeChatMessage(payload.message), 'item')
          if (reportData) finishWith(reportData)
        } catch {
          /* 개별 이벤트 파싱 실패는 무시 */
        }
      })

      if (!sentRef.current) {
        sentRef.current = true
        const direction = directionRef.current.trim()
        forceFreshRef.current = false
        const seed = buildFeatureSeed('item', {})
        const currentResult = buildCurrentResult({
          featureId: 'item',
          data: seed.data,
          selectedIdeaRank: null,
          startupProfile,
          workspaceContext: {},
        })
        await sendChatMessage(roomId, {
          userId: user?.id ?? null,
          content: direction ? `${GENERATE_REPORT_PROMPT}\n\n재추천 방향: ${direction}` : GENERATE_REPORT_PROMPT,
          metadata: JSON.stringify({
            source: 'onboarding-modal',
            featureId: 'item',
            hidden: true,
            reportGeneration: true,
            ...(direction ? { reportGuidance: direction } : {}),
          }),
          intent: 'auto',
          sessionType: 'FEATURE_CHAT',
          currentResultType: 'IDEA_REPORT',
          currentResultId: null,
          selectedIdeaId: null,
          candidateAgents: [],
          currentResult,
        })
      }
    }

    run().catch(() => {
      if (!cancelled) setError('추천을 불러오지 못했어요. 다시 시도해주세요.')
    })

    const timeoutId = window.setTimeout(() => {
      if (!cancelled) setError((prev) => prev || '시간이 초과됐어요. 다시 시도해주세요.')
    }, TIMEOUT_MS)

    return () => {
      cancelled = true
      if (eventSource) eventSource.close()
      window.clearTimeout(timeoutId)
    }
  }, [step, user, startupProfile])

  // 로딩 문구 회전
  useEffect(() => {
    if (step !== 'loading') return undefined
    const timer = window.setInterval(() => {
      setLoadingStep((index) => Math.min(index + 1, LOADING_STEPS.length - 1))
    }, 2600)
    return () => window.clearInterval(timer)
  }, [step])

  const retry = () => {
    sentRef.current = false
    setError('')
    setItems([])
    setReport(null)
    setLoadingStep(0)
    setStep('loading')
  }

  // 사용자가 입력한 방향으로(히스토리 무시) 새로 재추천한다.
  const submitRefine = () => {
    directionRef.current = refineText.trim()
    forceFreshRef.current = true
    retry()
  }

  const progress = Math.round(((loadingStep + 1) / LOADING_STEPS.length) * 100)

  return (
    <div className="onboarding-modal-backdrop">
      <div className="onboarding-modal" role="dialog" aria-modal="true">
        {onClose && (
          <button type="button" className="onboarding-modal-close" onClick={onClose} aria-label="닫기">
            <Icon name="plus" size={18} style={{ transform: 'rotate(45deg)' }} />
          </button>
        )}

        {step === 'choice' && (
          <ItemEntryChoice
            stage={stage}
            onChooseRecommend={() => setStep('loading')}
            onChooseInput={() => setStep('input')}
          />
        )}

        {step === 'loading' && (
          error ? (
            <div className="onboarding-modal-state">
              <h2>{error}</h2>
              <div className="onboarding-modal-actions">
                <button type="button" className="om-secondary" onClick={() => setStep('choice')}>이전</button>
                <button type="button" className="om-primary" onClick={retry}>다시 시도</button>
              </div>
            </div>
          ) : (
            <div className="onboarding-modal-state">
              <Icon name="sparkle" size={40} />
              <h2>{LOADING_STEPS[loadingStep]}</h2>
              <p>잠시만요, 입력하신 정보로 딱 맞는 창업 아이템을 추천하고 있어요.</p>
              <div className="generating-progress"><span style={{ width: `${progress}%` }} /></div>
            </div>
          )
        )}

        {step === 'list' && (
          <div className="onboarding-modal-list">
            <div className="onboarding-modal-head">
              <h2>추천 아이템을 골라보세요</h2>
              <p>마음에 드는 아이템을 선택하면 그 아이템으로 워크스페이스가 만들어져요.</p>
            </div>
            {items.length === 0 && <p className="onboarding-modal-empty">추천 결과가 없어요. 다시 시도하거나 직접 입력해 주세요.</p>}
            <div className="onboarding-modal-items">
              {items.map((item, index) => (
                <button
                  type="button"
                  className="onboarding-modal-item"
                  key={`${item.rank ?? index}-${item.title}`}
                  onClick={() => onSelect?.(item, report)}
                >
                  <span className="omi-rank">{item.rank ?? index + 1}</span>
                  <span className="omi-body">
                    <b>{item.title}</b>
                    <small>{item.reason}</small>
                  </span>
                  {item.score != null && <em className="omi-score">적합도 {item.score}</em>}
                  <Icon name="arrow" size={16} />
                </button>
              ))}
            </div>
            <div className="onboarding-modal-actions">
              <button type="button" className="om-secondary" onClick={() => setStep('choice')}>처음으로</button>
              <button type="button" className="om-secondary" onClick={() => { setRefineText(''); setStep('refine') }}>다시 추천</button>
            </div>
          </div>
        )}

        {step === 'refine' && (
          <div className="onboarding-modal-refine">
            <button type="button" className="item-input-back" onClick={() => setStep('list')}>
              <Icon name="arrow" size={14} style={{ transform: 'rotate(180deg)' }} /> 추천 목록으로
            </button>
            <div className="onboarding-modal-head">
              <h2>어떤 방향으로 다시 추천할까요?</h2>
              <p>원하는 방향을 적어주면 그 방향에 맞춰 다시 추천해드려요. 비워두면 조건을 바꿔 새로 추천합니다.</p>
            </div>
            <textarea
              className="onboarding-refine-input"
              value={refineText}
              onChange={(event) => setRefineText(event.target.value)}
              placeholder="예: 초기비용을 더 낮춰서 / 온라인 중심으로 / 푸드 말고 서비스업으로 / 주말에만 운영 가능한 걸로"
              rows={3}
            />
            <div className="onboarding-modal-actions">
              <button type="button" className="om-secondary" onClick={() => setStep('list')}>취소</button>
              <button type="button" className="om-primary" onClick={submitRefine}>이 방향으로 다시 추천</button>
            </div>
          </div>
        )}

        {step === 'input' && (
          <ItemInputForm
            prefill={{
              itemName: startupProfile?.currentItemName ?? '',
              industry: startupProfile?.currentIndustry ?? '',
              region: startupProfile?.businessRegion ?? '',
            }}
            onSubmit={onSelect}
            onBack={() => setStep('choice')}
          />
        )}
      </div>
    </div>
  )
}
