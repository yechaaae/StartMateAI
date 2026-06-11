import { agents } from '../../shared/data/agents'
import { AgentAvatar } from '../../shared/components/AgentAvatar'

export const ChatRow = ({ message }) => {
  if (message.role === 'user') return <div className="chat-row user"><div>{message.text}</div></div>
  const agent = agents[message.agent] || agents.idea
  const displayName = `${agent.label} 에이전트`

  return (
    <div className="chat-row agent">
      <AgentAvatar id={message.agent} />
      <div className="chat-copy">
        <strong style={{ color: agent.color }}>{displayName}</strong>
        <p>{message.text}</p>
      </div>
    </div>
  )
}
