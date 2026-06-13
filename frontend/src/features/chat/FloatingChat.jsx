import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Icon } from '../../shared/components/Icon'
import { ChatRow } from './ChatRow'
import { RotatingStatusProgress } from './RotatingStatusProgress'
import { TypingRow } from './TypingRow'
import './FloatingChat.css'

/**
 * 우하단 플로팅 채팅. 채팅 상태/로직은 페이지가 보유하고, 이 컴포넌트는 표현만 담당한다.
 * createPortal로 body에 렌더해 조상 overflow:hidden / 스태킹 컨텍스트 클리핑을 피한다.
 */
export const FloatingChat = ({
  accent = 'var(--brand)',
  active = false,
  launcherLabel = 'AI 전문가에게 질문하기',
  headerSlot,
  emptySlot,
  onNewChat,
  newChatLabel = '새 채팅',
  newChatDisabled = false,
  toolbarExtra = null,
  loading = false,
  messages = [],
  statusProgresses = [],
  typing = null,
  onOpenReport,
  failedStatus = null,
  error = '',
  input,
}) => {
  const [open, setOpen] = useState(false)
  const bodyRef = useRef(null)

  useEffect(() => {
    if (open && bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight
    }
  }, [open, messages, statusProgresses, typing])

  const showToolbar = Boolean(toolbarExtra)

  return createPortal(
    <div className="chat-dock-root" style={{ '--chat-accent': accent }}>
      {open ? (
        <section className="chat-dock" role="dialog" aria-label="AI 전문가 채팅">
          <header className="chat-dock-header">
            {headerSlot}
            <div className="chat-dock-header-actions">
              {onNewChat && (
                <button
                  type="button"
                  className="chat-dock-icon-btn chat-dock-new"
                  onClick={onNewChat}
                  disabled={newChatDisabled}
                  aria-label={newChatLabel}
                  title={newChatLabel}
                >
                  <Icon name="edit" size={19} />
                </button>
              )}
              <button
                type="button"
                className="chat-dock-icon-btn"
                onClick={() => setOpen(false)}
                aria-label="채팅 닫기"
                title="채팅 닫기"
              >
                <Icon name="close" size={21} />
              </button>
            </div>
          </header>

          {showToolbar && (
            <div className="chat-dock-toolbar">
              {toolbarExtra}
            </div>
          )}

          <div className="chat-dock-body" ref={bodyRef}>
            {loading && <div className="chat-loading">대화를 불러오는 중...</div>}
            {!loading && !messages.length && emptySlot}
            {messages.map((message) => (
              <ChatRow key={message.id} message={message} onOpenReport={onOpenReport} />
            ))}
            <RotatingStatusProgress progresses={statusProgresses} />
            {typing && <TypingRow agent={typing} />}
          </div>

          {!!failedStatus && failedStatus.status === 'FAILED' && (
            <div className={`chat-status-banner ${failedStatus.status?.toLowerCase()}`}>
              <b>{failedStatus.status}</b>
              {failedStatus.errorMessage
                ? <span>{failedStatus.errorMessage}</span>
                : <span>요청 ID {failedStatus.requestId}</span>}
            </div>
          )}
          {!!error && <div className="chat-error-banner">{error}</div>}

          {input}
        </section>
      ) : (
        <button
          type="button"
          className={active ? 'chat-fab active' : 'chat-fab'}
          onClick={() => setOpen(true)}
          aria-label={launcherLabel}
          title={launcherLabel}
        >
          <Icon name="discuss" size={24} />
          {active && <span className="chat-fab-dot" aria-hidden="true" />}
        </button>
      )}
    </div>,
    document.body,
  )
}
