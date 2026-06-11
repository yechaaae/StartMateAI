import assert from 'node:assert/strict'
import test from 'node:test'

import { listActiveProgresses, resolveTypingAgent, upsertActiveProgress } from './chatProgressState.js'

test('upsertActiveProgress keeps queued and running agents until each one completes', () => {
  let state = new Map()

  state = upsertActiveProgress(state, {
    requestId: 'req-1',
    status: 'PROCESSING',
    eventType: 'agents.selected',
    viewType: 'status',
    sequence: 1,
    selectedAgents: [
      { key: 'idea', agentKey: 'IdeaAgent', label: '아이디어 Agent', role: '아이템 후보 탐색', status: 'queued' },
      { key: 'finance', agentKey: 'FinanceAgent', label: '재무 Agent', role: '비용/손익 검토', status: 'queued' },
    ],
  })

  assert.deepEqual(
    listActiveProgresses(state).map((item) => item.agent.agentKey),
    ['FinanceAgent', 'IdeaAgent'],
  )

  state = upsertActiveProgress(state, {
    requestId: 'req-1',
    status: 'PROCESSING',
    eventType: 'agent.started',
    viewType: 'status',
    sequence: 2,
    message: '재무 Agent가 비용/손익 검토 쪽 근거를 먼저 살펴보고 있어요.',
    agent: { key: 'finance', agentKey: 'FinanceAgent', label: '재무 Agent', role: '비용/손익 검토', status: 'running' },
  })

  assert.equal(resolveTypingAgent(listActiveProgresses(state)), 'finance')

  state = upsertActiveProgress(state, {
    requestId: 'req-1',
    status: 'PROCESSING',
    eventType: 'agent.completed',
    viewType: 'result',
    sequence: 3,
    message: '재무 Agent 응답 완료',
    agent: { key: 'finance', agentKey: 'FinanceAgent', label: '재무 Agent', role: '비용/손익 검토', status: 'completed' },
  })

  assert.deepEqual(
    listActiveProgresses(state).map((item) => item.agent.agentKey),
    ['IdeaAgent'],
  )
})

test('upsertActiveProgress clears request entries after final completion', () => {
  let state = new Map()

  state = upsertActiveProgress(state, {
    requestId: 'req-2',
    status: 'PROCESSING',
    eventType: 'orchestrator.synthesizing',
    viewType: 'discussion',
    sequence: 7,
    message: '이제 정리해서 답할게요.',
    agent: { key: 'plan', agentKey: 'OrchestratorAgent', label: 'Orchestrator', role: 'Agent 의견 조율', status: 'running' },
  })

  assert.equal(listActiveProgresses(state).length, 1)
  assert.equal(resolveTypingAgent(listActiveProgresses(state)), 'plan')

  state = upsertActiveProgress(state, {
    requestId: 'req-2',
    status: 'COMPLETED',
    eventType: 'orchestrator.completed',
    viewType: 'status',
    sequence: 8,
    message: '완료',
    agent: { key: 'plan', agentKey: 'OrchestratorAgent', label: 'Orchestrator', role: 'Agent 의견 조율', status: 'completed' },
  })

  assert.equal(listActiveProgresses(state).length, 0)
})
