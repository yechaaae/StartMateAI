import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { operationFeedbackApi, savedResultApi } from '../../../shared/api/client'
import { agents } from '../../../shared/data/agents'
import { features } from '../../../shared/data/features'
import { AgentAvatar } from '../../../shared/components/AgentAvatar'
import { Icon } from '../../../shared/components/Icon'
import { ChatInput } from '../../chat/ChatInput'
import { FloatingChat } from '../../chat/FloatingChat'
import {
  clearActiveProgressByRequest,
  listActiveProgresses,
  resolveTypingAgent,
  upsertActiveProgress,
} from '../../chat/chatProgressState'
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
} from '../../chat/chatApi'
import {
  normalizeAgentProgressEvent,
  normalizeAgentProgressMessage,
  normalizeChatMessage,
  normalizeStatusEvent,
} from '../../chat/chatMappers'
import { useChatMessageQueue } from '../../chat/useChatMessageQueue'
import { Report } from '../../reports/Report'
import { ItemEntryChoice } from '../../reports/ItemEntryChoice'
import { ItemInputForm } from '../../reports/ItemInputForm'
import { buildOperationFeedbackPayload } from '../../reports/operationFeedbackLogic'
import { buildFeatureSavedReport } from '../../reports/savedReportPayload'
import { buildCurrentResult, buildFeatureSeed, buildWorkspacePatch } from '../featureChatContext'
import { applicationFormForContext } from '../../reports/applicationFormSchemas'
import { buildFeaturePageTheme } from './featurePageTheme'
import { ItemGeneratingState } from './ItemGeneratingState'
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

const reportDataFromMessage = (message, featureId) => {
  const result = message?.metadata?.result
  if (result?.shouldCreateResult !== true) return null
  const payload = result?.payload
  if (!payload?.reportData) return null
  if (payload.featureId && payload.featureId !== featureId) return null
  return payload.reportData
}

export const FeaturePage = ({
  id,
  go,
  user,
  startupProfile,
  workspaceContext,
  onWorkspaceContextChange,
  workspace,
  setWorkspace,
  onCreateWorkspace,
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
  // 지원사업 결과 화면 뷰 모드: 'all'(전체 추천) | 'saved'(저장한 결과만). 이 페이지에서만 유지된다.
  const [supportViewMode, setSupportViewMode] = useState('all')
  const [focusedSectionTitle, setFocusedSectionTitle] = useState(featureSeed.focusedSectionTitle)
  const [planGoal, setPlanGoal] = useState(featureSeed.planGoal)
  // 사업계획서 기능에서 사용자가 붙여넣는 공고문(있으면 그 내용에 맞춰 초안을 재생성한다).
  // 경북 사회적경제 창업학교 공고로 진입하면 고정 공고문이 기본값으로 들어온다.
  const [announcement, setAnnouncement] = useState(featureSeed.announcement ?? '')
  const {
    messages,
    pushImmediate,
    enqueue,
    flush,
    reset: resetMessages,
    isDraining,
  } = useChatMessageQueue([])
  const [room, setRoom] = useState(null)
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [creatingRoom, setCreatingRoom] = useState(false)
  const [connection, setConnection] = useState('idle')
  const [statusMap, setStatusMap] = useState({})
  const [activeProgressMap, setActiveProgressMap] = useState(new Map())
  const [error, setError] = useState('')
  const [savingReport, setSavingReport] = useState(false)
  const [aiReportStatus, setAiReportStatus] = useState('idle')
  const [streamVersion, setStreamVersion] = useState(0)
  const [savedReports, setSavedReports] = useState([])
  const [savedMenuOpen, setSavedMenuOpen] = useState(false)
  // 아이템 기능 진입 흐름: 선택 화면(choice) → AI 추천(recommend) 또는 직접 입력(input).
  // 다른 기능에서는 쓰이지 않는다. 저장된 리포트가 있으면(아래 loadLatestReport) recommend로 바로 진입한다.
  const [itemFlowStep, setItemFlowStep] = useState('choice')

  const reconnectTimeoutRef = useRef(null)
  const hiddenRequestIdsRef = useRef(new Set())
  const autoGenerationKeysRef = useRef(new Set())
  const savedMenuRef = useRef(null)

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

  // 우측 상단 '저장한 결과' 드롭다운: 이 기능으로 저장된 결과를 모아 불러본다(시뮬레이션과 동일 로직).
  const refreshSavedReports = useCallback(async () => {
    try {
      const response = await savedResultApi.list()
      const items = (response?.results ?? []).filter(
        (item) => String(item.sourceFeature ?? '').toLowerCase() === id,
      )
      setSavedReports(items)
    } catch {
      /* 저장 목록 조회 실패는 무시 */
    }
  }, [id])

  const loadSavedReport = async (savedResultId) => {
    setSavedMenuOpen(false)
    try {
      const detail = await savedResultApi.get(savedResultId)
      const reportData = detail?.payload?.reportData
      if (reportData) {
        applyReportData(reportData)
        setAiReportStatus('ready')
      }
    } catch (nextError) {
      setError(nextError.message ?? '저장한 결과를 불러오지 못했습니다.')
    }
  }

  useEffect(() => {
    const close = (event) => {
      if (savedMenuRef.current && !savedMenuRef.current.contains(event.target)) {
        setSavedMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
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
          // 아이템 페이지(드롭다운 '아이템 추가하기')는 항상 추천/직접입력 선택 화면부터 보여준다.
          // (회원가입 직후 아이템 선택은 별도 모달에서 처리하므로 여기서 자동 점프하지 않는다.)
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
    refreshSavedReports()

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
          setRoom(nextRooms[0])
          return
        }

        const fallbackRoom = await getFeatureChatRoom(targetFeature)
        if (!active) {
          return
        }
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
          resetMessages([])
          setStatusMap({})
          setActiveProgressMap(new Map())
          setConnection('connecting')
        }

        const history = await getChatMessages(room.roomId)
        if (!active) {
          return
        }
        const nextMessages = history.messages.map(normalizeChatMessage)
        resetMessages(nextMessages)
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
        // 리포트 패널 갱신은 도착 즉시(채팅 말풍선 순서만 큐가 통제).
        applyReportData(nextReport)
        setAiReportStatus('ready')
      }
      // 내 메시지는 즉시, 에이전트 답변은 큐를 거쳐 토론 뒤에 표시.
      if (nextMessage.role === 'user') {
        pushImmediate(nextMessage)
      } else {
        enqueue(nextMessage)
      }
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
        enqueue(normalizeAgentProgressMessage(nextProgress))
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
  const savedMenuItems = id === 'support' ? savedSupportPrograms : savedReports
  const visibleAgentStatus = runningAgentKey && agents[runningAgentKey]
    ? '현재 답변을 준비하고 있어요.'
    : visibleAgents.length
      ? '이번 답변에 참여 중인 전문가들이에요.'
      : helperText
  const chatAccent = runningAgentKey && agents[runningAgentKey] ? agents[runningAgentKey].color : agent.color
  const typingAgent = (typing || isDraining) ? (typing || feature.agent) : null

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
      announcement,
      workspaceContext,
      startupProfile,
    }),
    [
      announcement,
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
  // plan 기능에서 연결된 공고가 신청서 양식을 가지면, 리포트 UI가 그 신청서 폼으로 바뀐다.
  const applicationForm = id === 'plan'
    ? applicationFormForContext({ program: workspaceContext?.selectedSupportProgram, announcement })
    : null
  // 신청 항목(창업여부·창업 아이템·지원동기)의 프로필 기반 기본값. LLM이 꺼져 있어도 비지 않게 채운다.
  // (LLM이 켜져 있으면 AI 생성 답변이 이 값을 덮어쓴다.)
  const planFormDefaults = useMemo(() => {
    if (!applicationForm) return null
    // 현재 워크스페이스(=선택한 아이템)를 최우선으로 반영한다. featureWorkspace는 비어 있을 수 있다.
    const idea = workspace?.selectedIdea ?? workspaceContext?.selectedIdea ?? null
    const ideaTitle = idea?.title || workspace?.name || startupProfile?.currentItemName || '준비 중인 창업 아이템'
    const isExisting = Boolean(startupProfile?.currentItemName && startupProfile.currentItemName.trim())
    return {
      startupStatus: isExisting ? '기 창업자' : '예비창업자',
      // 창업 아이템 칸에는 워크스페이스 제목만 넣는다.
      item: ideaTitle,
      motivation:
        `${ideaTitle} 창업을 준비하며 사회적경제에 대한 기초·실무 역량과 사업화 자금이 필요합니다. `
        + '경북형 사회적경제 창업학교의 실무 교육(20시간), 우수팀 사업화 자금(최대 5천만원), '
        + '사회적경제기업 전환 컨설팅과 네트워킹을 통해 아이템을 체계적으로 다듬고, '
        + '지역 기반의 사회적 가치를 지속가능하게 실현하고자 지원합니다.',
    }
  }, [applicationForm, workspace, workspaceContext, startupProfile])

  const sendFeatureMessage = async (text, { hidden = false, currentResultOverride = null } = {}) => {
    if (!room?.roomId) {
      return null
    }
    if (!hidden) {
      setBusy(true)
    }
    setError('')
    // 이전 턴이 아직 드립 중이면 즉시 비워 현재로 스냅하고 새 턴 시작.
    flush()

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
        // 칩/공고처럼 방금 바뀐 입력으로 즉시 재생성할 때는 최신 값으로 만든 결과를 직접 넘긴다
        // (memo된 currentResult는 setState 직후 한 렌더 동안 이전 값이라 stale).
        currentResult: currentResultOverride ?? currentResult,
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
    // 아이템은 사용자가 '추천 받기'를 고른 뒤(recommend)에만 자동 생성한다.
    if (aiReportStatus !== 'empty' || !room?.roomId || id === 'operation'
        || (id === 'item' && itemFlowStep !== 'recommend')) {
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
  }, [aiReportStatus, id, room?.roomId, targetFeature, itemFlowStep])

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
      await refreshSavedReports()
      setSavedMenuOpen(true) // 저장한 결과를 우측 상단 드롭다운에서 바로 확인.
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
      setRoom(createdRoom)
    } catch (nextError) {
      setError(nextError.message ?? '새 기능 채팅 세션을 만들지 못했습니다.')
    } finally {
      setCreatingRoom(false)
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
      setSupportHasSearched(true)
    } catch (nextError) {
      setError(nextError.message ?? '지원사업 추천 결과를 불러오지 못했습니다.')
    } finally {
      setSupportSearchLoading(false)
    }
  }

  // 추천 결과에서 개별 지원사업을 '저장한 추천 목록'에 담는다(검색 시 자동 저장하지 않음).
  const handleSaveSupportProgram = (program) => {
    if (!program) return
    const filters = {
      recommendationBasis: supportSearchMode,
      priority: supportUserGoal,
      regionBasis: supportRegionBasis,
    }
    const nextSavedPrograms = mergeSupportProgramHistory(readSupportProgramHistory(), [program], filters)
    writeSupportProgramHistory(nextSavedPrograms)
    setSavedSupportPrograms(nextSavedPrograms)
    setSavedMenuOpen(true)
  }

  // 저장한 추천 목록에서 개별 지원사업을 제거한다('저장한 결과' 뷰의 × 버튼).
  const handleDeleteSupportProgram = (program) => {
    if (!program) return
    const targetId = program.id ?? program.title
    const nextSavedPrograms = removeSupportProgramHistoryItem(readSupportProgramHistory(), targetId)
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

  // 지원사업 카드의 '이 공고로 사업계획서 작성': 선택 공고를 부모 워크스페이스에 즉시 커밋한 뒤 plan으로 이동.
  // (support 페이지는 곧 언마운트돼 effect 기반 패치가 실행되지 않으므로, 부모 상태를 직접 갱신해야 plan이 그 공고를 받는다.)
  const handleWritePlanFromProgram = (program) => {
    const patch = {}
    if (program) patch.selectedSupportProgram = program
    // 현재 워크스페이스의 아이템을 함께 넘겨 plan이 그 아이템 기준으로 작성하게 한다.
    if (workspace?.selectedIdea) patch.selectedIdea = workspace.selectedIdea
    if (Object.keys(patch).length) {
      onWorkspaceContextChange?.(patch)
    }
    go('plan')
  }

  // 사업계획서: 붙여넣은 공고문에 맞춰 초안을 재생성한다.
  // setState 직후의 stale memo를 피하려고, 입력값으로 만든 currentResult를 직접 넘긴다.
  const handleSubmitAnnouncement = (text) => {
    if (!room?.roomId || aiReportStatus === 'loading') {
      return
    }
    const trimmed = (text ?? '').trim()
    setAnnouncement(trimmed)
    const override = buildCurrentResult({
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
      announcement: trimmed,
      workspaceContext,
      startupProfile,
    })
    setAiReportStatus('loading')
    sendFeatureMessage(GENERATE_REPORT_PROMPT, { hidden: true, currentResultOverride: override })
      .catch(() => setAiReportStatus('error'))
  }

  // SNS 홍보 자동화: 톤/목적 칩을 바꾸면 그 값을 에이전트에 넘겨 멘트를 다시 생성한다.
  const handleCampaignControlChange = (patch) => {
    if (!room?.roomId || aiReportStatus === 'loading') {
      return
    }
    const nextData = { ...data, ...patch }
    setData(nextData)
    setAiReportStatus('loading')
    // setData는 비동기라 memo된 currentResult가 아직 이전 값이므로, 새 data로 직접 결과를 만들어 넘긴다.
    const overrideResult = buildCurrentResult({
      featureId: id,
      data: nextData,
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
    })
    sendFeatureMessage(GENERATE_REPORT_PROMPT, { hidden: true, currentResultOverride: overrideResult })
      .catch(() => setAiReportStatus('error'))
  }

  // 직접 입력한 아이템으로 새 워크스페이스를 생성한다(워크스페이스 = 아이템).
  const handleItemInputSubmit = (item) => {
    onCreateWorkspace?.(item)
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
            {id === 'sns' ? null : (
              <>
                {id === 'plan' && (
                <div className="plan-header-meta">
                <div>
                  <small>보조할 사업</small>
                  <b>{data?.target || '선택한 사업'}</b>
                </div>
                <div>
                  <small>작성 전략</small>
                  <b>
                    {{
                      ALIGN_SUPPORT: '공고 요건에 맞춰 보완',
                      STRENGTHEN_SECTION: '핵심 문단 강화',
                      REWRITE_TONE: '문체 다듬기',
                      CHECK_GAPS: '빠진 항목 점검',
                    }[planGoal] || '공고 요건에 맞춰 보완'}
                  </b>
                </div>
              </div>
                )}
                <div className="sim-saved-menu" ref={savedMenuRef}>
                  <button
                    type="button"
                    className="sim-saved-trigger"
                    aria-expanded={savedMenuOpen}
                    onClick={() => setSavedMenuOpen((open) => !open)}
                  >
                    <Icon name="bookmark" size={15} />
                    저장한 결과{savedMenuItems.length ? ` ${savedMenuItems.length}` : ''}
                    <Icon name="chevron" size={14} />
                  </button>
                  {savedMenuOpen && (
                    <div className="sim-saved-dropdown">
                      {savedMenuItems.length === 0 ? (
                        <p className="sim-saved-empty">저장한 결과가 아직 없어요.</p>
                      ) : (
                        savedMenuItems.map((item) => (
                          <button
                            key={item.id ?? item.title}
                            type="button"
                            className="sim-saved-item"
                            onClick={() => {
                              if (id === 'support') {
                                setSelectedSupportTitle(item.title)
                                setSupportViewMode('saved')
                                setSavedMenuOpen(false)
                                return
                              }
                              loadSavedReport(item.id)
                            }}
                          >
                            <b>{item.title}</b>
                            {(item.createdAt || item.savedAt || item.summary || item.region) && (
                              <small>
                                {item.createdAt || item.savedAt ? (item.createdAt ?? item.savedAt).slice(0, 10) : ''}
                                {item.region ? ` · ${item.region}` : ''}
                                {item.summary ? ` · ${item.summary}` : ''}
                              </small>
                            )}
                          </button>
                        ))
                      )}
                    </div>
                  )}
                </div>
                {/* 운영 피드백은 폼 내부 저장 버튼을 쓰고, 아이템은 추천 화면일 때만 생성/저장 버튼을 보여준다. */}
                {id !== 'support' && id !== 'operation' && !(id === 'item' && itemFlowStep !== 'recommend') && (
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
              </>
            )}
          </div>
        </div>
        {id === 'item' && itemFlowStep === 'choice' ? (
          <ItemEntryChoice
            stage={startupProfile?.stage}
            onChooseRecommend={() => setItemFlowStep('recommend')}
            onChooseInput={() => setItemFlowStep('input')}
          />
        ) : id === 'item' && itemFlowStep === 'input' ? (
          <ItemInputForm
            prefill={{
              itemName: startupProfile?.currentItemName ?? '',
              industry: startupProfile?.currentIndustry ?? '',
              region: startupProfile?.businessRegion ?? '',
            }}
            onSubmit={handleItemInputSubmit}
            onBack={() => setItemFlowStep('choice')}
          />
        ) : aiReportStatus === 'ready' ? (
          <Report
            id={id}
            data={data}
            setData={setData}
            go={go}
            workspace={workspace}
            setWorkspace={setWorkspace}
            onCreateWorkspace={onCreateWorkspace}
            selectedIdeaRank={selectedIdeaRank}
            onSelectIdea={setSelectedIdeaRank}
            selectedSupportTitle={selectedSupportTitle}
            onSelectSupport={setSelectedSupportTitle}
            onWritePlanFromProgram={handleWritePlanFromProgram}
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
            onSaveSupportProgram={handleSaveSupportProgram}
            onDeleteSupportProgram={handleDeleteSupportProgram}
            savedSupportPrograms={savedSupportPrograms}
            supportViewMode={supportViewMode}
            onChangeSupportViewMode={setSupportViewMode}
            focusedSectionTitle={focusedSectionTitle}
            onFocusSection={setFocusedSectionTitle}
            planGoal={planGoal}
            onChangePlanGoal={setPlanGoal}
            announcement={announcement}
            onSubmitAnnouncement={handleSubmitAnnouncement}
            announcementLoading={aiReportStatus === 'loading'}
            onRequestOperationFeedback={handleOperationFeedbackRequest}
            operationFeedbackSaving={savingReport}
            onCampaignControlChange={handleCampaignControlChange}
            applicationForm={applicationForm}
            formDefaults={planFormDefaults}
          />
        ) : id === 'item' && aiReportStatus === 'loading' ? (
          <ItemGeneratingState agentId={feature.agent} />
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

      <FloatingChat
        accent={chatAccent}
        active={Boolean(typing || isDraining)}
        launcherLabel={`${agent.name}에게 이 리포트에 대해 물어보기`}
        headerSlot={(
          <div className="chat-dock-agent" style={{ color: chatAccent }}>
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
            <div className="chat-dock-agent-copy">
              <b>
                {visibleAgents.length
                  ? visibleAgents.map((visibleAgent) => visibleAgent.name).join(' · ')
                  : 'AI 전문가 채팅'}
              </b>
              <small>{visibleAgentStatus}</small>
            </div>
          </div>
        )}
        onNewChat={createSession}
        newChatLabel={creatingRoom ? '만드는 중' : '새 채팅'}
        newChatDisabled={creatingRoom || busy}
        loading={loading}
        emptySlot={(
          <div className="feature-chat-empty">
            <AgentAvatar id={feature.agent} size={52} active />
            <strong>{agent.name}가 리포트를 보고 있어요.</strong>
            <p>지금 보고 있는 결과를 기준으로 방향 수정, 비교, 다음 단계 질문을 이어갈 수 있어요.</p>
          </div>
        )}
        messages={messages.filter((message) => !message.metadata?.hidden)}
        statusProgresses={statusProgresses}
        typing={typingAgent}
        onOpenReport={go}
        failedStatus={latestStatus}
        error={error}
        input={(
          <ChatInput
            onSend={handleSend}
            disabled={busy || loading || connection === 'error' || !room?.roomId}
            placeholder="이 리포트를 바탕으로 더 물어보세요."
            accent={chatAccent}
            suggestions={FEATURE_SUGGESTIONS[id] ?? []}
          />
        )}
      />
    </main>
  )
}
