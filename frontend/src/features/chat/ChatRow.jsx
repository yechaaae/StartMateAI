import { agents } from '../../shared/data/agents'
import { features } from '../../shared/data/features'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { Icon } from '../../shared/components/Icon'
import { ChatMarkdown } from './ChatMarkdown'

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
        <ChatMarkdown text={message.text} />

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

const ReportCard = ({ card, onOpenReport }) => {
  const feature = features[card.featureId]
  const title = card.title || feature?.title || 'AI 리포트'
  const summary = card.summary || ''
  const bullets = Array.isArray(card.bullets) ? card.bullets.filter(Boolean).slice(0, 4) : []
  const canOpen = Boolean(card.featureId && onOpenReport)

  return (
    <div className="chat-report-card">
      <div className="chat-report-card-head">
        <span>{feature?.title || card.reportType || 'AI 리포트'}</span>
        <strong>{title}</strong>
      </div>
      {summary && <p>{summary}</p>}
      {bullets.length > 0 && (
        <ul>
          {bullets.map((item, index) => <li key={`${title}-${index}`}>{item}</li>)}
        </ul>
      )}
      {canOpen && (
        <button type="button" onClick={() => onOpenReport(card.featureId)}>
          <span>{card.ctaLabel || '리포트 보러가기'}</span>
          <Icon name="arrow" size={14} />
        </button>
      )}
    </div>
  )
}

const renderReportSection = (section, index) => {
  if (typeof section === 'string') {
    return (
      <section key={`section-${index}`}>
        <p>{section}</p>
      </section>
    )
  }

  if (!section || typeof section !== 'object') return null
  const items = Array.isArray(section.items) ? section.items.filter(Boolean) : []
  const body = section.body || section.text || ''

  return (
    <section key={`${section.title || 'section'}-${index}`}>
      {section.title && <h4>{section.title}</h4>}
      {body && <p>{body}</p>}
      {items.length > 0 && (
        <ul>
          {items.map((item, itemIndex) => <li key={`${section.title || index}-${itemIndex}`}>{item}</li>)}
        </ul>
      )}
    </section>
  )
}

const ReportBlock = ({ block }) => {
  const sections = Array.isArray(block.sections) ? block.sections : []

  return (
    <div className="chat-report-block">
      <div className="chat-report-block-head">
        <span>{block.reportType || 'custom'}</span>
        <strong>{block.title || 'AI 상담 리포트'}</strong>
      </div>
      {block.summary && <p className="chat-report-block-summary">{block.summary}</p>}
      {sections.map(renderReportSection)}
    </div>
  )
}

export const ChatRow = ({ message, onOpenReport }) => {
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
        {message.reportCard ? (
          <ReportCard card={message.reportCard} onOpenReport={onOpenReport} />
        ) : message.reportBlock ? (
          <ReportBlock block={message.reportBlock} />
        ) : (
          <ChatMarkdown text={message.text} />
        )}
      </div>
    </div>
  )
}
