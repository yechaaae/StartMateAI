import { useEffect, useMemo, useRef, useState } from 'react'
import { savedResultApi } from '../../shared/api/client'
import { RoadviewPicker } from '../simulator/RoadviewPicker'
import { AssumptionForm } from '../simulator/AssumptionForm'
import { DailyReportChart } from '../simulator/DailyReportChart'
import { Icon } from '../../shared/components/Icon'
import { agents } from '../../shared/data/agents'
import { AgentAvatar } from '../../shared/components/AgentAvatar'
import { ChatInput } from '../chat/ChatInput'
import { FloatingChat } from '../chat/FloatingChat'
import { buildDailySimulation } from '../simulator/simulationCalculations'
import {
  clearActiveProgressByRequest,
  listActiveProgresses,
  resolveTypingAgent,
  upsertActiveProgress,
} from '../chat/chatProgressState'
import {
  createChatEventSource,
  createFeatureChatRoom,
  getChatMessages,
  getFeatureChatRoom,
  getFeatureChatRooms,
  sendChatMessage,
} from '../chat/chatApi'
import {
  normalizeAgentProgressEvent,
  normalizeAgentProgressMessage,
  normalizeChatMessage,
  normalizeStatusEvent,
} from '../chat/chatMappers'
import { useChatMessageQueue } from '../chat/useChatMessageQueue'
import { buildSimulationSavedReport } from '../reports/savedReportPayload'

const steps = ['위치 설정', '가정값 설정', '리포트 확인']
const TARGET_FEATURE = 'SIMULATOR'
const CURRENT_RESULT_TYPE = 'SIMULATION_REPORT'
const GENERATE_REPORT_PROMPT = '현재 시뮬레이션 결과를 각 Agent가 함께 검토해서 기능 페이지에 표시할 최종 리포트로 정리해줘.'
const welcomeMessage = {
  id: 'simulator-welcome',
  role: 'agent',
  senderType: 'AGENT',
  agent: 'finance',
  text: '30일 시뮬레이션 리포트를 만들면 AI Agent들이 수익성, 아이템 적합도, 시나리오를 함께 검토해요.',
  metadata: {},
  createdAt: null,
}

const reportDataFromMessage = (message) => {
  const result = message?.metadata?.result
  if (result?.shouldCreateResult !== true) return null
  const payload = result?.payload
  if (payload?.featureId !== 'simulator') return null
  return payload.reportData ?? null
}

const simulationReportFromReportData = (reportData) => {
  if (reportData?.metrics && reportData?.summary) return reportData
  if (reportData?.report?.metrics && reportData?.report?.summary) return reportData.report
  return null
}

const firstNonBlank = (...values) => (
  values
    .map((value) => String(value ?? '').trim())
    .find(Boolean) ?? ''
)

// 가정값 제안 응답(저장 안 함)에서 가정값을 읽는다. shouldCreateResult 여부와 무관.
const assumptionFromMessage = (message) => {
  const payload = message?.metadata?.result?.payload
  if (payload?.featureId !== 'simulator') return null
  const assumption = payload?.reportData?.assumption
  return assumption && typeof assumption === 'object' ? assumption : null
}

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

export const SimulatorPage = ({ go, workspace, user, startupProfile }) => {
  const [step, setStep] = useState(1)
  const [location, setLocation] = useState(null)
  const [assumption, setAssumption] = useState(null)
  const [report, setReport] = useState(null)
  const [suggestedAssumption, setSuggestedAssumption] = useState(null)
  const [assumptionLoading, setAssumptionLoading] = useState(false)
  const [savedReports, setSavedReports] = useState([])
  const [savedMenuOpen, setSavedMenuOpen] = useState(false)
  const savedMenuRef = useRef(null)
  const {
    messages,
    pushImmediate,
    enqueue,
    flush,
    reset: resetMessages,
    isDraining,
  } = useChatMessageQueue([welcomeMessage])
  const [room, setRoom] = useState(null)
  const [busy, setBusy] = useState(false)
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState('')
  const [savingReport, setSavingReport] = useState(false)
  const [creatingRoom, setCreatingRoom] = useState(false)
  const [statusMap, setStatusMap] = useState({})
  const [activeProgressMap, setActiveProgressMap] = useState(new Map())
  const hiddenRequestIdsRef = useRef(new Set())
  const agent = agents.finance
  const agentDisplayName = `${agent.label} 에이전트`
  const idea = workspace?.selectedIdea
  const showChat = step === 3 && report
  const initialMapRegion = useMemo(() => firstNonBlank(
    startupProfile?.businessRegion,
    workspace?.selectedIdea?.location,
    workspace?.selectedIdea?.region,
    startupProfile?.residenceRegion,
  ), [startupProfile, workspace])

  useEffect(() => {
    let active = true

    const bootstrap = async () => {
      try {
        setChatLoading(true)
        setChatError('')
        const roomListResponse = await getFeatureChatRooms(TARGET_FEATURE)
        if (!active) return

        const nextRooms = roomListResponse.rooms ?? []
        if (nextRooms.length) {
          setRoom(nextRooms[0])
          return
        }

        const fallbackRoom = await getFeatureChatRoom(TARGET_FEATURE)
        if (!active) return
        setRoom(fallbackRoom)
      } catch (error) {
        try {
          const createdRoom = await createFeatureChatRoom(TARGET_FEATURE)
          if (!active) return
          setRoom(createdRoom)
        } catch (createError) {
          if (active) setChatError(createError.message ?? error.message ?? '시뮬레이션 채팅을 준비하지 못했습니다.')
        }
      } finally {
        if (active) setChatLoading(false)
      }
    }

    bootstrap()

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    let active = true

    const loadLatestReport = async () => {
      try {
        const latest = await savedResultApi.latest(TARGET_FEATURE)
        if (!active) return
        if (latest?.payload?.reportData) {
          applyAiReportData(latest.payload.reportData)
        }
      } catch (error) {
        if (active) setChatError(error.message ?? '최신 시뮬레이션 리포트를 불러오지 못했습니다.')
      }
    }

    loadLatestReport()

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!room?.roomId) {
      return undefined
    }

    let active = true
    const eventSource = createChatEventSource(room.roomId)

    const loadHistory = async () => {
      try {
        setChatLoading(true)
        setChatError('')
        setStatusMap({})
        setActiveProgressMap(new Map())

        const history = await getChatMessages(room.roomId)
        if (!active) return

        const nextMessages = history.messages.map(normalizeChatMessage)
        resetMessages([welcomeMessage, ...nextMessages])
      } catch (error) {
        if (active) setChatError(error.message ?? '이전 시뮬레이션 대화를 불러오지 못했습니다.')
      } finally {
        if (active) setChatLoading(false)
      }
    }

    loadHistory()

    eventSource.addEventListener('chat-message', (event) => {
      if (!active) return
      const payload = JSON.parse(event.data)
      if (!payload.message) return
      const nextMessage = normalizeChatMessage(payload.message)
      const nextReportData = reportDataFromMessage(nextMessage)
      if (nextReportData) {
        // 리포트 패널 갱신은 도착 즉시(채팅 말풍선 순서만 큐가 통제).
        applyAiReportData(nextReportData)
      }
      const nextAssumption = assumptionFromMessage(nextMessage)
      if (nextAssumption) {
        setSuggestedAssumption(nextAssumption)
        setAssumptionLoading(false)
      }
      // 내 메시지는 즉시, 에이전트 답변은 큐를 거쳐 토론 뒤에 표시.
      if (nextMessage.role === 'user') {
        pushImmediate(nextMessage)
      } else {
        enqueue(nextMessage)
      }
    })

    eventSource.addEventListener('chat-status', (event) => {
      if (!active) return
      const payload = JSON.parse(event.data)
      if (!payload.status) return
      const nextStatus = normalizeStatusEvent(payload.status)

      if (['COMPLETED', 'FAILED'].includes(nextStatus.status)) {
        setActiveProgressMap((prev) => clearActiveProgressByRequest(prev, nextStatus.requestId))
      }

      if (hiddenRequestIdsRef.current.has(nextStatus.requestId)) {
        if (nextStatus.status === 'FAILED') {
          setChatError(nextStatus.errorMessage || 'AI 시뮬레이션 리포트를 갱신하지 못했습니다.')
        }
        return
      }
      setStatusMap((prev) => ({ ...prev, [nextStatus.requestId]: nextStatus }))
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
      if (active) setChatError('시뮬레이션 채팅 연결이 잠시 불안정합니다.')
    }

    return () => {
      active = false
      eventSource.close()
    }
  }, [room?.roomId])

  const currentResult = useMemo(() => ({
    featureId: 'simulator',
    startupProfile,
    workspaceIdea: idea ?? null,
    ideaContext: idea ?? null,
    location,
    assumption,
    report,
    simulationInput: {
      item: idea?.title ?? '선택한 창업 아이템',
      price: assumption?.pricePerOrder ?? null,
      capital: assumption?.initialBudget ?? null,
      startOrders: assumption?.expectedDailyOrders ?? null,
      growthPct: 20,
    },
  }), [assumption, idea, location, report, startupProfile])

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
      ? 'finance'
      : null

  const applyAiReportData = (reportData) => {
    const nextReport = simulationReportFromReportData(reportData)
    if (!nextReport) return
    setReport(nextReport)
    if (reportData.location || nextReport.location) setLocation(reportData.location ?? nextReport.location)
    if (reportData.assumption || nextReport.assumption) setAssumption(reportData.assumption ?? nextReport.assumption)
    setStep(3)
  }

  const refreshSavedReports = async () => {
    try {
      const response = await savedResultApi.list()
      const items = (response?.results ?? []).filter(
        (item) => String(item.sourceFeature ?? '').toLowerCase() === 'simulator',
      )
      setSavedReports(items)
    } catch {
      /* 저장 목록 조회 실패는 무시 */
    }
  }

  const loadSavedReport = async (savedResultId) => {
    setSavedMenuOpen(false)
    try {
      const detail = await savedResultApi.get(savedResultId)
      const reportData = detail?.payload?.reportData
      if (reportData) applyAiReportData(reportData)
    } catch (error) {
      setChatError(error.message ?? '저장한 결과를 불러오지 못했습니다.')
    }
  }

  useEffect(() => {
    refreshSavedReports()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const close = (event) => {
      if (savedMenuRef.current && !savedMenuRef.current.contains(event.target)) {
        setSavedMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const handleLocationSelect = (loc) => {
    setLocation(loc)
    setSuggestedAssumption(null) // 위치가 바뀌면 가정값을 새 위치 기준으로 다시 받는다.
    setStep(2)
  }

  const handleRunSimulation = (form) => {
    setAssumption(form)
    const simulation = buildDailySimulation(form)

    setReport({
      location,
      assumption: form,
      metrics: simulation.metrics,
      summary: simulation.summary,
    })
    setStep(3)
  }

  const sendFeatureMessage = async (text, { hidden = false, assumptionRequest = false } = {}) => {
    if (!room?.roomId) return null
    if (!hidden) setBusy(true)
    setChatError('')
    // 이전 턴이 아직 드립 중이면 즉시 비워 현재로 스냅하고 새 턴 시작.
    flush()

    try {
      const messageMetadata = { source: 'simulator-page', featureId: 'simulator' }
      if (hidden) {
        messageMetadata.hidden = true
        if (assumptionRequest) {
          messageMetadata.assumptionRequest = true
        } else {
          messageMetadata.reportGeneration = true
        }
      }
      const response = await sendChatMessage(room.roomId, {
        userId: user?.id ?? null,
        content: text,
        metadata: JSON.stringify(messageMetadata),
        intent: 'auto',
        sessionType: 'FEATURE_CHAT',
        currentResultType: CURRENT_RESULT_TYPE,
        currentResultId: null,
        selectedIdeaId: idea?.rank ?? null,
        candidateAgents: [],
        currentResult,
      })

      if (hidden) {
        hiddenRequestIdsRef.current.add(response.requestId)
        setStatusMap((prev) => {
          const next = { ...prev }
          delete next[response.requestId]
          return next
        })
      } else {
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
      }
      return response
    } catch (error) {
      setChatError(error.message ?? '메시지를 보내지 못했습니다.')
      throw error
    } finally {
      if (!hidden) setBusy(false)
    }
  }

  const send = async (text) => {
    if (busy || !room?.roomId) return
    try {
      await sendFeatureMessage(text)
    } catch {
      // Error state is set by sendFeatureMessage.
    }
  }

  const handleGenerateAiReport = () => {
    if (!room?.roomId || !report || busy) return
    sendFeatureMessage(GENERATE_REPORT_PROMPT, { hidden: true }).catch(() => {})
  }

  const createSession = async () => {
    if (creatingRoom) return
    setCreatingRoom(true)
    setChatError('')
    try {
      const createdRoom = await createFeatureChatRoom(TARGET_FEATURE)
      // 룸이 바뀌면 SSE 효과가 대화/상태를 새로 불러온다(welcomeMessage만 남음).
      setRoom(createdRoom)
    } catch (error) {
      setChatError(error.message ?? '새 채팅을 시작하지 못했습니다.')
    } finally {
      setCreatingRoom(false)
    }
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
      await refreshSavedReports()
      setSavedMenuOpen(true) // 저장한 결과를 우측 상단 드롭다운에서 바로 확인.
    } catch (error) {
      window.alert(error.message ?? '리포트를 저장하지 못했습니다.')
    } finally {
      setSavingReport(false)
    }
  }

  // 가정값 단계 진입 시 AI(파이낸스)에게 가정값 제안을 요청해 폼을 자동 프리필한다.
  useEffect(() => {
    if (step !== 2 || !idea || !location || !room?.roomId) return
    if (suggestedAssumption || assumptionLoading) return
    setAssumptionLoading(true)
    sendFeatureMessage('이 아이템과 위치 기준으로 시뮬레이션 가정값을 제안해줘.', {
      hidden: true,
      assumptionRequest: true,
    }).catch(() => setAssumptionLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, idea, location, room?.roomId, suggestedAssumption, assumptionLoading])

  return (
    <main className={`feature-page simulator-feature-page ${showChat ? 'with-chat' : 'no-chat'}`}>
      <section className="report-area">
        <div className="simulator-page">
          <div className="simulator-header">
            <div>
              <h1>창업 시뮬레이션</h1>
              <p>지도에서 위치를 고르고 지역 평균 임대료와 판매 가정을 반영해 첫 30일 손익을 예측합니다.</p>
            </div>
            <div className="sim-saved-menu" ref={savedMenuRef}>
              <button
                type="button"
                className="sim-saved-trigger"
                aria-expanded={savedMenuOpen}
                onClick={() => setSavedMenuOpen((open) => !open)}
              >
                <Icon name="bookmark" size={15} />
                저장한 결과{savedReports.length ? ` ${savedReports.length}` : ''}
                <Icon name="chevron" size={14} />
              </button>
              {savedMenuOpen && (
                <div className="sim-saved-dropdown">
                  {savedReports.length === 0 ? (
                    <p className="sim-saved-empty">저장한 결과가 아직 없어요.</p>
                  ) : (
                    savedReports.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        className="sim-saved-item"
                        onClick={() => loadSavedReport(item.id)}
                      >
                        <b>{item.title}</b>
                        {(item.createdAt || item.summary) && (
                          <small>
                            {item.createdAt ? item.createdAt.slice(0, 10) : ''}
                            {item.summary ? ` · ${item.summary}` : ''}
                          </small>
                        )}
                      </button>
                    ))
                  )}
                </div>
              )}
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
                </div>
              </div>

              <Stepper step={step} onJump={setStep} />

              {step === 1 && <RoadviewPicker initialRegion={initialMapRegion} onSelect={handleLocationSelect} />}
              {step === 2 && (
                <AssumptionForm
                  location={location}
                  idea={idea}
                  suggested={suggestedAssumption}
                  loading={assumptionLoading}
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
        <FloatingChat
          accent={agent.color}
          active={Boolean(typing || isDraining)}
          launcherLabel={`${agentDisplayName}에게 시뮬레이션에 대해 물어보기`}
          headerSlot={(
            <div className="chat-dock-agent" style={{ color: agent.color }}>
              <AgentAvatar id="finance" />
              <div className="chat-dock-agent-copy">
                <b>{agentDisplayName}</b>
                <small>월세와 손익을 함께 봅니다</small>
              </div>
            </div>
          )}
          onNewChat={createSession}
          newChatLabel={creatingRoom ? '만드는 중' : '새 채팅'}
          newChatDisabled={creatingRoom || busy}
          toolbarExtra={(
            <button
              type="button"
              className="secondary-chip sim-ai-refresh"
              onClick={handleGenerateAiReport}
              disabled={busy || chatLoading || !room?.roomId}
            >
              <Icon name="refresh" size={14} />
              AI 리포트 갱신
            </button>
          )}
          loading={chatLoading}
          messages={messages.filter((message) => !message.metadata?.hidden)}
          statusProgresses={statusProgresses}
          typing={(typing || isDraining) ? (typing || 'finance') : null}
          onOpenReport={go}
          failedStatus={latestStatus}
          error={chatError}
          input={(
            <ChatInput
              onSend={send}
              disabled={busy || chatLoading || !room?.roomId}
              placeholder="시뮬레이션을 어떻게 바꿀까요?"
              accent={agent.color}
              suggestions={['건당 금액 500원 올리면?', '광고비를 줄이면 어때?', '판매/이용 건수가 20% 줄면?']}
            />
          )}
        />
      )}
    </main>
  )
}
