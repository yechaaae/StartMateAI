import { agents } from '../../shared/data/agents'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { Icon } from '../../shared/components/Icon'

export const ChatRow = ({ message }) => {
  if (message.role === 'user') return <div className="chat-row user"><div>{message.text}</div></div>
  const agent = agents[message.agent] ?? null
  const displayName = agent ? agent.name : 'AI 전문가'

  return (
    <div className="chat-row agent">
      {agent ? (
        <AgentAvatar id={message.agent} />
      ) : (
        <span className="chat-agent-placeholder">
          <Icon name="discuss" size={18} />
        </span>
      )}
      <div className="chat-copy">
        <strong style={agent ? { color: agent.color } : undefined}>{displayName}</strong>
        <p>{message.text}</p>
      </div>
    </div>
  )
}
