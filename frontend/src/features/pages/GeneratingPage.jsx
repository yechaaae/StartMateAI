import { useEffect, useRef, useState } from 'react'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import {
  createChatEventSource,
  getChatMessages,
  getFeatureChatRoom,
  sendChatMessage,
} from '../chat/chatApi'
import { normalizeChatMessage, reportDataFromMessage } from '../chat/chatMappers'
import { buildCurrentResult, buildFeatureSeed } from './featureChatContext'

const GENERATE_REPORT_PROMPT = '현재 기능 페이지에 표시할 최종 리포트를 각 Agent가 함께 검토해서 생성해줘.'

const STATUS_STEPS = [
  '입력하신 정보를 정리하고 있어요',
  '창업 프로필을 분석하고 있어요',
  'Agent들이 어울리는 아이템을 찾고 있어요',
  '추천 결과를 다듬고 있어요',
]

const TIMEOUT_MS = 45000
const STEP_INTERVAL_MS = 2600

// 온보딩 직후 아이템 추천 리포트를 미리 생성하고, 완료되면 아이템 결과 화면으로 넘긴다.
export const GeneratingPage = ({ go, user, startupProfile }) => {
  const [stepIndex, setStepIndex] = useState(0)
  const sentRef = useRef(false)

  useEffect(() => {
    let cancelled = false
    let eventSource = null

    const finish = () => {
      if (cancelled) return
      cancelled = true
      go('item')
    }

    const hasReport = (messages) => (messages ?? [])
      .map(normalizeChatMessage)
      .some((message) => reportDataFromMessage(message, 'item'))

    const run = async () => {
      const room = await getFeatureChatRoom('ITEM')
      if (cancelled) return
      const roomId = room.roomId

      // 이미 생성된 결과가 있으면 즉시 통과
      try {
        const history = await getChatMessages(roomId)
        if (cancelled) return
        if (hasReport(history.messages)) {
          finish()
          return
        }
      } catch {
        // 히스토리 조회 실패는 무시하고 계속 진행
      }

      eventSource = createChatEventSource(roomId)
      eventSource.addEventListener('chat-message', (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (!payload.message) return
          if (reportDataFromMessage(normalizeChatMessage(payload.message), 'item')) {
            finish()
          }
        } catch {
          // 개별 이벤트 파싱 실패는 무시
        }
      })

      // 생성 요청은 한 번만 (StrictMode 재마운트 대비)
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
          metadata: JSON.stringify({
            source: 'generating-page',
            featureId: 'item',
            hidden: true,
            reportGeneration: true,
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

    run().catch(() => finish())

    const timeoutId = window.setTimeout(finish, TIMEOUT_MS)
    const stepTimer = window.setInterval(() => {
      setStepIndex((index) => Math.min(index + 1, STATUS_STEPS.length - 1))
    }, STEP_INTERVAL_MS)

    return () => {
      cancelled = true
      if (eventSource) eventSource.close()
      window.clearTimeout(timeoutId)
      window.clearInterval(stepTimer)
    }
  }, [go, user, startupProfile])

  const progress = Math.round(((stepIndex + 1) / STATUS_STEPS.length) * 100)

  return (
    <main className="loading-page generating-page">
      <AgentAvatar id="idea" size={64} active />
      <h2>{STATUS_STEPS[stepIndex]}</h2>
      <p>잠시만요, 입력하신 정보로 딱 맞는 창업 아이템을 추천하고 있어요.</p>
      <div className="generating-progress">
        <span style={{ width: `${progress}%` }} />
      </div>
    </main>
  )
}
