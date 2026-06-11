import { agents } from '../../shared/data/agents'

export const StatusProgressRow = ({ progress }) => {
  if (!progress?.message) {
    return null
  }

  const agent = agents[progress.agent?.key] || agents.idea
  const displayName = progress.agent?.label
    ? `${progress.agent.label} 에이전트`
    : `${agent.label} 에이전트`

  return (
    <div className="chat-progress-status" aria-live="polite">
      <span className="chat-progress-status-agent">{displayName}</span>
      <span className="chat-progress-status-message">{progress.message}</span>
    </div>
  )
}
