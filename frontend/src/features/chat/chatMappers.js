const AGENT_NAME_TO_KEY = {
  ProfileAgent: 'profile',
  IdeaAgent: 'idea',
  FinanceAgent: 'finance',
  PolicyAgent: 'policy',
  PlanAgent: 'plan',
  OperationAgent: 'operation',
  MarketingAgent: 'marketing',
}

const parseMetadata = (metadata) => {
  if (!metadata) return {}
  try {
    return JSON.parse(metadata)
  } catch {
    return {}
  }
}

export const normalizeChatMessage = (message) => {
  const metadata = parseMetadata(message.metadata)

  return {
    id: message.messageId,
    role: message.senderType === 'USER' ? 'user' : 'agent',
    senderType: message.senderType,
    userId: message.userId ?? null,
    agentId: message.agentId ?? null,
    agent: AGENT_NAME_TO_KEY[metadata.agent] ?? 'profile',
    text: message.content,
    metadata,
    createdAt: message.createdAt ?? null,
  }
}

export const normalizeStatusEvent = (status) => ({
  requestId: status.requestId,
  messageId: status.messageId,
  status: status.status,
  errorMessage: status.errorMessage ?? '',
  updatedAt: status.updatedAt ?? null,
})

export const upsertMessage = (messages, nextMessage) => {
  const existingIndex = messages.findIndex((message) => message.id === nextMessage.id)
  if (existingIndex < 0) return [...messages, nextMessage]

  const copy = [...messages]
  copy[existingIndex] = { ...copy[existingIndex], ...nextMessage }
  return copy
}
