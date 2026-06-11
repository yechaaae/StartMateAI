import { useEffect, useRef, useState } from 'react'
import { savedResultApi } from '../../shared/api/client'
import { RoadviewPicker } from '../simulator/RoadviewPicker'
import { AssumptionForm } from '../simulator/AssumptionForm'
import { DailyReportChart } from '../simulator/DailyReportChart'
import { Icon } from '../../shared/components/Icon'
import { agents } from '../../shared/data/agents'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { ChatInput } from '../chat/ChatInput'
import { ChatRow } from '../chat/ChatRow'
import { TypingRow } from '../chat/TypingRow'
import { buildSimulationSavedReport } from '../reports/savedReportPayload'

const steps = ['위치 탐색', '가정값 설정', '리포트 확인']

const Stepper = ({ step, onJump }) => (
  <div className="sim-stepper">
    {steps.map((label, index) => {
      const current = step === index + 1
      const done = step > index + 1
      return (
        <div className="sim-step-wrap" key={label}>
          <button
            className={current ? 'current' : done ? 'done' : ''}
            disabled={index + 1 > step}
            onClick={() => index + 1 <= step && onJump(index + 1)}
          >
            <span>{done ? <Icon name="check" size={13} /> : index + 1}</span>
            {label}
          </button>
          {index < steps.length - 1 && <Icon name="arrow" size={15} className="sim-step-arrow" />}
        </div>
      )
    })}
  </div>
)

const IdeaRequired = ({ go }) => (
  <section className="sim-empty-state">
    <div className="sim-empty-icon"><Icon name="bulb" size={28} /></div>
    <h2>먼저 창업 아이템을 선택해주세요</h2>
    <p>시뮬레이션은 AI 창업 아이템 추천에서 선택한 아이템을 기준으로 위치, 월세, 건당 금액, 판매/이용 건수를 계산합니다.</p>
    <button className="sim-primary-btn" onClick={() => go('item')}>
      AI 창업 아이템 추천으로 이동 <Icon name="arrow" size={17} />
    </button>
  </section>
)

export const SimulatorPage = ({ go, workspace }) => {
  const [step, setStep] = useState(1)
  const [location, setLocation] = useState(null)
  const [assumption, setAssumption] = useState(null)
  const [report, setReport] = useState(null)
  const [messages, setMessages] = useState([
    { agent: 'finance', text: '30일 시뮬레이션 리포트를 만들었어요. 가격, 광고비, 판매/이용 건수를 바꾸고 싶으면 말씀해주세요.' },
  ])
  const [busy, setBusy] = useState(false)
  const [savingReport, setSavingReport] = useState(false)
  const [typing, setTyping] = useState(null)
  const chatRef = useRef(null)
  const agent = agents.finance
  const agentDisplayName = `${agent.label} 에이전트`
  const idea = workspace?.selectedIdea
  const showChat = step === 3 && report

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight
  }, [messages, typing])

  const handleLocationSelect = (loc) => {
    setLocation(loc)
    setStep(2)
  }

  const handleRunSimulation = (form) => {
    setAssumption(form)

    const metrics = []
    let cumulativeProfit = 0
    let totalRevenue = 0
    let totalCost = 0
    let bepDay = null

    for (let day = 1; day <= 30; day += 1) {
      const progress = day / 30
      const weekdayBoost = [0, 6, 4, 2, 5, 9, 11][day % 7]
      const baseOrders = Math.floor(form.expectedDailyOrders * (0.58 + 0.42 * progress))
      const orders = Math.max(0, baseOrders + weekdayBoost - 4)
      const revenue = orders * form.pricePerOrder
      const variableCost = Math.round(revenue * form.variableCostRate)
      const fixedCost = Math.round((form.monthlyRent + form.laborCost + form.marketingCost + form.otherFixedCost) / form.operatingDays)
      const profit = revenue - variableCost - fixedCost

      cumulativeProfit += profit
      totalRevenue += revenue
      totalCost += variableCost + fixedCost

      if (!bepDay && cumulativeProfit >= 0) bepDay = day

      metrics.push({
        day,
        orders,
        revenue,
        variableCost,
        fixedCost,
        profit,
        cumulativeProfit,
        cashBalance: form.initialBudget + cumulativeProfit,
      })
    }

    setReport({
      location,
      assumption: form,
      metrics,
      summary: {
        totalRevenue,
        totalCost,
        totalProfit: totalRevenue - totalCost,
        bepDay,
        cashShortageRisk: form.initialBudget + cumulativeProfit < form.monthlyRent ? '높음' : '낮음',
      },
    })
    setStep(3)
  }

  const send = (text) => {
    setMessages((prev) => [...prev, { role: 'user', text }])
    setBusy(true)
    setTyping('finance')
    window.setTimeout(() => {
      setTyping(null)
      setMessages((prev) => [
        ...prev,
        { agent: 'finance', text: '요청을 반영할 준비가 되어 있어요. 백엔드 계산 API가 연결되면 이 자리에서 값을 다시 계산하고 리포트를 갱신하면 됩니다.' },
      ])
      setBusy(false)
    }, 900)
  }

  const handleSave = async () => {
    if (!report || savingReport) return

    try {
      setSavingReport(true)
      await savedResultApi.save(buildSimulationSavedReport({
        workspace,
        location,
        assumption,
        report,
      }))
      go('saved')
    } catch (error) {
      window.alert(error.message ?? '리포트를 저장하지 못했습니다.')
    } finally {
      setSavingReport(false)
    }
  }

  return (
    <main className={`feature-page simulator-feature-page ${showChat ? 'with-chat' : 'no-chat'}`}>
      <section className="report-area">
        <div className="simulator-page">
          <div className="simulator-header">
            <div>
              <h1>창업 시뮬레이션</h1>
              <p>지도에서 위치를 고르고 지역 평균 임대료와 판매 가정을 반영해 첫 30일 손익을 예측합니다.</p>
            </div>
          </div>

          {!idea ? (
            <IdeaRequired go={go} />
          ) : (
            <>
              <div className="sim-selected-idea">
                <div>
                  <span>선택한 창업 아이템</span>
                  <b>{idea.title}</b>
                  <p>{idea.reason}</p>
                </div>
                {idea.score && <em>적합도 {idea.score}</em>}
              </div>

              <Stepper step={step} onJump={setStep} />

              {step === 1 && <RoadviewPicker onSelect={handleLocationSelect} />}
              {step === 2 && (
                <AssumptionForm
                  location={location}
                  idea={idea}
                  onBack={() => setStep(1)}
                  onRun={handleRunSimulation}
                />
              )}
              {step === 3 && (
                <DailyReportChart
                  data={report}
                  assumption={assumption}
                  location={location}
                  onBack={() => setStep(2)}
                  onLocationEdit={() => setStep(1)}
                  onSave={handleSave}
                />
              )}
            </>
          )}
        </div>
      </section>

      {showChat && (
        <aside className="feature-chat">
          <header style={{ color: agent.color }}>
            <AgentAvatar id="finance" />
            <div>
              <b>{agentDisplayName}</b>
              <small>월세와 손익을 함께 봅니다</small>
            </div>
          </header>
          <div className="feature-chat-body" ref={chatRef}>
            {messages.map((message, index) => <ChatRow key={index} message={message} />)}
            {typing && <TypingRow agent={typing} />}
          </div>
          <ChatInput
            onSend={send}
            disabled={busy}
            placeholder="시뮬레이션을 어떻게 바꿀까요?"
            accent={agent.color}
            suggestions={['건당 금액 500원 올리면?', '광고비를 줄이면 어때?', '판매/이용 건수가 20% 줄면?']}
          />
        </aside>
      )}
    </main>
  )
}
