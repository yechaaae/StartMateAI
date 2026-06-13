import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { operationFeedbackApi, savedResultApi } from '../../../shared/api/client'
import { agents } from '../../../shared/data/agents'
import { features } from '../../../shared/data/features'
import { AgentAvatar } from '../../../shared/components/AgentAvatar'
import { Icon } from '../../../shared/components/Icon'
import { ChatInput } from '../../chat/ChatInput'
import { ChatRow } from '../../chat/ChatRow'
import {
  clearActiveProgressByRequest,
  listActiveProgresses,
  resolveTypingAgent,
  upsertActiveProgress,
} from '../../chat/chatProgressState'
import { RotatingStatusProgress } from '../../chat/RotatingStatusProgress'
import { TypingRow } from '../../chat/TypingRow'
import { runSupportProgramSearch } from '../../reports/supportProgramSearch'
import {
  mergeSupportProgramHistory,
  readSupportProgramHistory,
  removeSupportProgramHistoryItem,
  writeSupportProgramHistory,
} from '../../reports/supportProgramStorage'
import {
  createChatEventSource,
  createFeatureChatRoom,
  getChatMessages,
  getFeatureChatRoom,
  getFeatureChatRooms,
  sendChatMessage,
  updateFeatureChatRoomTitle,
} from '../../chat/chatApi'
import {
  normalizeAgentProgressEvent,
  normalizeAgentProgressMessage,
  normalizeChatMessage,
  normalizeStatusEvent,
  reportDataFromMessage,
  upsertMessage,
} from '../../chat/chatMappers'
import { Report } from '../../reports/Report'
import { buildOperationFeedbackPayload } from '../../reports/operationFeedbackLogic'
import { buildFeatureSavedReport } from '../../reports/savedReportPayload'
import { buildCurrentResult, buildFeatureSeed, buildWorkspacePatch } from '../featureChatContext'
import { buildFeaturePageTheme } from './featurePageTheme'
import './FeaturePage.css'

const FEATURE_TARGETS = {
  item: 'ITEM',
  simulator: 'SIMULATOR',
  support: 'SUPPORT',
  plan: 'PLAN',
  operation: 'OPERATION',
  sns: 'SNS',
}

const RESULT_TYPES = {
  item: 'IDEA_REPORT',
  simulator: 'SIMULATION_REPORT',
  support: 'SUPPORT_REPORT',
  plan: 'PLAN_REPORT',
  operation: 'OPERATION_REPORT',
  sns: 'SNS_REPORT',
}

const FEATURE_SUGGESTIONS = {
  item: [
    '초기 자본에 맞게 더 현실적인 방향으로 바꿔줘',
    '20대 여성 고객층 기준으로 다시 정리해줘',
    '지원사업과 연결하기 좋은 아이템으로 좁혀줘',
  ],
  simulator: [
    '손익분기점을 더 빨리 만들려면 어떻게 해야 해?',
    '가격을 올리면 어떤 리스크가 생길까?',
    '초기 비용을 줄일 수 있는 방안을 알려줘',
  ],
  support: [
    '선정 가능성이 높은 순서로 정리해줘',
    '서류 준비 우선순위를 알려줘',
    '주의할 조건만 따로 뽑아줘',
  ],
  plan: [
    '시장 분석 문단을 더 설득력 있게 써줘',
    '지원사업 제출용 톤으로 다듬어줘',
    '수익 모델 부분을 더 구체화해줘',
  ],
  operation: [
    '매출 개선 우선순위를 정리해줘',
    '광고 전환율이 낮은 원인을 짚어줘',
    '바로 실행할 액션 아이템 3개만 줘',
  ],
  sns: [
    '인스타 릴스용 카피로 바꿔줘',
    '좀 더 친근한 말투로 다듬어줘',
    '해시태그를 지역 중심으로 다시 짜줘',
  ],
}

const GENERATE_REPORT_PROMPT = '현재 기능 페이지에 표시할 최종 리포트를 각 Agent가 함께 검토해서 생성해줘.'

export const FeaturePage = ({
  id,
  go,
  user,
  startupProfile,
  workspaceContext,
  onWorkspaceContextChange,
  workspace,
  setWorkspace,
}) => {
  const feature = features[id]
  const agent = agents[feature.agent]
  const targetFeature = FEATURE_TARGETS[id] ?? id.toUpperCase()
  const currentResultType = RESULT_TYPES[id] ?? 'FEATURE_REPORT'
  const featureSeed = buildFeatureSeed(id, workspaceContext)
  const helperText = id === 'item'
    ? '오른쪽 리포트에서 고른 아이템을 기준으로 바로 대화할 수 있어요.'
    : id === 'support'
      ? '프로필, 아이템, 현재 보고 있는 지원사업을 함께 보고 대화해요.'
      : id === 'plan'
        ? '초안, 연결된 지원사업, 선택한 문단을 같이 넘겨서 보완할 수 있어요.'
        : id === 'simulator'
          ? '아이템과 시뮬레이션 수치를 함께 보고 수익성을 같이 점검해요.'
          : id === 'operation'
            ? '운영 지표와 개선 제안을 바탕으로 다음 액션을 정리할 수 있어요.'
            : '홍보 초안과 운영 맥락을 함께 보고 카피를 다듬을 수 있어요.'

  const [data, setData] = useState(featureSeed.data)
  const [selectedIdeaRank, setSelectedIdeaRank] = useState(featureSeed.selectedIdeaRank)
  const [selectedSupportTitle, setSelectedSupportTitle] = useState(featureSeed.selectedSupportTitle)
  const [selectedOperationSuggestionTitle, setSelectedOperationSuggestionTitle] = useState(
    featureSeed.selectedOperationSuggestionTitle,
  )
  const [supportSearchMode, setSupportSearchMode] = useState(featureSeed.supportSearchMode)
  const [supportUserGoal, setSupportUserGoal] = useState(featureSeed.supportUserGoal)
  const [supportRegionBasis, setSupportRegionBasis] = useState(featureSeed.supportRegionBasis)
  const [supportSearchLoading, setSupportSearchLoading] = useState(false)
  const [supportHasSearched, setSupportHasSearched] = useState(false)
  const [savedSupportPrograms, setSavedSupportPrograms] = useState(() => (
    id === 'support' ? readSupportProgramHistory() : []
  ))
  const [focusedSectionTitle, setFocusedSectionTitle] = useState(featureSeed.focusedSectionTitle)
  const [planGoal, setPlanGoal] = useState(featureSeed.planGoal)
  const [messages, setMessages] = useState([])
  const [rooms, setRooms] = useState([])
  const [room, setRoom] = useState(null)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [creatingRoom, setCreatingRoom] = useState(false)
  const [connection, setConnection] = useState('idle')
  const [statusMap, setStatusMap] = useState({})
  const [activeProgressMap, setActiveProgressMap] = useState(new Map())
  const [error, setError] = useState('')
  const [sessionMenuOpen, setSessionMenuOpen] = useState(false)
  const [editingRoomId, setEditingRoomId] = useState(null)
  const [titleDraft, setTitleDraft] = useState('')
  const [savingTitle, setSavingTitle] = useState(false)
  const [savingReport, setSavingReport] = useState(false)
  const [aiReportStatus, setAiReportStatus] = useState('idle')
  const [streamVersion, setStreamVersion] = useState(0)

  const chatRef = useRef(null)
  const sessionMenuRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const hiddenRequestIdsRef = useRef(new Set())
  const autoGenerationKeysRef = useRef(new Set())

  const applyReportData = useCallback((reportData) => {
    setData(reportData)
    if (id === 'item') {
      setSelectedIdeaRank(reportData.items?.[0]?.rank ?? null)
    }
    if (id === 'support') {
      setSelectedSupportTitle(reportData.list?.[0]?.title ?? null)
      if (reportData.list?.length) {
        setSupportHasSearched(true)
      }
    }
    if (id === 'plan') {
      setFocusedSectionTitle(reportData.sections?.[0]?.[0] ?? null)
    }
    if (id === 'operation') {
      const firstSuggestion = reportData.suggestions?.[0]
      setSelectedOperationSuggestionTitle(
        Array.isArray(firstSuggestion) ? firstSuggestion[0] : firstSuggestion?.title ?? null,
      )
    }
  }, [id])

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight
    }
  }, [messages, activeProgressMap, statusMap])

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

    const loadLatestReport = async () => {
      try {
        setAiReportStatus('loading')
        const latest = await savedResultApi.latest(targetFeature)
        if (!active) {
          return
        }
        const reportData = latest?.payload?.reportData
        if (reportData) {
          applyReportData(reportData)
          setAiReportStatus('ready')
        } else if (id === 'operation') {
          // 운영 피드백은 사용자가 직접 입력하는 폼이므로 AI 생성 없이 빈 폼을 바로 보여준다.
          setAiReportStatus('ready')
        } else {
          setAiReportStatus('empty')
        }
      } catch (nextError) {
        if (!active) {
          return
        }
        setError(nextError.message ?? '최신 리포트를 불러오지 못했습니다.')
        setAiReportStatus('error')
      }
    }

    loadLatestReport()

    return () => {
      active = false
    }
  }, [applyReportData, id, targetFeature])

  useEffect(() => {
    let active = true

    const bootstrap = async () => {
      try {
        setLoading(true)
        setError('')

        const roomListResponse = await getFeatureChatRooms(targetFeature)
        if (!active) {
          return
        }

        const nextRooms = roomListResponse.rooms ?? []
        if (nextRooms.length) {
          setRooms(nextRooms)
          setRoom(nextRooms[0])
          return
        }

        const fallbackRoom = await getFeatureChatRoom(targetFeature)
        if (!active) {
          return
        }
        setRooms([fallbackRoom])
        setRoom(fallbackRoom)
      } catch (nextError) {
        if (!active) {
          return
        }
        setError(nextError.message ?? '기능 채팅을 준비하지 못했습니다.')
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    bootstrap()

    return () => {
      active = false
    }
  }, [targetFeature])

  useEffect(() => {
    setStreamVersion(0)
  }, [room?.roomId])

  useEffect(() => {
    if (!room?.roomId) {
      return undefined
    }

    let active = true
    const eventSource = createChatEventSource(room.roomId)

    const loadHistory = async ({ reset = false, showLoading = false } = {}) => {
      try {
        if (showLoading) {
          setLoading(true)
        }
        setError('')
        if (reset) {
          setMessages([])
          setStatusMap({})
          setActiveProgressMap(new Map())
          setConnection('connecting')
        }

        const history = await getChatMessages(room.roomId)
        if (!active) {
          return
        }
        const nextMessages = history.messages.map(normalizeChatMessage)
        setMessages(nextMessages)
      } catch (nextError) {
        if (!active) {
          return
        }
        setError(nextError.message ?? '이전 대화를 불러오지 못했습니다.')
      } finally {
        if (active && showLoading) {
          setLoading(false)
        }
      }
    }

    loadHistory({ reset: true, showLoading: true })

    eventSource.addEventListener('chat-connected', () => {
      if (!active) {
        return
      }
      setConnection('connected')
      if (streamVersion > 0) {
        loadHistory()
      }
    })

    eventSource.addEventListener('chat-message', (event) => {
      if (!active) {
        return
      }
      const payload = JSON.parse(event.data)
      if (!payload.message) {
        return
      }
      const nextMessage = normalizeChatMessage(payload.message)
      // 운영 피드백 폼은 사용자 입력이 원본이라 AI 응답으로 덮어쓰지 않는다.
      const nextReport = id === 'operation' ? null : reportDataFromMessage(nextMessage, id)
      if (nextReport) {
        applyReportData(nextReport)
        setAiReportStatus('ready')
      }
      setMessages((prev) => upsertMessage(prev, nextMessage))
    })

    eventSource.addEventListener('chat-status', (event) => {
      if (!active) {
        return
      }
      const payload = JSON.parse(event.data)
      if (!payload.status) {
        return
      }
      const nextStatus = normalizeStatusEvent(payload.status)
      if (hiddenRequestIdsRef.current.has(nextStatus.requestId)) {
        if (nextStatus.status === 'FAILED') {
          setAiReportStatus('error')
        }
        if (['COMPLETED', 'FAILED'].includes(nextStatus.status)) {
          setActiveProgressMap((prev) => clearActiveProgressByRequest(prev, nextStatus.requestId))
        }
        return
      }
      setStatusMap((prev) => ({ ...prev, [nextStatus.requestId]: nextStatus }))
      if (['COMPLETED', 'FAILED'].includes(nextStatus.status)) {
        setActiveProgressMap((prev) => clearActiveProgressByRequest(prev, nextStatus.requestId))
      }
    })

    eventSource.addEventListener('agent-progress', (event) => {
      if (!active) {
        return
      }
      const payload = JSON.parse(event.data)
      if (!payload.agentProgress) {
        return
      }
      const nextProgress = normalizeAgentProgressEvent(payload.agentProgress)
      setActiveProgressMap((prev) => upsertActiveProgress(prev, nextProgress))
      if (hiddenRequestIdsRef.current.has(nextProgress.requestId)) {
        return
      }
      if (nextProgress.viewType !== 'status' && nextProgress.agent && nextProgress.message) {
        setMessages((prev) => upsertMessage(prev, normalizeAgentProgressMessage(nextProgress)))
      }
    })

    eventSource.onerror = () => {
      if (!active) {
        return
      }
      setConnection('connecting')
      if (reconnectTimeoutRef.current) {
        return
      }
      reconnectTimeoutRef.current = window.setTimeout(() => {
        reconnectTimeoutRef.current = null
        if (!active) {
          return
        }
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
  }, [applyReportData, id, room?.roomId, streamVersion])

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
      ? feature.agent
      : null
  const runningAgentKey = typing && agents[typing] ? typing : null
  const visibleAgentKeys = useMemo(() => {
    const ordered = []
    for (const progress of activeProgresses) {
      const key = progress.agent?.key
      if (!key || !agents[key] || ordered.includes(key)) continue
      ordered.push(key)
    }
    return ordered
  }, [activeProgresses])
  const visibleAgents = visibleAgentKeys.map((key) => ({ key, ...agents[key] }))
  const visibleAgentStatus = runningAgentKey && agents[runningAgentKey]
    ? '현재 답변을 준비하고 있어요.'
    : visibleAgents.length
      ? '이번 답변에 참여 중인 전문가들이에요.'
      : helperText

  useEffect(() => {
    onWorkspaceContextChange?.(buildWorkspacePatch({
      featureId: id,
      data,
      selectedIdeaRank,
      selectedSupportTitle,
      selectedOperationSuggestionTitle,
      supportSearchMode,
      supportUserGoal,
      supportRegionBasis,
      focusedSectionTitle,
      planGoal,
    }))
  }, [
    data,
    focusedSectionTitle,
    id,
    onWorkspaceContextChange,
    planGoal,
    selectedIdeaRank,
    selectedOperationSuggestionTitle,
    selectedSupportTitle,
    supportRegionBasis,
    supportSearchMode,
    supportUserGoal,
  ])

  const currentResult = useMemo(
    () => buildCurrentResult({
      featureId: id,
      data,
      selectedIdeaRank,
      selectedSupportTitle,
      selectedOperationSuggestionTitle,
      supportSearchMode,
      supportUserGoal,
      supportRegionBasis,
      focusedSectionTitle,
      planGoal,
      workspaceContext,
      startupProfile,
    }),
    [
      data,
      focusedSectionTitle,
      id,
      planGoal,
      selectedIdeaRank,
      selectedOperationSuggestionTitle,
      selectedSupportTitle,
      startupProfile,
      supportRegionBasis,
      supportSearchMode,
      supportUserGoal,
      workspaceContext,
    ],
  )
  const resolvedIdeaId = workspaceContext?.selectedIdea?.rank ?? selectedIdeaRank ?? null

  const sendFeatureMessage = async (text, { hidden = false } = {}) => {
    if (!room?.roomId) {
      return null
    }
    if (!hidden) {
      setBusy(true)
    }
    setError('')

    try {
      const messageMetadata = { source: 'feature-page', featureId: id }
      if (hidden) {
        messageMetadata.hidden = true
        messageMetadata.reportGeneration = true
      }
      const response = await sendChatMessage(room.roomId, {
        userId: user?.id ?? null,
        content: text,
        metadata: JSON.stringify(messageMetadata),
        intent: 'auto',
        sessionType: 'FEATURE_CHAT',
        currentResultType,
        currentResultId: null,
        selectedIdeaId: resolvedIdeaId,
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
        setMessages((prev) => upsertMessage(prev, {
          id: response.messageId,
          role: 'user',
          senderType: response.senderType,
          userId: user?.id ?? null,
          agentId: null,
          agent: null,
          text: response.content,
          metadata: messageMetadata,
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
      }

      return response
    } catch (nextError) {
      setError(nextError.message ?? '메시지를 보내지 못했습니다.')
      throw nextError
    } finally {
      if (!hidden) {
        setBusy(false)
      }
    }
  }

  useEffect(() => {
    // 운영 피드백은 사용자 입력 폼이라 AI 자동 리포트 생성을 트리거하지 않는다.
    if (aiReportStatus !== 'empty' || !room?.roomId || id === 'operation') {
      return
    }

    const generationKey = `${targetFeature}:${room.roomId}`
    if (autoGenerationKeysRef.current.has(generationKey)) {
      return
    }

    autoGenerationKeysRef.current.add(generationKey)
    setAiReportStatus('loading')
    sendFeatureMessage(GENERATE_REPORT_PROMPT, { hidden: true })
      .catch(() => setAiReportStatus('error'))
  }, [aiReportStatus, id, room?.roomId, targetFeature])

  const updateRoomState = (updatedRoom) => {
    setRooms((prev) => prev.map((candidate) => (
      candidate.roomId === updatedRoom.roomId ? updatedRoom : candidate
    )))
    setRoom((prev) => (prev?.roomId === updatedRoom.roomId ? updatedRoom : prev))
  }

  const handleOperationFeedbackRequest = async () => {
    if (savingReport || id !== 'operation') {
      return
    }

    try {
      setSavingReport(true)
      setError('')
      await operationFeedbackApi.save(
        buildOperationFeedbackPayload(data, selectedOperationSuggestionTitle),
      )
    } catch (nextError) {
      setError(nextError.message ?? '운영 피드백을 저장하지 못했습니다.')
    } finally {
      setSavingReport(false)
    }
  }

  const handleSaveReport = async () => {
    if (savingReport || aiReportStatus !== 'ready') {
      return
    }

    try {
      setSavingReport(true)
      setError('')
      await savedResultApi.save(buildFeatureSavedReport({
        featureId: id,
        data,
        currentResult,
        selectedIdeaRank,
        selectedSupportTitle,
        selectedOperationSuggestionTitle,
        supportSearchMode,
        supportUserGoal,
        focusedSectionTitle,
        planGoal,
      }))
      go('saved')
    } catch (nextError) {
      setError(nextError.message ?? '리포트를 저장하지 못했습니다.')
    } finally {
      setSavingReport(false)
    }
  }

  const handleSend = async (text) => {
    if (busy || !room?.roomId) {
      return
    }
    try {
      await sendFeatureMessage(text)
    } catch (nextError) {
      setError(nextError.message ?? '메시지를 보내지 못했습니다.')
    }
  }

  const createSession = async () => {
    if (creatingRoom) {
      return
    }
    setCreatingRoom(true)
    setError('')

    try {
      const createdRoom = await createFeatureChatRoom(targetFeature)
      setRooms((prev) => [createdRoom, ...prev])
      setRoom(createdRoom)
      setSessionMenuOpen(false)
      setEditingRoomId(null)
    } catch (nextError) {
      setError(nextError.message ?? '새 기능 채팅 세션을 만들지 못했습니다.')
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
    if (savingTitle) {
      return
    }

    try {
      setSavingTitle(true)
      setError('')
      const updatedRoom = await updateFeatureChatRoomTitle(roomId, targetFeature, titleDraft)
      updateRoomState(updatedRoom)
      setEditingRoomId(null)
      setTitleDraft('')
    } catch (nextError) {
      setError(nextError.message ?? '세션 이름을 수정하지 못했습니다.')
    } finally {
      setSavingTitle(false)
    }
  }

  const handleSupportProgramSearch = async () => {
    if (supportSearchLoading) {
      return
    }

    setSupportSearchLoading(true)
    setError('')

    try {
      const filters = {
        recommendationBasis: supportSearchMode,
        priority: supportUserGoal,
        regionBasis: supportRegionBasis,
      }
      const results = await runSupportProgramSearch({
        ...filters,
        startupProfile,
        selectedIdea: workspaceContext?.selectedIdea ?? null,
      })

      setData((prev) => ({ ...prev, list: results }))
      setSelectedSupportTitle(results[0]?.title ?? null)
      const nextSavedPrograms = mergeSupportProgramHistory(readSupportProgramHistory(), results, filters)
      writeSupportProgramHistory(nextSavedPrograms)
      setSavedSupportPrograms(nextSavedPrograms)
      setSupportHasSearched(true)
    } catch (nextError) {
      setError(nextError.message ?? '지원사업 추천 결과를 불러오지 못했습니다.')
    } finally {
      setSupportSearchLoading(false)
    }
  }

  const handleDeleteSavedSupportProgram = (programId) => {
    const nextSavedPrograms = removeSupportProgramHistoryItem(readSupportProgramHistory(), programId)
    writeSupportProgramHistory(nextSavedPrograms)
    setSavedSupportPrograms(nextSavedPrograms)
  }

  const handleRegenerateReport = () => {
    if (!room?.roomId || aiReportStatus === 'loading') {
      return
    }
    setAiReportStatus('loading')
    sendFeatureMessage(GENERATE_REPORT_PROMPT, { hidden: true })
      .catch(() => setAiReportStatus('error'))
  }

  return (
    <main className="feature-page" style={buildFeaturePageTheme(feature, agents)}>
      <section className="report-area">
        <div className="feature-page-header">
          <div>
            <h1>{feature.title}</h1>
            <p>{feature.sub}</p>
          </div>
          <div className="report-title-actions">
            {/* 운영 피드백은 사용자 입력 폼이라 AI 생성/일반 저장 버튼 대신 폼 내부 저장 버튼을 쓴다. */}
            {id !== 'operation' && (
              <>
                <button
                  type="button"
                  className="secondary-chip"
                  onClick={handleRegenerateReport}
                  disabled={aiReportStatus === 'loading' || loading || !room?.roomId}
                >
                  <Icon name="refresh" size={15} />
                  <span>
                    {aiReportStatus === 'loading'
                      ? 'AI 생성 중'
                      : aiReportStatus === 'empty'
                        ? 'AI 리포트 생성'
                        : 'AI 리포트 갱신'}
                  </span>
                </button>
                {aiReportStatus === 'ready' && (
                  <button
                    type="button"
                    className="secondary-chip"
                    onClick={handleSaveReport}
                    disabled={savingReport || aiReportStatus !== 'ready'}
                  >
                    <Icon name="bookmark" size={15} />
                    <span>{savingReport ? '저장 중' : '리포트 저장'}</span>
                  </button>
                )}
              </>
            )}
          </div>
        </div>
        {aiReportStatus === 'ready' ? (
          <Report
            id={id}
            data={data}
            setData={setData}
            go={go}
            workspace={workspace}
            setWorkspace={setWorkspace}
            selectedIdeaRank={selectedIdeaRank}
            onSelectIdea={setSelectedIdeaRank}
            selectedSupportTitle={selectedSupportTitle}
            onSelectSupport={setSelectedSupportTitle}
            selectedOperationSuggestionTitle={selectedOperationSuggestionTitle}
            onSelectOperationSuggestion={setSelectedOperationSuggestionTitle}
            supportSearchMode={supportSearchMode}
            onChangeSupportSearchMode={setSupportSearchMode}
            supportUserGoal={supportUserGoal}
            onChangeSupportUserGoal={setSupportUserGoal}
            supportRegionBasis={supportRegionBasis}
            onChangeSupportRegionBasis={setSupportRegionBasis}
            supportSearchLoading={supportSearchLoading}
            supportHasSearched={supportHasSearched}
            onRunSupportSearch={handleSupportProgramSearch}
            savedSupportPrograms={savedSupportPrograms}
            onDeleteSavedSupportProgram={handleDeleteSavedSupportProgram}
            focusedSectionTitle={focusedSectionTitle}
            onFocusSection={setFocusedSectionTitle}
            planGoal={planGoal}
            onChangePlanGoal={setPlanGoal}
            onRequestOperationFeedback={handleOperationFeedbackRequest}
            operationFeedbackSaving={savingReport}
          />
        ) : (
          <div className="ai-report-state">
            <AgentAvatar id={feature.agent} size={56} active={aiReportStatus === 'loading'} />
            <h2>
              {aiReportStatus === 'loading'
                ? 'AI 리포트를 준비하고 있어요'
                : aiReportStatus === 'error'
                  ? 'AI 리포트를 만들지 못했어요'
                  : '아직 생성된 AI 리포트가 없어요'}
            </h2>
            <p>
              {aiReportStatus === 'loading'
                ? '저장된 최신 리포트를 확인하거나 새 리포트를 생성하는 중입니다.'
                : aiReportStatus === 'error'
                  ? '잠시 후 다시 생성하거나 채팅으로 요청을 보내주세요.'
                  : '저장된 리포트가 없어 Agent들이 현재 프로필과 작업 맥락으로 새 리포트를 준비합니다.'}
            </p>
            {aiReportStatus !== 'loading' && (
              <button type="button" className="secondary-chip" onClick={handleRegenerateReport}>
                <Icon name="refresh" size={15} />
                {aiReportStatus === 'empty' ? 'AI 리포트 생성' : '다시 생성'}
              </button>
            )}
          </div>
        )}
      </section>

      <aside className="feature-chat">
        <header
          className={visibleAgents.length ? 'feature-chat-agent-header active' : 'feature-chat-agent-header'}
          style={{ color: runningAgentKey && agents[runningAgentKey] ? agents[runningAgentKey].color : agent.color }}
        >
          {visibleAgents.length ? (
            <div className="feature-chat-agent-stack">
              {visibleAgents.map((visibleAgent) => (
                <AgentAvatar
                  key={visibleAgent.key}
                  id={visibleAgent.key}
                  active={visibleAgent.key === runningAgentKey}
                />
              ))}
            </div>
          ) : (
            <span className="feature-chat-agent-placeholder">
              <Icon name="discuss" size={18} />
            </span>
          )}
          <div>
            <b>
              {visibleAgents.length
                ? visibleAgents.map((visibleAgent) => visibleAgent.name).join(' · ')
                : 'AI 전문가 채팅'}
            </b>
            <small>{visibleAgentStatus}</small>
          </div>
        </header>

        <div className="feature-session-toolbar">
          <div className="chat-session-picker" ref={sessionMenuRef}>
            <button
              className={sessionMenuOpen ? 'chat-session-trigger on' : 'chat-session-trigger'}
              onClick={() => setSessionMenuOpen((prev) => !prev)}
              disabled={!rooms.length}
            >
              <div className="chat-session-trigger-copy">
                <small>{targetFeature} 세션</small>
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

          <button className="chat-session-new" onClick={createSession} disabled={creatingRoom || busy}>
            <Icon name="plus" size={16} />
            <span>{creatingRoom ? '만드는 중' : '새 세션'}</span>
          </button>
        </div>

        <div className="feature-chat-body" ref={chatRef}>
          {loading && <div className="chat-loading">대화를 불러오는 중...</div>}
          {!loading && !messages.length && (
            <div className="feature-chat-empty">
              <AgentAvatar id={feature.agent} size={52} active />
              <strong>{agent.name}가 리포트를 보고 있어요.</strong>
              <p>지금 보고 있는 결과를 기준으로 방향 수정, 비교, 다음 단계 질문을 이어갈 수 있어요.</p>
            </div>
          )}
          {messages
            .filter((message) => !message.metadata?.hidden)
            .map((message) => <ChatRow key={message.id} message={message} onOpenReport={go} />)}
          <RotatingStatusProgress progresses={statusProgresses} />
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
          onSend={handleSend}
          disabled={busy || loading || connection === 'error' || !room?.roomId}
          placeholder="이 리포트를 바탕으로 더 물어보세요."
          accent={runningAgentKey && agents[runningAgentKey] ? agents[runningAgentKey].color : agent.color}
          suggestions={FEATURE_SUGGESTIONS[id] ?? []}
        />
      </aside>
    </main>
  )
}
