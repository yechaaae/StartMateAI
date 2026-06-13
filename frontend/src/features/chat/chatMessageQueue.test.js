import assert from 'node:assert/strict'
import test from 'node:test'

import {
  QUEUE_BASE_INTERVAL_MS,
  QUEUE_MIN_INTERVAL_MS,
  createMessageQueueCore,
  nextInterval,
} from './chatMessageQueue.js'

test('nextInterval은 큐가 짧으면 기본 간격, 길수록 좁히되 하한을 지킨다', () => {
  assert.equal(nextInterval(0), QUEUE_BASE_INTERVAL_MS)
  assert.equal(nextInterval(1), 1000)
  assert.equal(nextInterval(3), 600)
  assert.equal(nextInterval(6), 375)
  assert.equal(nextInterval(10), QUEUE_MIN_INTERVAL_MS) // 250 -> 300 하한
  assert.equal(nextInterval(100), QUEUE_MIN_INTERVAL_MS)
  assert.ok(nextInterval(2) <= QUEUE_BASE_INTERVAL_MS)
})

test('enqueue는 FIFO로 쌓고 dequeue가 순서대로 꺼낸다', () => {
  const core = createMessageQueueCore()
  assert.equal(core.enqueue({ id: 'a' }), true)
  assert.equal(core.enqueue({ id: 'b' }), true)
  assert.equal(core.enqueue({ id: 'c' }), true)
  assert.equal(core.length, 3)

  assert.equal(core.dequeue().id, 'a')
  assert.equal(core.dequeue().id, 'b')
  assert.equal(core.dequeue().id, 'c')
  assert.equal(core.dequeue(), null)
  assert.equal(core.length, 0)
})

test('이미 본 id는 중복으로 들어가지 않는다(SSE 재연결 방어)', () => {
  const core = createMessageQueueCore()
  assert.equal(core.enqueue({ id: 'x' }), true)
  assert.equal(core.enqueue({ id: 'x' }), false) // 같은 id 재유입
  assert.equal(core.length, 1)
})

test('id가 없는 메시지는 무시한다', () => {
  const core = createMessageQueueCore()
  assert.equal(core.enqueue({}), false)
  assert.equal(core.enqueue(null), false)
  assert.equal(core.length, 0)
})

test('markSeen으로 즉시표시한 메시지는 큐 경로에서 중복되지 않는다', () => {
  const core = createMessageQueueCore()
  core.markSeen('u1')
  assert.equal(core.enqueue({ id: 'u1' }), false)
})

test('flushAll은 남은 큐를 순서대로 모두 반환하고 비운다', () => {
  const core = createMessageQueueCore()
  core.enqueue({ id: 'a' })
  core.enqueue({ id: 'b' })
  const rest = core.flushAll()
  assert.deepEqual(rest.map((m) => m.id), ['a', 'b'])
  assert.equal(core.length, 0)
})

test('reset은 큐와 seen 이력을 모두 비워 같은 id를 다시 받을 수 있다', () => {
  const core = createMessageQueueCore()
  core.enqueue({ id: 'a' })
  core.reset()
  assert.equal(core.length, 0)
  assert.equal(core.enqueue({ id: 'a' }), true) // reset 후엔 다시 허용
})
