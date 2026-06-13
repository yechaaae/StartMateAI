import { useEffect, useState } from 'react'
import { AgentAvatar } from '../../../shared/components/AgentAvatar'

// 아이템 추천 생성 중 토스식 진행 화면 (회전 문구 + 진행바).
const STATUS_STEPS = [
  '입력하신 정보를 정리하고 있어요',
  '창업 프로필을 분석하고 있어요',
  'Agent들이 어울리는 아이템을 찾고 있어요',
  '추천 결과를 다듬고 있어요',
]

export const ItemGeneratingState = ({ agentId }) => {
  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    const timer = window.setInterval(() => {
      setStepIndex((index) => Math.min(index + 1, STATUS_STEPS.length - 1))
    }, 2600)
    return () => window.clearInterval(timer)
  }, [])

  const progress = Math.round(((stepIndex + 1) / STATUS_STEPS.length) * 100)

  return (
    <div className="ai-report-state item-generating">
      <AgentAvatar id={agentId} size={56} active />
      <h2>{STATUS_STEPS[stepIndex]}</h2>
      <p>잠시만요, 입력하신 정보로 딱 맞는 창업 아이템을 추천하고 있어요.</p>
      <div className="generating-progress">
        <span style={{ width: `${progress}%` }} />
      </div>
    </div>
  )
}
