import { useEffect, useMemo, useRef, useState } from 'react'
import { agents } from '../../shared/data/agents'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { Icon } from '../../shared/components/Icon'
import { ChatInput } from '../chat/ChatInput'
import { FloatingChat } from '../chat/FloatingChat'
import {
  clearActiveProgressByRequest,
  listActiveProgresses,
  resolveTypingAgent,
  upsertActiveProgress,
} from '../chat/chatProgressState'
import {
  createChatEventSource,
  createFreeChatRoom,
  getChatMessages,
  getFreeChatRoom,
  getFreeChatRooms,
  sendChatMessage,
} from '../chat/chatApi'
import {
  normalizeAgentProgressEvent,
  normalizeAgentProgressMessage,
  normalizeChatMessage,
  normalizeStatusEvent,
} from '../chat/chatMappers'
import { useChatMessageQueue } from '../chat/useChatMessageQueue'

// 홈(워크스페이스) 우하단 플로팅 파트너 채팅.
// 다른 기능 페이지처럼 FloatingChat 도크를 띄우되, 자유 상담(FREE_CHAT) 룸을 사용한다.
// (상태/SSE/전송 로직은 DiscussPage와 동일한 검증된 흐름을 따른다)
export const WorkspaceChat = ({ user, go }) => {
  const {
    messages: items,
    pushImmediate,
    enqueue,
    flush,
    reset: resetItems,
    isDraining,
  } = useChatMessageQueue([])
  const [room, setRoom] = useState(null)
  const [connection, setConnection] = useState('idle')
  const [loading, setLoading] = useState(true)
  const [creatingRoom, setCreatingRoom] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [statusMap, setStatusMap] = useState({})
  const [activeProgressMap, setActiveProgressMap] = useState(new Map())
  const [streamVersion, setStreamVersion] = useState(0)
  const reconnectTimeoutRef = useRef(null)

  useEffect(() => {
    let active = true
    const bootstrap = async () => {
      try {
        setLoading(true)
        setError('')
        const roomListResponse = await getFreeChatRooms()
        if (!active) return
        const nextRooms = roomListResponse.rooms ?? []
        if (nextRooms.length) {
          setRoom(nextRooms[0])
          return
        }
        const fallbackRoom = await getFreeChatRoom()
        if (!active) return
        setRoom(fallbackRoom)
      } catch (nextError) {
        if (!active) return
        setError(nextError.message ?? '채팅 연결을 준비하지 못했습니다.')
      } finally {
        if (active) setLoading(false)
      }
    }
    bootstrap()
    return () => { active = false }
  }, [])

  useEffect(() => { setStreamVersion(0) }, [room?.roomId])

  useEffect(() => {
    if (!room?.roomId) return undefined
    let active = true
    const eventSource = createChatEventSource(room.roomId)

    const loadHistory = async ({ reset = false, showLoading = false } = {}) => {
      try {
        if (showLoading) setLoading(true)
        setError('')
        if (reset) {
          resetItems([])
          setStatusMap({})
          setActiveProgressMap(new Map())
          setConnection('connecting')
        }
        const history = await getChatMessages(room.roomId)
        if (!active) return
        resetItems(history.messages.map(normalizeChatMessage))
      } catch (nextError) {
        if (!active) return
        setError(nextError.message ?? '이전 대화를 불러오지 못했습니다.')
      } finally {
        if (active && showLoading) setLoading(false)
      }
    }

    loadHistory({ reset: true, showLoading: true })

    eventSource.addEventListener('chat-connected', () => {
      if (!active) return
      setConnection('connected')
      if (streamVersion > 0) loadHistory()
    })

    eventSource.addEventListener('chat-message', (event) => {
      if (!active) return
      const payload = JSON.parse(event.data)
      if (!payload.message) return
      const message = normalizeChatMessage(payload.message)
      if (message.role === 'user') pushImmediate(message)
      else enqueue(message)
    })

    eventSource.addEventListener('chat-status', (event) => {
      if (!active) return
      const payload = JSON.parse(event.data)
      if (!payload.status) return
      const nextStatus = normalizeStatusEvent(payload.status)
      setStatusMap((prev) => ({ ...prev, [nextStatus.requestId]: nextStatus }))
      if (['COMPLETED', 'FAILED'].includes(nextStatus.status)) {
        setActiveProgressMap((prev) => clearActiveProgressByRequest(prev, nextStatus.requestId))
      }
    })

    eventSource.addEventListener('agent-progress', (event) => {
      if (!active) return
      const payload = JSON.parse(event.data)
      if (!payload.agentProgress) return
      const nextProgress = normalizeAgentProgressEvent(payload.agentProgress)
      setActiveProgressMap((prev) => upsertActiveProgress(prev, nextProgress))
      if (nextProgress.viewType !== 'status' && nextProgress.agent && nextProgress.message) {
        enqueue(normalizeAgentProgressMessage(nextProgress))
      }
    })

    eventSource.onerror = () => {
      if (!active) return
      setConnection('connecting')
      if (reconnectTimeoutRef.current) return
      reconnectTimeoutRef.current = window.setTimeout(() => {
        reconnectTimeoutRef.current = null
        if (!active) return
        eventSource.close()
        setStreamVersion((prev) => prev + 1)
      }, 1200)
    }

    return () => {
      active = false
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      eventSource.close()
    }
  }, [room?.roomId, streamVersion])

  const latestStatus = useMemo(() => Object.values(statusMap).at(-1) ?? null, [statusMap])
  const activeProgresses = useMemo(() => listActiveProgresses(activeProgressMap), [activeProgressMap])
  const statusProgresses = useMemo(
    () => activeProgresses.filter((progress) => progress.viewType === 'status'),
    [activeProgresses],
  )
  const typing = activeProgresses.length
    ? resolveTypingAgent(
        activeProgresses.filter((progress) => (
          ['running', 'queued'].includes(String(progress.agent?.status ?? '').toLowerCase())
          || progress.eventType === 'orchestrator.synthesizing'
        )),
        null,
      )
    : latestStatus && ['QUEUED', 'PROCESSING'].includes(latestStatus.status)
      ? 'profile'
      : null

  const send = async (text) => {
    if (sending || !room?.roomId) return
    setSending(true)
    setError('')
    flush()
    try {
      const messageMetadata = { source: 'home-chat' }
      const response = await sendChatMessage(room.roomId, {
        userId: user?.id ?? null,
        content: text,
        metadata: JSON.stringify(messageMetadata),
        intent: 'auto',
        sessionType: 'FREE_CHAT',
        candidateAgents: [],
        currentResult: {},
      })
      messageMetadata.requestId = response.requestId
      pushImmediate({
        id: response.messageId,
        role: 'user',
        senderType: response.senderType,
        userId: user?.id ?? null,
        agentId: null,
        agent: null,
        text: response.content,
        metadata: messageMetadata,
        createdAt: null,
      })
      setStatusMap((prev) => ({
        ...prev,
        [response.requestId]: {
          requestId: response.requestId,
          messageId: response.messageId,
          status: 'QUEUED',
          errorMessage: '',
          updatedAt: null,
        },
      }))
    } catch (nextError) {
      setError(nextError.message ?? '메시지를 보내지 못했습니다.')
    } finally {
      setSending(false)
    }
  }

  const createSession = async () => {
    if (creatingRoom) return
    setCreatingRoom(true)
    setError('')
    try {
      const createdRoom = await createFreeChatRoom()
      setRoom(createdRoom)
    } catch (nextError) {
      setError(nextError.message ?? '새 채팅을 만들지 못했습니다.')
    } finally {
      setCreatingRoom(false)
    }
  }

  return (
    <FloatingChat
      accent="var(--brand)"
      active={Boolean(typing || isDraining)}
      launcherLabel="파트너들에게 물어보기"
      headerSlot={(
        <div className="chat-dock-agent">
          <span className="feature-chat-agent-placeholder">
            <Icon name="discuss" size={18} />
          </span>
          <div className="chat-dock-agent-copy">
            <b>파트너 채팅</b>
            <small>
              {connection === 'connected'
                ? '실시간 연결됨'
                : connection === 'connecting'
                  ? '연결 중'
                  : '준비 중'}
            </small>
          </div>
        </div>
      )}
      onNewChat={createSession}
      newChatLabel={creatingRoom ? '만드는 중' : '새 채팅'}
      newChatDisabled={creatingRoom || sending}
      loading={loading}
      emptySlot={(
        <div className="feature-chat-empty">
          <div className="agent-stack">{Object.keys(agents).map((id) => <AgentAvatar key={id} id={id} />)}</div>
          <strong>이 워크스페이스에 대해 무엇이든 물어보세요.</strong>
          <p>선택한 아이템과 프로필을 기준으로 파트너들이 함께 답합니다.</p>
        </div>
      )}
      messages={items.filter((message) => !message.metadata?.hidden)}
      statusProgresses={statusProgresses}
      typing={typing}
      onOpenReport={go}
      failedStatus={latestStatus}
      error={error}
      input={(
        <ChatInput
          onSend={send}
          disabled={sending || loading || connection === 'error' || !room?.roomId}
          placeholder="이 워크스페이스에 대해 물어보세요."
          suggestions={[
            '이 아이템 30일 검증 계획을 더 구체화해줘',
            '이 아이템에 맞는 지원사업이 있을까?',
            '초기 비용을 줄일 방법을 알려줘',
          ]}
        />
      )}
    />
  )
}
