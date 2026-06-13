import { useCallback, useEffect, useRef, useState } from 'react'
import { upsertMessage } from './chatMappers'
import { createMessageQueueCore } from './chatMessageQueue'

// 채팅 메시지 표시를 제어하는 훅.
// - pushImmediate: 내 메시지/상태성 메시지를 즉시 표시
// - enqueue: 에이전트 진행/토론/최종답변을 큐에 넣어 한 줄씩(≈1초, 밀리면 따라잡기) 표시
// - flush: 남은 큐를 즉시 비워 현재로 스냅(새 질문 시)
// - reset: 큐/이력 초기화 후 messages를 교체(방 전환·히스토리 로드)
// - isDraining: 큐가 아직 흘러나오는 중인지(타이핑 점 유지에 사용)
export const useChatMessageQueue = (initialMessages = []) => {
  const [messages, setMessages] = useState(initialMessages)
  const [isDraining, setIsDraining] = useState(false)
  const coreRef = useRef(null)
  if (coreRef.current === null) {
    coreRef.current = createMessageQueueCore()
  }
  const timerRef = useRef(null)

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  // 한 틱마다 한 개 꺼내 표시하고, 남아 있으면 다음 간격으로 재예약한다.
  const tick = useCallback(() => {
    const core = coreRef.current
    const item = core.dequeue()
    if (item) {
      setMessages((prev) => upsertMessage(prev, item))
    }
    if (core.length > 0) {
      timerRef.current = setTimeout(tick, core.nextInterval())
    } else {
      timerRef.current = null
      setIsDraining(false)
    }
  }, [])

  const ensureTimer = useCallback(() => {
    if (timerRef.current === null && coreRef.current.length > 0) {
      setIsDraining(true)
      timerRef.current = setTimeout(tick, coreRef.current.nextInterval())
    }
  }, [tick])

  const enqueue = useCallback((message) => {
    if (coreRef.current.enqueue(message)) {
      ensureTimer()
    }
  }, [ensureTimer])

  const pushImmediate = useCallback((message) => {
    if (!message) {
      return
    }
    coreRef.current.markSeen(message.id)
    setMessages((prev) => upsertMessage(prev, message))
  }, [])

  const flush = useCallback(() => {
    const rest = coreRef.current.flushAll()
    stopTimer()
    setIsDraining(false)
    if (rest.length) {
      setMessages((prev) => rest.reduce((acc, message) => upsertMessage(acc, message), prev))
    }
  }, [stopTimer])

  const reset = useCallback((nextMessages = []) => {
    coreRef.current.reset()
    stopTimer()
    setIsDraining(false)
    setMessages(nextMessages)
  }, [stopTimer])

  useEffect(() => () => stopTimer(), [stopTimer])

  return { messages, setMessages, pushImmediate, enqueue, flush, reset, isDraining }
}
