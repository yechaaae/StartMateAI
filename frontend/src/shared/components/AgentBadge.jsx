import { agents } from '../data/agents'
import { Icon } from './Icon'

export const AgentBadge = ({ id }) => {
  const agent = agents[id]
  return (
    <div className="agent-badge">
      <span style={{ background: agent.color }}><Icon name={agent.icon} size={14} /></span>
      <b>{agent.name}</b>
    </div>
  )
}
