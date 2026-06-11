import { useEffect, useMemo, useRef, useState } from 'react'
import { agents } from '../../shared/data/agents'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { Icon } from '../../shared/components/Icon'
import { ChatInput } from '../chat/ChatInput'
import { ChatRow } from '../chat/ChatRow'
import {
  clearActiveProgressByRequest,
  listActiveProgresses,
  resolveTypingAgent,
  upsertActiveProgress,
} from '../chat/chatProgressState'
import { StatusProgressRow } from '../chat/StatusProgressRow'
import { TypingRow } from '../chat/TypingRow'
import {
  createChatEventSource,
  createFreeChatRoom,
  getChatMessages,
  getFreeChatRoom,
  getFreeChatRooms,
  sendChatMessage,
  updateFreeChatRoomTitle,
} from '../chat/chatApi'
import {
  normalizeAgentProgressEvent,
  normalizeAgentProgressMessage,
  normalizeChatMessage,
  normalizeStatusEvent,
  upsertMessage,
} from '../chat/chatMappers'

export const DiscussPage = ({ user }) => {
  const [items, setItems] = useState([])
  const [rooms, setRooms] = useState([])
  const [room, setRoom] = useState(null)
  const [connection, setConnection] = useState('idle')
  const [loading, setLoading] = useState(true)
  const [creatingRoom, setCreatingRoom] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [statusMap, setStatusMap] = useState({})
  const [activeProgressMap, setActiveProgressMap] = useState(new Map())
  const [sessionMenuOpen, setSessionMenuOpen] = useState(false)
  const [editingRoomId, setEditingRoomId] = useState(null)
  const [titleDraft, setTitleDraft] = useState('')
  const [savingTitle, setSavingTitle] = useState(false)
  const [streamVersion, setStreamVersion] = useState(0)
  const scroll = useRef(null)
  const sessionMenuRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  useEffect(() => {
    if (scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight
  }, [items, statusMap, activeProgressMap])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!sessionMenuRef.current?.contains(event.target)) {
        setSessionMenuOpen(false)
        setEditingRoomId(null)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

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
          setRooms(nextRooms)
          setRoom(nextRooms[0])
          return
        }

        const fallbackRoom = await getFreeChatRoom()
        if (!active) return
        setRooms([fallbackRoom])
        setRoom(fallbackRoom)
      } catch (nextError) {
        if (!active) return
        setError(nextError.message ?? '채팅 연결을 준비하지 못했습니다.')
      } finally {
        if (active) setLoading(false)
      }
    }

    bootstrap()

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    setStreamVersion(0)
  }, [room?.roomId])

  useEffect(() => {
    if (!room?.roomId) return undefined

    let active = true
    const eventSource = createChatEventSource(room.roomId)

    const loadHistory = async ({ reset = false, showLoading = false } = {}) => {
      try {
        if (showLoading) setLoading(true)
        setError('')

        if (reset) {
          setItems([])
          setStatusMap({})
          setActiveProgressMap(new Map())
          setConnection('connecting')
        }

        const history = await getChatMessages(room.roomId)
        if (!active) return
        setItems(history.messages.map(normalizeChatMessage))
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
      if (streamVersion > 0) {
        loadHistory()
      }
    })

    eventSource.addEventListener('chat-message', (event) => {
      if (!active) return
      const payload = JSON.parse(event.data)
      if (!payload.message) return
      setItems((prev) => upsertMessage(prev, normalizeChatMessage(payload.message)))
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
        setItems((prev) => upsertMessage(prev, normalizeAgentProgressMessage(nextProgress)))
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

  const updateRoomState = (updatedRoom) => {
    setRooms((prev) => prev.map((candidate) => (
      candidate.roomId === updatedRoom.roomId ? updatedRoom : candidate
    )))
    setRoom((prev) => (prev?.roomId === updatedRoom.roomId ? updatedRoom : prev))
  }

  const send = async (text) => {
    if (sending || !room?.roomId) return
    setSending(true)
    setError('')

    try {
      const response = await sendChatMessage(room.roomId, {
        userId: user?.id ?? null,
        content: text,
        metadata: JSON.stringify({ source: 'discuss-page' }),
        intent: 'auto',
        sessionType: 'FREE_CHAT',
        candidateAgents: [],
        currentResult: {},
      })

      setItems((prev) => upsertMessage(prev, {
        id: response.messageId,
        role: 'user',
        senderType: response.senderType,
        userId: user?.id ?? null,
        agentId: null,
        agent: null,
        text: response.content,
        metadata: { source: 'discuss-page' },
        createdAt: null,
      }))

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
      setRooms((prev) => [createdRoom, ...prev])
      setRoom(createdRoom)
      setSessionMenuOpen(false)
      setEditingRoomId(null)
    } catch (nextError) {
      setError(nextError.message ?? '새 자유 상담 세션을 만들지 못했습니다.')
    } finally {
      setCreatingRoom(false)
    }
  }

  const startEditingTitle = (candidateRoom) => {
    setEditingRoomId(candidateRoom.roomId)
    setTitleDraft(candidateRoom.title ?? '')
    setSessionMenuOpen(true)
  }

  const cancelEditingTitle = () => {
    setEditingRoomId(null)
    setTitleDraft('')
  }

  const submitTitleUpdate = async (roomId) => {
    if (savingTitle) return

    try {
      setSavingTitle(true)
      setError('')
      const updatedRoom = await updateFreeChatRoomTitle(roomId, titleDraft)
      updateRoomState(updatedRoom)
      setEditingRoomId(null)
      setTitleDraft('')
    } catch (nextError) {
      setError(nextError.message ?? '세션 이름을 수정하지 못했습니다.')
    } finally {
      setSavingTitle(false)
    }
  }

  return (
    <main className="discuss-page">
      <div className="page-title compact">
        <div>
          <h1>AI와 자유 상담하기</h1>
          <p>창업 아이템, 자금, 지원사업, 홍보까지 자유롭게 질문하고 이어서 대화해보세요.</p>
        </div>
        <div className={`chat-connection ${connection}`}>
          {connection === 'connected'
            ? '실시간 연결됨'
            : connection === 'connecting'
              ? '연결 중'
              : connection === 'error'
                ? '연결 문제'
                : '준비 중'}
        </div>
      </div>

      <div className="chat-session-bar">
        <div className="chat-session-picker" ref={sessionMenuRef}>
          <button
            className={sessionMenuOpen ? 'chat-session-trigger on' : 'chat-session-trigger'}
            onClick={() => setSessionMenuOpen((prev) => !prev)}
            disabled={!rooms.length}
          >
            <div className="chat-session-trigger-copy">
              <small>상담 세션</small>
              <b>{room?.title ?? '세션 선택'}</b>
            </div>
            <Icon name="chevron" size={16} />
          </button>

          {sessionMenuOpen && (
            <div className="chat-session-menu">
              {rooms.map((candidateRoom) => {
                const isEditing = editingRoomId === candidateRoom.roomId
                const isSelected = candidateRoom.roomId === room?.roomId

                return (
                  <div
                    key={candidateRoom.roomId}
                    className={isSelected ? 'chat-session-option on' : 'chat-session-option'}
                  >
                    {isEditing ? (
                      <form
                        className="chat-session-edit"
                        onSubmit={(event) => {
                          event.preventDefault()
                          submitTitleUpdate(candidateRoom.roomId)
                        }}
                      >
                        <input
                          value={titleDraft}
                          onChange={(event) => setTitleDraft(event.target.value)}
                          placeholder="세션 이름"
                          autoFocus
                          maxLength={60}
                        />
                        <button type="submit" disabled={savingTitle}>
                          <Icon name="check" size={14} />
                        </button>
                        <button type="button" className="ghost" onClick={cancelEditingTitle} disabled={savingTitle}>
                          취소
                        </button>
                      </form>
                    ) : (
                      <>
                        <button
                          className="chat-session-select"
                          onClick={() => {
                            setRoom(candidateRoom)
                            setSessionMenuOpen(false)
                            setEditingRoomId(null)
                          }}
                        >
                          <div>
                            <b>{candidateRoom.title}</b>
                            <small>{isSelected ? '현재 보고 있는 세션' : '이 세션으로 전환'}</small>
                          </div>
                        </button>
                        <button
                          className="chat-session-rename"
                          onClick={() => startEditingTitle(candidateRoom)}
                          aria-label={`${candidateRoom.title} 이름 수정`}
                        >
                          <Icon name="edit" size={14} />
                        </button>
                      </>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <button className="chat-session-new" onClick={createSession} disabled={creatingRoom || sending}>
          <Icon name="plus" size={16} />
          <span>{creatingRoom ? '만드는 중' : '새 상담 시작'}</span>
        </button>
      </div>

      <div className="chat-panel" ref={scroll}>
        {loading && <div className="chat-loading">대화를 불러오는 중...</div>}
        {!loading && !items.length && (
          <div className="empty-chat">
            <div className="agent-stack">{Object.keys(agents).map((id) => <AgentAvatar key={id} id={id} />)}</div>
            <h2>무엇이든 물어보세요</h2>
            <p>첫 질문을 보내면 자유 상담실 대화가 시작돼요.</p>
          </div>
        )}
        {items.map((item) => <ChatRow key={item.id} message={item} />)}
        {statusProgresses.map((progress) => <StatusProgressRow key={progress.id} progress={progress} />)}
        {typing && <TypingRow agent={typing} />}
      </div>

      {!!latestStatus && latestStatus.status === 'FAILED' && (
        <div className={`chat-status-banner ${latestStatus.status?.toLowerCase()}`}>
          <b>{latestStatus.status}</b>
          {latestStatus.errorMessage ? <span>{latestStatus.errorMessage}</span> : <span>요청 ID {latestStatus.requestId}</span>}
        </div>
      )}
      {!!error && <div className="chat-error-banner">{error}</div>}

      <ChatInput
        onSend={send}
        disabled={sending || loading || connection === 'error' || !room?.roomId}
        placeholder="창업에 대한 고민을 자유롭게 물어보세요."
        suggestions={[
          '지금 100만원으로 가능한 창업 아이템 추천해줘',
          '지원사업 신청 가능성 높은 방향을 알려줘',
          'SNS 홍보 문구를 만들어줘',
        ]}
      />
    </main>
  )
}
