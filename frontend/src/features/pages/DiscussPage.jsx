import { useEffect, useRef, useState } from 'react'
import { agents } from '../../shared/data/agents'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { Icon } from '../../shared/components/Icon'
import { ChatInput } from '../chat/ChatInput'
import { ChatRow } from '../chat/ChatRow'
import { TypingRow } from '../chat/TypingRow'
import { agentReply, routeAgents } from '../chat/chatLogic'

export const DiscussPage = () => {
  const [items, setItems] = useState([])
  const [busy, setBusy] = useState(false)
  const [typing, setTyping] = useState(null)
  const scroll = useRef(null)
  useEffect(() => { if (scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight }, [items, typing])

  const send = (text) => {
    if (busy) return
    const selected = routeAgents(text)
    setBusy(true)
    setItems((prev) => [...prev, { role: 'user', text }, { role: 'router', selected }])
    let delay = 500
    selected.forEach((agent) => {
      window.setTimeout(() => setTyping(agent), delay)
      delay += 700
      window.setTimeout(() => {
        setTyping(null)
        setItems((prev) => [...prev, { agent, text: agentReply(agent, text) }])
      }, delay)
      delay += 250
    })
    window.setTimeout(() => {
      setItems((prev) => [...prev, { role: 'conclusion', text: '정리하면, 토론에서는 방향을 먼저 잡고 정식 결과물이 필요할 때 기능 페이지로 넘어가는 흐름이 가장 자연스럽습니다.' }])
      setBusy(false)
    }, delay + 500)
  }

  return (
    <main className="discuss-page">
      <div className="page-title compact"><div><h1>AI와 토론하기</h1><p>질문에 맞는 Agent가 자동으로 모여 의견을 나눕니다.</p></div></div>
      <div className="chat-panel" ref={scroll}>
        {!items.length && <div className="empty-chat"><div className="agent-stack">{Object.keys(agents).map((id) => <AgentAvatar key={id} id={id} />)}</div><h2>무엇이든 물어보세요</h2><p>창업 아이템, 자금, 지원사업, 홍보까지 자유롭게 질문할 수 있어요.</p></div>}
        {items.map((item, index) => {
          if (item.role === 'router') return <div className="router-row" key={index}><Icon name="sparkle" /><div><b>Agent Router</b><p>{item.selected.map((id) => agents[id].name).join(', ')}가 이 질문에 적합해요.</p></div></div>
          if (item.role === 'conclusion') return <div className="conclusion" key={index}><b>종합 결론</b><p>{item.text}</p></div>
          return <ChatRow key={index} message={item} />
        })}
        {typing && <TypingRow agent={typing} />}
      </div>
      <ChatInput onSend={send} disabled={busy} placeholder="창업에 대한 고민을 물어보세요" suggestions={['자금 100만 원으로 가능한 창업 아이템 추천해줘', '지원사업 신청 가능성이 높은 방향을 알려줘', 'SNS 홍보 문구를 만들어줘']} />
    </main>
  )
}
