// 에이전트 진행/토론 메시지를 한 번에 쏟지 않고 한 줄씩(대화처럼) 흘려보내기 위한 큐.
// React/타이머와 무관한 순수 로직이라 단독 테스트가 쉽다. 훅(useChatMessageQueue)이 이걸 구동한다.

export const QUEUE_BASE_INTERVAL_MS = 1000
export const QUEUE_MIN_INTERVAL_MS = 300

// 큐가 밀릴수록 간격을 좁혀 따라잡는다(B). 짧은 토론은 또박또박 1초, 길면 자동으로 빨라진다.
export const nextInterval = (queueLength) => {
  if (queueLength <= 0) {
    return QUEUE_BASE_INTERVAL_MS
  }
  const raw = Math.round((QUEUE_BASE_INTERVAL_MS * 3) / (queueLength + 2))
  return Math.min(QUEUE_BASE_INTERVAL_MS, Math.max(QUEUE_MIN_INTERVAL_MS, raw))
}

// 큐 상태(대기열 + 표시 이력)를 들고 enqueue/dequeue/flush/reset을 제공한다.
// seen 집합으로 SSE 재연결 시 같은 메시지가 중복 표시되는 것을 막는다.
export const createMessageQueueCore = () => {
  let queue = []
  const seen = new Set()

  return {
    // 새 메시지를 대기열에 넣는다. id가 없거나 이미 본 메시지면 무시하고 false 반환.
    enqueue(message) {
      const id = message?.id
      if (!id || seen.has(id)) {
        return false
      }
      seen.add(id)
      queue.push(message)
      return true
    },
    // 즉시 표시한 메시지의 id도 seen에 등록해 큐 경로와의 중복을 방지한다.
    markSeen(id) {
      if (id) {
        seen.add(id)
      }
    },
    // 대기열에서 한 개 꺼낸다. 없으면 null.
    dequeue() {
      return queue.length ? queue.shift() : null
    },
    // 남은 대기열을 모두 꺼내 비운다(새 질문 시 현재로 스냅).
    flushAll() {
      const rest = queue
      queue = []
      return rest
    },
    // 방 전환/언마운트 시 전부 초기화.
    reset() {
      queue = []
      seen.clear()
    },
    get length() {
      return queue.length
    },
    nextInterval() {
      return nextInterval(queue.length)
    },
  }
}
