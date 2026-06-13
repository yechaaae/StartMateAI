import { useEffect, useState } from 'react'
import { AgentAvatar } from '../../../shared/components/AgentAvatar'

const STEPS = [
  '공고 요건을 분석하고 있어요',
  '창업 아이템과 프로필을 검토하고 있어요',
  '사회적 가치와 지원동기를 정리하고 있어요',
  '신청서 항목에 맞춰 초안을 작성하고 있어요',
]

// 공고로 사업계획서(신청 항목)를 '작성하는 척' 보여주는 로딩 화면.
// durationMs 동안 단계 메시지와 진행바를 채운 뒤 부모가 결과로 전환한다.
export const PlanWritingState = ({ agentId, durationMs = 10000 }) => {
  const [step, setStep] = useState(0)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const tick = 100
    let elapsed = 0
    const timer = window.setInterval(() => {
      elapsed += tick
      const ratio = Math.min(1, elapsed / durationMs)
      setProgress(Math.round(ratio * 100))
      setStep(Math.min(STEPS.length - 1, Math.floor(ratio * STEPS.length)))
      if (ratio >= 1) {
        window.clearInterval(timer)
      }
    }, tick)
    return () => window.clearInterval(timer)
  }, [durationMs])

  return (
    <div className="ai-report-state plan-writing-state">
      <AgentAvatar id={agentId} size={56} active />
      <h2>{STEPS[step]}</h2>
      <p>공고에 맞춰 사업계획서 신청 항목을 작성하고 있어요. 잠시만 기다려 주세요.</p>
      <div className="generating-progress"><span style={{ width: `${progress}%` }} /></div>
    </div>
  )
}
