import { agents } from '../../shared/data/agents'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { Icon } from '../../shared/components/Icon'

const PROGRESS_LABELS = {
  discussion: '의견 조율 중',
  result: '분석 결과',
  argument: '의견 제시',
  challenge: '이견 제기',
  revision: '의견 수정',
  consensus: '합의 정리',
}

const DETAIL_FIELD_LABELS = {
  issue: '쟁점',
  basis: '근거',
  proposal: '제안',
  position: '입장',
  recommendation: '권장',
}

const getAgentDisplayName = (message, agent) => (
  message.agentLabel || agent?.name || 'AI Expert'
)

const getRelatedAgentLabel = (message) => {
  const relatedAgentKey = message.progressTargetAgent || message.progressSourceAgent
  if (!relatedAgentKey || relatedAgentKey === message.agent) {
    return ''
  }
  const relatedAgent = agents[relatedAgentKey]
  return relatedAgent?.name || ''
}

const getProgressHeadline = (message, agent) => {
  const displayName = getAgentDisplayName(message, agent)
  const relatedLabel = getRelatedAgentLabel(message)

  if (message.progressType === 'challenge' && relatedLabel) {
    return `${displayName} -> ${relatedLabel}`
  }

  return displayName
}

const getProgressSubLabel = (message) => {
  if (message.progressType === 'challenge' && getRelatedAgentLabel(message)) {
    return '질문을 다시 검토하며 반박 의견을 주고받는 중'
  }

  return PROGRESS_LABELS[message.progressType] || '에이전트 대화'
}

const getDetailHighlights = (detail) => {
  if (!detail || typeof detail !== 'object') return []

  return Object.entries(DETAIL_FIELD_LABELS)
    .map(([key, label]) => {
      const value = detail[key]
      if (typeof value !== 'string' || !value.trim()) return null
      return { key, label, value: value.trim() }
    })
    .filter(Boolean)
}

const ProgressConversationRow = ({ message, agent }) => {
  const displayName = getProgressHeadline(message, agent)
  const subLabel = getProgressSubLabel(message)
  const selectedAgents = (message.selectedAgents || [])
    .filter((item) => item?.key && item.key !== message.agent)
    .slice(0, 4)
  const highlights = getDetailHighlights(message.progressDetail).slice(0, 3)

  return (
    <div className={`chat-row agent chat-row-progress chat-row-progress-${message.progressType || 'discussion'}`}>
      {agent ? (
        <AgentAvatar id={message.agent} />
      ) : (
        <span className="chat-agent-placeholder">
          <Icon name="discuss" size={18} />
        </span>
      )}
      <div className="chat-copy chat-progress-copy">
        <div className="chat-progress-head">
          <strong style={agent ? { color: agent.color } : undefined}>{displayName}</strong>
          <span>{subLabel}</span>
        </div>
        <p>{message.text}</p>

        {selectedAgents.length > 0 && (
          <div className="chat-progress-agents">
            {selectedAgents.map((item) => (
              <span key={`${message.id}-${item.agentKey || item.label}`}>
                {item.label || item.agentKey}
              </span>
            ))}
          </div>
        )}

        {highlights.length > 0 && (
          <div className="chat-progress-highlights">
            {highlights.map((item) => (
              <div key={`${message.id}-${item.key}`}>
                <b>{item.label}</b>
                <span>{item.value}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export const ChatRow = ({ message }) => {
  if (message.role === 'user') return <div className="chat-row user"><div>{message.text}</div></div>

  const agent = agents[message.agent] ?? null
  const displayName = getAgentDisplayName(message, agent)
  const isProgressConversation = message.progressMessage && message.progressType && message.progressType !== 'status'

  if (isProgressConversation) {
    return <ProgressConversationRow message={message} agent={agent} />
  }

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
