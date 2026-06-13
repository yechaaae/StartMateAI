import { useEffect, useState } from 'react'
import { StatusProgressRow } from './StatusProgressRow'

const ROTATE_INTERVAL_MS = 2000

// 실행 중인 Agent 상태를 스택으로 모두 쌓지 않고, 한 번에 하나씩 돌아가며 보여줍니다.
// 완료된 Agent는 progresses 목록에서 빠지므로 자연스럽게 회전 대상에서 제외됩니다.
export const RotatingStatusProgress = ({ progresses }) => {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (progresses.length <= 1) {
      setIndex(0)
      return undefined
    }

    const timer = setInterval(() => {
      setIndex((prev) => (prev + 1) % progresses.length)
    }, ROTATE_INTERVAL_MS)

    return () => clearInterval(timer)
  }, [progresses.length])

  if (!progresses.length) {
    return null
  }

  const current = progresses[index % progresses.length]
  return <StatusProgressRow progress={current} />
}
