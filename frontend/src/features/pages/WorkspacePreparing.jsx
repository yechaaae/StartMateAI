import { useEffect, useState } from 'react'
import { AgentAvatar } from '../../shared/components/AgentAvatar'

// 아이템 선택 직후, 워크스페이스를 만들고 진입하기 전 짧은 준비 화면(토스식).
const STEPS = [
  '선택한 아이템을 정리하고 있어요',
  '워크스페이스를 만들고 있어요',
  '곧 시작할게요',
]

export const WorkspacePreparing = ({ itemTitle }) => {
  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    const timer = window.setInterval(() => {
      setStepIndex((index) => Math.min(index + 1, STEPS.length - 1))
    }, 700)
    return () => window.clearInterval(timer)
  }, [])

  const progress = Math.round(((stepIndex + 1) / STEPS.length) * 100)

  return (
    <main className="loading-page generating-page">
      <AgentAvatar id="idea" size={64} active />
      <h2>{STEPS[stepIndex]}</h2>
      <p>{itemTitle ? `「${itemTitle}」 워크스페이스를 준비하고 있어요.` : '워크스페이스를 준비하고 있어요.'}</p>
      <div className="generating-progress">
        <span style={{ width: `${progress}%` }} />
      </div>
    </main>
  )
}
