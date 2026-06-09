import { useEffect, useMemo, useRef, useState } from 'react'
import { agents } from '../../shared/data/agents'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { ChatInput } from '../chat/ChatInput'
import { ChatRow } from '../chat/ChatRow'
import { TypingRow } from '../chat/TypingRow'
import { CHAT_USER_ID, createChatEventSource, getChatMessages, getFreeChatRoom, sendChatMessage } from '../chat/chatApi'
import { normalizeChatMessage, normalizeStatusEvent, upsertMessage } from '../chat/chatMappers'

export const DiscussPage = () => {
  const [items, setItems] = useState([])
  const [room, setRoom] = useState(null)
  const [connection, setConnection] = useState('idle')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [statusMap, setStatusMap] = useState({})
  const scroll = useRef(null)

  useEffect(() => {
    if (scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight
  }, [items, statusMap])

  useEffect(() => {
    let active = true
    let eventSource

    const bootstrap = async () => {
      try {
        setLoading(true)
        setError('')

        const nextRoom = await getFreeChatRoom(CHAT_USER_ID)
        if (!active) return
        setRoom(nextRoom)

        const history = await getChatMessages(nextRoom.roomId, CHAT_USER_ID)
        if (!active) return
        setItems(history.messages.map(normalizeChatMessage))

        eventSource = createChatEventSource(nextRoom.roomId, CHAT_USER_ID)
        setConnection('connecting')

        eventSource.addEventListener('chat-connected', () => {
          if (!active) return
          setConnection('connected')
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
        })

        eventSource.onerror = () => {
          if (!active) return
          setConnection('error')
        }
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
      eventSource?.close()
    }
  }, [])

  const latestStatus = useMemo(() => Object.values(statusMap).at(-1) ?? null, [statusMap])
  const typing = latestStatus && ['QUEUED', 'PROCESSING'].includes(latestStatus.status) ? 'profile' : null

  const send = async (text) => {
    if (sending || !room?.roomId) return
    setSending(true)
    setError('')

    try {
      const response = await sendChatMessage(room.roomId, {
        userId: CHAT_USER_ID,
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
        userId: CHAT_USER_ID,
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

  return (
    <main className="discuss-page">
      <div className="page-title compact">
        <div>
          <h1>AI와 자유 상담하기</h1>
          <p>창업 아이템, 자금, 지원사업, 홍보까지 자유롭게 질문할 수 있어요.</p>
        </div>
        <div className={`chat-connection ${connection}`}>
          {connection === 'connected' ? '실시간 연결됨' : connection === 'connecting' ? '연결 중' : connection === 'error' ? '연결 문제' : '준비 중'}
        </div>
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
        {typing && <TypingRow agent={typing} />}
      </div>

      {!!latestStatus && (
        <div className={`chat-status-banner ${latestStatus.status?.toLowerCase()}`}>
          <b>{latestStatus.status}</b>
          {latestStatus.errorMessage ? <span>{latestStatus.errorMessage}</span> : <span>요청 ID {latestStatus.requestId}</span>}
        </div>
      )}
      {!!error && <div className="chat-error-banner">{error}</div>}

      <ChatInput
        onSend={send}
        disabled={sending || loading || connection === 'error'}
        placeholder="창업에 대한 고민을 자유롭게 물어보세요."
        suggestions={[
          '자금 100만원으로 가능한 창업 아이템 추천해줘',
          '지원사업 신청 가능성 높은 방향을 알려줘',
          'SNS 홍보 문구를 만들어줘',
        ]}
      />
    </main>
  )
}
