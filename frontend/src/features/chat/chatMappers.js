const AGENT_NAME_TO_KEY = {
  ProfileAgent: 'profile',
  IdeaAgent: 'idea',
  FinanceAgent: 'finance',
  PolicyAgent: 'policy',
  PlanAgent: 'plan',
  OperationAgent: 'operation',
  MarketingAgent: 'marketing',
}

const AGENT_TOKEN_TO_KEY = {
  profile: 'profile',
  profileagent: 'profile',
  intentagent: 'profile',
  idea: 'idea',
  ideaagent: 'idea',
  idea_agent: 'idea',
  marketagent: 'idea',
  market_agent: 'idea',
  finance: 'finance',
  financeagent: 'finance',
  finance_agent: 'finance',
  policy: 'policy',
  policyagent: 'policy',
  policy_agent: 'policy',
  fitagent: 'policy',
  fit_agent: 'policy',
  plan: 'plan',
  planagent: 'plan',
  operation: 'operation',
  operationagent: 'operation',
  opsagent: 'operation',
  ops_agent: 'operation',
  cxagent: 'operation',
  cx_agent: 'operation',
  simulation: 'finance',
  simulationagent: 'finance',
  simulation_agent: 'finance',
  riskagent: 'finance',
  risk_agent: 'finance',
  marketing: 'marketing',
  marketingagent: 'marketing',
  marketing_agent: 'marketing',
  copyagent: 'marketing',
  copy_agent: 'marketing',
  summaryagent: 'profile',
  summary_agent: 'profile',
  freechatagent: 'profile',
}

const parseMetadata = (metadata) => {
  if (!metadata) return {}
  try {
    return JSON.parse(metadata)
  } catch {
    return {}
  }
}

const resolveAgentKey = (...values) => {
  for (const value of values) {
    if (!value) continue
    const normalized = String(value).replace(/[\s-]+/g, '').toLowerCase()
    if (AGENT_TOKEN_TO_KEY[normalized]) return AGENT_TOKEN_TO_KEY[normalized]
    if (AGENT_TOKEN_TO_KEY[String(value).toLowerCase()]) return AGENT_TOKEN_TO_KEY[String(value).toLowerCase()]
    if (AGENT_NAME_TO_KEY[value]) return AGENT_NAME_TO_KEY[value]
  }
  return 'profile'
}

export const normalizeChatMessage = (message) => {
  const metadata = parseMetadata(message.metadata)

  return {
    id: message.messageId,
    role: message.senderType === 'USER' ? 'user' : 'agent',
    senderType: message.senderType,
    userId: message.userId ?? null,
    agentId: message.agentId ?? null,
    agent: resolveAgentKey(metadata.agent),
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

export const normalizeAgentProgressEvent = (agentProgress) => {
  const normalizeAgent = (agent) => {
    if (!agent) return null
    return {
      key: resolveAgentKey(agent.agentKey, agent.label),
      agentKey: agent.agentKey ?? '',
      label: agent.label ?? '',
      role: agent.role ?? '',
      status: agent.status ?? '',
    }
  }

  const selectedAgents = Array.isArray(agentProgress.selectedAgents)
    ? agentProgress.selectedAgents.map(normalizeAgent).filter(Boolean)
    : []

  return {
    requestId: agentProgress.requestId,
    status: agentProgress.status ?? 'PROCESSING',
    targetFeature: agentProgress.targetFeature ?? '',
    eventType: agentProgress.eventType ?? '',
    orchestrator: agentProgress.orchestrator ?? '',
    sequence: agentProgress.sequence ?? 0,
    message: agentProgress.message ?? '',
    agent: normalizeAgent(agentProgress.agent),
    selectedAgents,
  }
}

export const normalizeAgentProgressMessage = (agentProgress) => ({
  id: `progress-${agentProgress.requestId}-${agentProgress.sequence}`,
  role: 'agent',
  senderType: 'AGENT',
  userId: null,
  agentId: null,
  agent: agentProgress.agent?.key ?? 'profile',
  text: agentProgress.message || '에이전트가 작업 중입니다.',
  metadata: {
    agent: agentProgress.agent?.label ?? '',
    agentKey: agentProgress.agent?.agentKey ?? '',
    progressType: agentProgress.eventType ?? '',
    progressStatus: agentProgress.agent?.status ?? agentProgress.status ?? '',
    progressRole: agentProgress.agent?.role ?? '',
    requestId: agentProgress.requestId,
    sequence: agentProgress.sequence,
    orchestrator: agentProgress.orchestrator ?? '',
    progressMessage: true,
  },
  createdAt: null,
})

export const upsertMessage = (messages, nextMessage) => {
  const existingIndex = messages.findIndex((message) => message.id === nextMessage.id)
  if (existingIndex < 0) return [...messages, nextMessage]

  const copy = [...messages]
  copy[existingIndex] = { ...copy[existingIndex], ...nextMessage }
  return copy
}
