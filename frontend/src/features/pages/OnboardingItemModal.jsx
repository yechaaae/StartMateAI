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
  const [step, setStep] = useState('choice') // choice | loading | list | input
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [loadingStep, setLoadingStep] = useState(0)
  const sentRef = useRef(false)

  // 추천 생성: 아이템 채팅방 → SSE → 생성 요청 → reportData 도착 시 목록으로.
  useEffect(() => {
    if (step !== 'loading') {
      return undefined
    }
    let cancelled = false
    let eventSource = null

    const finishWith = (nextItems) => {
      if (cancelled) return
      setItems(nextItems ?? [])
      setStep('list')
    }

    const run = async () => {
      const room = await getFeatureChatRoom('ITEM')
      if (cancelled) return
      const roomId = room.roomId

      try {
        const history = await getChatMessages(roomId)
        if (cancelled) return
        const existing = (history.messages ?? [])
          .map(normalizeChatMessage)
          .map((message) => reportDataFromMessage(message, 'item'))
          .find(Boolean)
        if (existing) {
          finishWith(existing.items)
          return
        }
      } catch {
        /* 히스토리 조회 실패는 무시 */
      }

      eventSource = createChatEventSource(roomId)
      eventSource.addEventListener('chat-message', (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (!payload.message) return
          const reportData = reportDataFromMessage(normalizeChatMessage(payload.message), 'item')
          if (reportData) finishWith(reportData.items)
        } catch {
          /* 개별 이벤트 파싱 실패는 무시 */
        }
      })

      if (!sentRef.current) {
        sentRef.current = true
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
          content: GENERATE_REPORT_PROMPT,
          metadata: JSON.stringify({ source: 'onboarding-modal', featureId: 'item', hidden: true, reportGeneration: true }),
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
    setLoadingStep(0)
    setStep('loading')
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
                  onClick={() => onSelect?.(item)}
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
              <button type="button" className="om-secondary" onClick={retry}>다시 추천</button>
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
