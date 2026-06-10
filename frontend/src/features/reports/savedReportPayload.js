const formatNumber = (value) => {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return null
  }
  return new Intl.NumberFormat('ko-KR').format(value)
}

const trimSummary = (value) => {
  if (!value) return ''
  return value.length > 180 ? `${value.slice(0, 177)}...` : value
}

export const FEATURE_RESULT_TYPES = {
  item: 'IDEA_REPORT',
  simulator: 'SIMULATION_REPORT',
  support: 'SUPPORT_REPORT',
  plan: 'PLAN_REPORT',
  operation: 'OPERATION_REPORT',
  sns: 'SNS_REPORT',
}

export const buildFeatureSavedReport = ({
  featureId,
  data,
  currentResult,
  selectedIdeaRank,
  selectedSupportTitle,
  selectedOperationSuggestionTitle,
  supportSearchMode,
  supportUserGoal,
  focusedSectionTitle,
  planGoal,
}) => {
  const selectedIdea = (data.items ?? []).find((item) => item.rank === selectedIdeaRank) ?? data.items?.[0] ?? null
  const selectedSupport = (data.list ?? []).find((item) => item.title === selectedSupportTitle) ?? data.list?.[0] ?? null
  const selectedSuggestion = (data.suggestions ?? []).find((item) => item[0] === selectedOperationSuggestionTitle) ?? data.suggestions?.[0] ?? null
  const focusedSection = (data.sections ?? []).find((section) => section[0] === focusedSectionTitle) ?? data.sections?.[0] ?? null

  let title = '저장한 리포트'
  let summary = '리포트 스냅샷입니다.'

  if (featureId === 'item') {
    title = selectedIdea ? `${selectedIdea.title} 추천 리포트` : '창업 아이템 추천 리포트'
    summary = `${data.location} 기준 추천 아이템과 상권 분석 결과를 저장했습니다.`
  } else if (featureId === 'support') {
    title = selectedSupport ? `${selectedSupport.title} 지원사업 리포트` : '지원사업 추천 리포트'
    summary = selectedSupport
      ? `${selectedSupport.region} · 매칭 점수 ${selectedSupport.score}점 기준으로 저장했습니다.`
      : '지원사업 추천 결과를 저장했습니다.'
  } else if (featureId === 'plan') {
    title = data.target ? `${data.target} 사업계획서 초안` : '사업계획서 초안'
    summary = focusedSection
      ? `${focusedSection[0]} 문단을 중심으로 정리한 초안입니다.`
      : '사업계획서 초안을 저장했습니다.'
  } else if (featureId === 'operation') {
    title = data.period ? `${data.period} 운영 피드백 리포트` : '운영 피드백 리포트'
    summary = selectedSuggestion
      ? `${selectedSuggestion[0]} 제안을 포함한 운영 피드백입니다.`
      : '운영 피드백 결과를 저장했습니다.'
  } else if (featureId === 'sns') {
    title = data.topic ? `${data.topic} SNS 초안` : 'SNS 홍보 초안'
    summary = `${data.channel ?? 'SNS'} 채널용 캠페인 초안을 저장했습니다.`
  }

  return {
    sourceFeature: featureId,
    resultType: FEATURE_RESULT_TYPES[featureId] ?? 'FEATURE_REPORT',
    referenceId: null,
    title,
    summary: trimSummary(summary),
    payload: {
      featureId,
      reportData: data,
      currentResult,
      viewState: {
        selectedIdeaRank,
        selectedSupportTitle,
        selectedOperationSuggestionTitle,
        supportSearchMode,
        supportUserGoal,
        focusedSectionTitle,
        planGoal,
      },
    },
  }
}

export const buildSimulationSavedReport = ({
  workspace,
  location,
  assumption,
  report,
}) => {
  const ideaTitle = workspace?.selectedIdea?.title ?? report?.ideaTitle ?? '창업 시뮬레이션'
  const totalProfit = report?.summary?.totalProfit
  const formattedProfit = formatNumber(totalProfit)

  return {
    sourceFeature: 'simulator',
    resultType: FEATURE_RESULT_TYPES.simulator,
    referenceId: null,
    title: `${ideaTitle} 시뮬레이션 리포트`,
    summary: trimSummary(
      formattedProfit
        ? `${location?.label ?? location?.address ?? '선택 위치'} 기준 예상 순이익 ${formattedProfit}원 시뮬레이션입니다.`
        : '창업 시뮬레이션 결과를 저장했습니다.',
    ),
    payload: {
      featureId: 'simulator',
      reportData: {
        workspaceIdea: workspace?.selectedIdea ?? null,
        location,
        assumption,
        report,
      },
    },
  }
}
