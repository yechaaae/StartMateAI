const AGENT_NAME_TO_KEY = {
  ProfileAgent: 'profile',
  IdeaAgent: 'idea',
  FinanceAgent: 'finance',
  PolicyAgent: 'policy',
  PlanAgent: 'plan',
  OperationAgent: 'operation',
  MarketingAgent: 'marketing',
  CommercialAreaAgent: 'commercial_area',
  LegalAgent: 'legal',
  OrchestratorAgent: 'plan',
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
  commercial_area: 'commercial_area',
  commercialarea: 'commercial_area',
  commercialareaagent: 'commercial_area',
  commercial_area_agent: 'commercial_area',
  locationagent: 'commercial_area',
  location_agent: 'commercial_area',
  legal: 'legal',
  legalagent: 'legal',
  legal_agent: 'legal',
  lawagent: 'legal',
  law_agent: 'legal',
  orchestrator: 'plan',
  orchestratoragent: 'plan',
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
  return null
}

const normalizeAgentDescriptor = (agent) => {
  if (!agent) return null
  return {
    key: resolveAgentKey(agent.agentKey, agent.label),
    agentKey: agent.agentKey ?? '',
    label: agent.label ?? '',
    role: agent.role ?? '',
    status: agent.status ?? '',
  }
}

const inferProgressViewType = (metadata) => {
  const explicit = metadata.viewType ?? metadata.type ?? metadata.progressType ?? ''
  if (explicit) return String(explicit).toLowerCase()

  const eventType = String(metadata.eventType ?? '').toLowerCase()
  if (eventType === 'agent.completed') return 'result'
  if (eventType === 'orchestrator.synthesizing') return 'discussion'
  return ''
}

const inferEventViewType = (agentProgress) => {
  const explicit = agentProgress.viewType ?? agentProgress.type ?? ''
  if (explicit) {
    return String(explicit).toLowerCase()
  }

  const eventType = String(agentProgress.eventType ?? '').toLowerCase()
  if (eventType === 'agent.completed') return 'result'
  if (eventType === 'orchestrator.synthesizing') return 'discussion'
  return 'status'
}

export const normalizeChatMessage = (message) => {
  const metadata = parseMetadata(message.metadata)
  const selectedAgents = Array.isArray(metadata.selectedAgents)
    ? metadata.selectedAgents.map(normalizeAgentDescriptor).filter(Boolean)
    : []

  return {
    id: message.messageId,
    role: message.senderType === 'USER' ? 'user' : 'agent',
    senderType: message.senderType,
    userId: message.userId ?? null,
    agentId: message.agentId ?? null,
    agent: resolveAgentKey(metadata.agentKey, metadata.agentLabel, metadata.agent),
    agentLabel: metadata.agentLabel ?? metadata.agent ?? '',
    text: message.content,
    metadata,
    progressMessage: metadata.progressMessage === true,
    progressType: inferProgressViewType(metadata),
    progressStatus: metadata.progressStatus ?? '',
    progressRole: metadata.progressRole ?? '',
    requestId: metadata.requestId ?? '',
    sequence: metadata.sequence ?? null,
    orchestrator: metadata.orchestrator ?? '',
    selectedAgents,
    progressDetail: metadata.detail ?? null,
    progressSourceAgent: resolveAgentKey(
      metadata.detail?.sourceAgentKey,
      metadata.detail?.source_intent,
      metadata.detail?.sourceAgent,
    ),
    progressTargetAgent: resolveAgentKey(
      metadata.detail?.targetAgentKey,
      metadata.detail?.target_intent,
      metadata.detail?.targetAgent,
    ),
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
  const fallbackAgent = agentProgress.agent ?? (
    agentProgress.orchestrator
      ? {
          agentKey: agentProgress.orchestrator,
          label: 'Orchestrator',
          role: 'Agent coordination',
          status: agentProgress.status ?? 'running',
        }
      : null
  )

  const selectedAgents = Array.isArray(agentProgress.selectedAgents)
    ? agentProgress.selectedAgents.map(normalizeAgentDescriptor).filter(Boolean)
    : []

  return {
    requestId: agentProgress.requestId,
    status: agentProgress.status ?? 'PROCESSING',
    targetFeature: agentProgress.targetFeature ?? '',
    eventType: agentProgress.eventType ?? '',
    type: (agentProgress.type ?? '').toLowerCase(),
    viewType: inferEventViewType(agentProgress),
    orchestrator: agentProgress.orchestrator ?? '',
    sequence: agentProgress.sequence ?? 0,
    message: agentProgress.message ?? '',
    agent: normalizeAgentDescriptor(fallbackAgent),
    selectedAgents,
    detail: agentProgress.detail ?? {},
  }
}

export const normalizeAgentProgressMessage = (agentProgress) => {
  const metadata = {
    agent: agentProgress.agent?.agentKey ?? '',
    agentKey: agentProgress.agent?.agentKey ?? '',
    agentLabel: agentProgress.agent?.label ?? '',
    eventType: agentProgress.eventType ?? '',
    type: agentProgress.type ?? agentProgress.viewType ?? '',
    viewType: agentProgress.viewType ?? agentProgress.type ?? '',
    progressType: agentProgress.eventType ?? '',
    progressStatus: agentProgress.agent?.status ?? agentProgress.status ?? '',
    progressRole: agentProgress.agent?.role ?? '',
    requestId: agentProgress.requestId,
    sequence: agentProgress.sequence,
    orchestrator: agentProgress.orchestrator ?? '',
    selectedAgents: agentProgress.selectedAgents ?? [],
    detail: agentProgress.detail ?? {},
    progressMessage: true,
  }

  return {
    id: `progress-${agentProgress.requestId}-${agentProgress.sequence}`,
    role: 'agent',
    senderType: 'AGENT',
    userId: null,
    agentId: null,
    agent: agentProgress.agent?.key ?? null,
    agentLabel: agentProgress.agent?.label ?? '',
    text: agentProgress.message || 'Agent is working on the request.',
    metadata,
    progressMessage: true,
    progressType: inferProgressViewType(metadata),
    progressStatus: metadata.progressStatus,
    progressRole: metadata.progressRole,
    requestId: metadata.requestId,
    sequence: metadata.sequence,
    orchestrator: metadata.orchestrator,
    selectedAgents: agentProgress.selectedAgents ?? [],
    progressDetail: metadata.detail,
    progressSourceAgent: resolveAgentKey(
      metadata.detail?.sourceAgentKey,
      metadata.detail?.source_intent,
      metadata.detail?.sourceAgent,
    ),
    progressTargetAgent: resolveAgentKey(
      metadata.detail?.targetAgentKey,
      metadata.detail?.target_intent,
      metadata.detail?.targetAgent,
    ),
    createdAt: null,
  }
}

export const upsertMessage = (messages, nextMessage) => {
  const existingIndex = messages.findIndex((message) => message.id === nextMessage.id)
  if (existingIndex < 0) return [...messages, nextMessage]

  const copy = [...messages]
  copy[existingIndex] = { ...copy[existingIndex], ...nextMessage }
  return copy
}
