import assert from 'node:assert/strict'
import test from 'node:test'

import { upsertMessage } from './chatMappers.js'

const userMessage = (requestId) => ({
  id: `user-${requestId}`,
  role: 'user',
  text: '질문',
  metadata: { requestId },
})

const progressMessage = (requestId, sequence) => ({
  id: `progress-${requestId}-${sequence}`,
  role: 'agent',
  text: `progress ${sequence}`,
  metadata: {
    progressMessage: true,
    requestId,
    sequence,
  },
})

const finalMessage = (requestId) => ({
  id: `final-${requestId}`,
  role: 'agent',
  text: '최종 답변',
  metadata: { requestId },
})

test('upsertMessage keeps progress bubbles in sequence order for the same request', () => {
  let messages = []
  messages = upsertMessage(messages, userMessage('req-1'))
  messages = upsertMessage(messages, progressMessage('req-1', 3))
  messages = upsertMessage(messages, progressMessage('req-1', 2))

  assert.deepEqual(
    messages.map((message) => message.id),
    ['user-req-1', 'progress-req-1-2', 'progress-req-1-3'],
  )
})

test('upsertMessage places late progress before the final answer for the same request', () => {
  let messages = []
  messages = upsertMessage(messages, userMessage('req-2'))
  messages = upsertMessage(messages, finalMessage('req-2'))
  messages = upsertMessage(messages, progressMessage('req-2', 4))

  assert.deepEqual(
    messages.map((message) => message.id),
    ['user-req-2', 'progress-req-2-4', 'final-req-2'],
  )
})

test('upsertMessage preserves arrival order across different requests', () => {
  let messages = []
  messages = upsertMessage(messages, userMessage('req-a'))
  messages = upsertMessage(messages, userMessage('req-b'))
  messages = upsertMessage(messages, progressMessage('req-a', 1))

  assert.deepEqual(
    messages.map((message) => message.id),
    ['user-req-a', 'user-req-b', 'progress-req-a-1'],
  )
})
