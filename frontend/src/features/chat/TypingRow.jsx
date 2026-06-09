import { AgentAvatar } from '../../shared/components/AgentAvatar'

export const TypingRow = ({ agent }) => (
  <div className="chat-row agent typing-row">
    <AgentAvatar id={agent} active />
    <div className="typing-dots"><span /><span /><span /></div>
  </div>
)
