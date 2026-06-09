import { useEffect, useRef, useState } from 'react'
import { agents } from '../../shared/data/agents'
import { features } from '../../shared/data/features'
import { cloneReport } from '../../shared/data/reports'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { AgentBadge } from '../../shared/components/AgentBadge'
import { ChatInput } from '../chat/ChatInput'
import { ChatRow } from '../chat/ChatRow'
import { TypingRow } from '../chat/TypingRow'
import { Report } from '../reports/Report'

export const FeaturePage = ({ id, go }) => {
  const f = features[id]
  const agent = agents[f.agent]
  const [data, setData] = useState(() => cloneReport(id))
  const [messages, setMessages] = useState([{ agent: f.agent, text: `${f.title} 결과를 만들었어요. 오른쪽에서 원하는 방향을 말하면 이 리포트를 수정할 수 있어요.` }])
  const [busy, setBusy] = useState(false)
  const [typing, setTyping] = useState(null)
  const chatRef = useRef(null)
  useEffect(() => { if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight }, [messages, typing])

  const send = (text) => {
    setMessages((prev) => [...prev, { role: 'user', text }])
    setBusy(true)
    setTyping(f.agent)
    window.setTimeout(() => {
      setTyping(null)
      setMessages((prev) => [...prev, { agent: f.agent, text: `${agent.name}가 요청을 반영했어요. 실제 서비스에서는 이 지점에서 백엔드 AI API가 결과 JSON을 갱신합니다.` }])
      setBusy(false)
    }, 900)
  }

  return (
    <main className="feature-page">
      <section className="report-area">
        <div className="page-title"><div><h1>{f.title}</h1><p>{f.sub}</p></div><AgentBadge id={f.agent} /></div>
        <Report id={id} data={data} setData={setData} go={go} />
      </section>
      <aside className="feature-chat">
        <header style={{ color: agent.color }}><AgentAvatar id={f.agent} /><div><b>{agent.name}</b><small>이 리포트를 함께 수정해요</small></div></header>
        <div className="feature-chat-body" ref={chatRef}>
          {messages.map((m, i) => <ChatRow key={i} message={m} />)}
          {typing && <TypingRow agent={typing} />}
        </div>
        <ChatInput onSend={send} disabled={busy} placeholder="리포트를 어떻게 바꿀까요?" accent={agent.color} suggestions={['더 현실적인 방향으로 바꿔줘', '지원사업 신청 가능성이 높은 쪽으로', '20대 타깃 느낌으로 바꿔줘']} />
      </aside>
    </main>
  )
}
