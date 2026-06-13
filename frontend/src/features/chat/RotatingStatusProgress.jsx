import { useEffect, useState } from 'react'
import { StatusProgressRow } from './StatusProgressRow'

const ROTATE_INTERVAL_MS = 2000

const isOrchestrator = (progress) => {
  const agentKey = progress?.agent?.agentKey ?? ''
  const label = progress?.agent?.label ?? ''
  return /orchestrator/i.test(agentKey) || /orchestrator/i.test(label)
}

// Orchestrator는 위에 고정으로 보여주고(에이전트들을 부르는 역할),
// 그 아래에서 실제 실행 중인 Agent들을 하나씩 돌아가며 보여줍니다.
// 완료된 Agent는 progresses에서 빠지므로 회전 대상에서 자연히 제외됩니다.
export const RotatingStatusProgress = ({ progresses }) => {
  const orchestrator = progresses.find(isOrchestrator) ?? null
  const agentProgresses = progresses.filter((progress) => !isOrchestrator(progress))
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (agentProgresses.length <= 1) {
      setIndex(0)
      return undefined
    }

    const timer = setInterval(() => {
      setIndex((prev) => (prev + 1) % agentProgresses.length)
    }, ROTATE_INTERVAL_MS)

    return () => clearInterval(timer)
  }, [agentProgresses.length])

  if (!orchestrator && !agentProgresses.length) {
    return null
  }

  const currentAgent = agentProgresses.length
    ? agentProgresses[index % agentProgresses.length]
    : null

  return (
    <div className="chat-progress-stack">
      {orchestrator && <StatusProgressRow progress={orchestrator} variant="orchestrator" />}
      {currentAgent && <StatusProgressRow progress={currentAgent} />}
    </div>
  )
}
