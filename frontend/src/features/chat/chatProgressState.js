const buildProgressKey = (requestId, agentKey) => `${requestId}:${agentKey}`

const normalizeSequence = (value, fallback = 0) => {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  return fallback
}

const cloneMap = (progressMap) => new Map(progressMap ?? [])

const sortProgresses = (progresses) => (
  [...progresses].sort((left, right) => {
    const sequenceGap = normalizeSequence(left.sequence) - normalizeSequence(right.sequence)
    if (sequenceGap !== 0) return sequenceGap
    return String(left.id).localeCompare(String(right.id))
  })
)

const buildQueuedMessage = (agent) => `${agent.label}가 곧 검토를 시작할 예정이에요.`

const buildAgentProgressEntry = (progress, agent, message) => ({
  id: buildProgressKey(progress.requestId, agent.agentKey ?? agent.key ?? 'profile'),
  requestId: progress.requestId,
  sequence: normalizeSequence(progress.sequence),
  eventType: progress.eventType,
  viewType: progress.viewType,
  status: progress.status,
  message,
  agent: {
    key: agent.key ?? 'profile',
    agentKey: agent.agentKey ?? '',
    label: agent.label ?? '',
    role: agent.role ?? '',
    status: agent.status ?? '',
  },
})

const removeByRequestId = (progressMap, requestId) => {
  const next = cloneMap(progressMap)
  for (const [key, value] of next.entries()) {
    if (value.requestId === requestId) {
      next.delete(key)
    }
  }
  return next
}

export const clearActiveProgressByRequest = (progressMap, requestId) => removeByRequestId(progressMap, requestId)

export const upsertActiveProgress = (progressMap, progress) => {
  if (!progress?.requestId) return cloneMap(progressMap)

  if (String(progress.status ?? '').toUpperCase() === 'COMPLETED') {
    return removeByRequestId(progressMap, progress.requestId)
  }

  const next = cloneMap(progressMap)
  const agent = progress.agent
  const eventType = String(progress.eventType ?? '').toLowerCase()

  if (eventType === 'agents.selected' && Array.isArray(progress.selectedAgents)) {
    for (const selectedAgent of progress.selectedAgents) {
      if (!selectedAgent?.agentKey) continue
      const queuedEntry = buildAgentProgressEntry(
        progress,
        { ...selectedAgent, status: selectedAgent.status || 'queued' },
        buildQueuedMessage(selectedAgent),
      )
      next.set(queuedEntry.id, queuedEntry)
    }
    return next
  }

  if (!agent?.agentKey) {
    return next
  }

  const entryId = buildProgressKey(progress.requestId, agent.agentKey)

  if (eventType === 'agent.completed' || eventType === 'agent.failed' || String(agent.status ?? '').toLowerCase() === 'completed') {
    next.delete(entryId)
    return next
  }

  next.set(entryId, buildAgentProgressEntry(progress, agent, progress.message))
  return next
}

export const listActiveProgresses = (progressMap) => sortProgresses(Array.from((progressMap ?? new Map()).values()))

export const resolveTypingAgent = (progresses, fallbackAgent = null) => {
  const latest = sortProgresses(progresses).at(-1) ?? null
  return latest?.agent?.key ?? fallbackAgent
}
