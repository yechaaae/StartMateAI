import { agents } from '../data/agents'
import { Icon } from './Icon'

export const AgentAvatar = ({ id, size = 34, active = false }) => {
  const agent = agents[id] || agents.idea
  return (
    <div className={active ? 'agent-avatar active' : 'agent-avatar'} style={{ width: size, height: size, color: active ? '#fff' : agent.color, background: active ? agent.color : agent.tint }}>
      <Icon name={agent.icon} size={size * 0.56} />
    </div>
  )
}
