import { getFeatureChatRoom, sendChatMessage } from '../../chat/chatApi'

// FeaturePage가 리포트 자동 생성에 쓰는 것과 동일한 hidden 프롬프트.
const GENERATE_REPORT_PROMPT = '현재 기능 페이지에 표시할 최종 리포트를 각 Agent가 함께 검토해서 생성해줘.'

const RESULT_TYPES = {
  ITEM: 'IDEA_REPORT',
  SIMULATOR: 'SIMULATION_REPORT',
  SUPPORT: 'SUPPORT_REPORT',
  PLAN: 'PLAN_REPORT',
  OPERATION: 'OPERATION_REPORT',
  SNS: 'SNS_REPORT',
}

// 워크스페이스 진입 전에 기능 리포트를 백그라운드로 미리 생성한다.
// 백엔드가 shouldCreateResult 응답 시 SavedResult를 자동 저장하므로(ChatAiResponseCommandService),
// 트리거만 해두면 이후 해당 기능 탭 진입 시 loadLatestReport가 바로 불러온다.
// fire-and-forget: 실패해도 무시(탭 진입 시 지연 생성 폴백이 동작).
export const pregenerateFeatureReport = async (
  targetFeature,
  { userId = null, featureId, currentResult = {} } = {},
) => {
  try {
    const room = await getFeatureChatRoom(targetFeature)
    if (!room?.roomId) {
      return
    }
    await sendChatMessage(room.roomId, {
      userId,
      content: GENERATE_REPORT_PROMPT,
      metadata: JSON.stringify({
        source: 'workspace-pregen',
        featureId: featureId ?? targetFeature.toLowerCase(),
        hidden: true,
        reportGeneration: true,
      }),
      intent: 'auto',
      sessionType: 'FEATURE_CHAT',
      currentResultType: RESULT_TYPES[targetFeature] ?? 'FEATURE_REPORT',
      currentResultId: null,
      selectedIdeaId:
        currentResult?.campaignContext?.selectedIdea?.rank
        ?? currentResult?.selectedIdea?.rank
        ?? null,
      candidateAgents: [],
      currentResult,
    })
  } catch {
    /* 사전 생성 실패는 무시 — 탭 진입 시 지연 생성으로 폴백 */
  }
}
