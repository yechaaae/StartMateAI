import { cloneReport } from '../../shared/data/reports.js'
import {
  PINNED_GYEONGBUK_ANNOUNCEMENT,
  PINNED_GYEONGBUK_SOCIAL_PROGRAM_TITLE,
  withPinnedGyeongbukSocialProgram,
} from '../reports/supportProgramSearch.js'

// 경북 사회적경제 창업학교 공고로 plan에 진입했는지 판별한다(고정 공고문 자동 주입용).
const isPinnedGyeongbukProgram = (program) => (
  program?.title === PINNED_GYEONGBUK_SOCIAL_PROGRAM_TITLE
)

const clone = (value) => JSON.parse(JSON.stringify(value))

const findSelectedIdea = (data, selectedIdeaRank) => (
  (data.items ?? []).find((item) => item.rank === selectedIdeaRank) ?? null
)

const findSelectedSupportProgram = (data, selectedSupportTitle) => (
  withPinnedGyeongbukSocialProgram(data.list ?? [], { force: true })
    .find((item) => item.title === selectedSupportTitle) ?? null
)

const buildPlanSections = (data) => (
  (data.sections ?? []).map(([title, body]) => ({ title, body }))
)

const operationSuggestionTitle = (suggestion) => (
  Array.isArray(suggestion) ? suggestion[0] : suggestion?.title
)

const buildOperationSuggestionObjects = (data) => (
  (data.suggestions ?? []).map((suggestion) => (
    Array.isArray(suggestion)
      ? { title: suggestion[0], body: suggestion[1], link: suggestion[2] ?? null }
      : { title: suggestion.title, body: suggestion.body, link: suggestion.link ?? null }
  ))
)

export const buildFeatureSeed = (featureId, workspaceContext = {}) => {
  const data = cloneReport(featureId)

  if (featureId === 'simulator' && workspaceContext.selectedIdea?.title) {
    data.item = workspaceContext.selectedIdea.title
  }

  if (featureId === 'plan' && workspaceContext.selectedSupportProgram?.title) {
    data.target = workspaceContext.selectedSupportProgram.title
  }

  if (featureId === 'sns' && workspaceContext.selectedIdea?.title) {
    data.topic = workspaceContext.selectedIdea.title
  }

  if (featureId === 'sns' && workspaceContext.operationContext?.highlightSuggestion?.title) {
    data.hook = `${workspaceContext.operationContext.highlightSuggestion.title}에 맞춰 다시 구성한 캠페인 초안입니다.`
    data.objective = 'CONVERSION'
  }

  return {
    data,
    selectedIdeaRank: data.items?.[0]?.rank ?? workspaceContext.selectedIdea?.rank ?? null,
    selectedSupportTitle: workspaceContext.selectedSupportProgram?.title ?? data.list?.[0]?.title ?? null,
    selectedOperationSuggestionTitle:
      workspaceContext.operationContext?.selectedSuggestion?.title
      ?? operationSuggestionTitle(data.suggestions?.[0])
      ?? null,
    supportSearchMode: workspaceContext.supportSearchMode ?? 'PROFILE_IDEA',
    supportUserGoal: workspaceContext.supportUserGoal ?? 'HIGH_MATCH',
    supportRegionBasis: workspaceContext.supportRegionBasis ?? 'BUSINESS_REGISTRATION',
    focusedSectionTitle: workspaceContext.focusedSection?.title ?? data.sections?.[0]?.[0] ?? null,
    planGoal: workspaceContext.planGoal ?? 'ALIGN_SUPPORT',
    // 경북 사회적경제 창업학교 공고로 plan에 진입하면 고정 공고문을 기본값으로 채운다.
    announcement: featureId === 'plan' && isPinnedGyeongbukProgram(workspaceContext.selectedSupportProgram)
      ? PINNED_GYEONGBUK_ANNOUNCEMENT
      : '',
  }
}

export const buildWorkspacePatch = ({
  featureId,
  data,
  selectedIdeaRank,
  selectedSupportTitle,
  selectedOperationSuggestionTitle,
  supportSearchMode,
  supportUserGoal,
  supportRegionBasis,
  focusedSectionTitle,
  planGoal,
}) => {
  if (featureId === 'item') {
    return {
      itemReport: clone(data),
      selectedIdea: findSelectedIdea(data, selectedIdeaRank),
    }
  }

  if (featureId === 'simulator') {
    return {
      simulationContext: {
        item: data.item,
        price: data.price,
        capital: data.capital,
        startOrders: data.startOrders,
        growthPct: data.growthPct,
        risks: clone(data.risks ?? []),
      },
    }
  }

  if (featureId === 'support') {
    return {
      supportReport: clone(data),
      supportSearchMode,
      supportUserGoal,
      supportRegionBasis,
      selectedSupportProgram: findSelectedSupportProgram(data, selectedSupportTitle),
    }
  }

  if (featureId === 'plan') {
    const sections = buildPlanSections(data)
    return {
      planGoal,
      planDraft: {
        target: data.target,
        sections,
      },
      focusedSection: sections.find((section) => section.title === focusedSectionTitle) ?? sections[0] ?? null,
    }
  }

  if (featureId === 'operation') {
    const selectedSuggestion = buildOperationSuggestionObjects(data)
      .find((item) => item.title === selectedOperationSuggestionTitle) ?? null

    return {
      operationContext: {
        period: data.period ?? '',
        kpis: clone(data.kpis ?? []),
        products: clone(data.products ?? []),
        channels: clone(data.channels ?? []),
        notes: data.notes ?? '',
        suggestions: clone(data.suggestions ?? []),
        selectedSuggestion,
        highlightSuggestion: selectedSuggestion,
      },
    }
  }

  if (featureId === 'sns') {
    return {
      snsContext: {
        topic: data.topic,
        hook: data.hook,
        beats: clone(data.beats ?? []),
        tags: clone(data.tags ?? []),
        channel: data.channel ?? 'INSTAGRAM_REELS',
        tone: data.tone ?? 'FRIENDLY',
        objective: data.objective ?? 'CONVERSION',
        callToAction: data.callToAction ?? '',
        schedule: data.schedule,
      },
    }
  }

  return {}
}

export const buildCurrentResult = ({
  featureId,
  data,
  selectedIdeaRank,
  selectedSupportTitle,
  selectedOperationSuggestionTitle,
  supportSearchMode,
  supportUserGoal,
  supportRegionBasis,
  focusedSectionTitle,
  planGoal,
  announcement = '',
  workspaceContext = {},
  startupProfile = null,
}) => {
  const selectedIdea = findSelectedIdea(data, selectedIdeaRank)
  const selectedSupportProgram = findSelectedSupportProgram(data, selectedSupportTitle)
  const linkedIdea = workspaceContext.selectedIdea ?? selectedIdea ?? null
  const linkedSupportProgram = workspaceContext.selectedSupportProgram ?? selectedSupportProgram ?? null

  if (featureId === 'item') {
    return {
      startupProfile,
      location: data.location,
      analysis: clone(data.analysis ?? []),
      items: clone(data.items ?? []),
      selectedIdea,
    }
  }

  if (featureId === 'simulator') {
    return {
      startupProfile,
      ideaContext: linkedIdea,
      simulationInput: {
        item: data.item,
        price: data.price,
        capital: data.capital,
        startOrders: data.startOrders,
        growthPct: data.growthPct,
      },
      risks: clone(data.risks ?? []),
    }
  }

  if (featureId === 'support') {
    return {
      startupProfile,
      supportSearchMode,
      userGoal: supportUserGoal,
      regionBasis: supportRegionBasis,
      selectedSupportProgram,
      recommendations: clone(data.list ?? []),
      profileContext: {
        useStartupProfile: supportSearchMode !== 'IDEA_ONLY',
        startupProfile,
      },
      ideaContext: {
        useSelectedIdea: supportSearchMode !== 'PROFILE_ONLY',
        selectedIdea: linkedIdea,
      },
    }
  }

  if (featureId === 'plan') {
    const sections = buildPlanSections(data)
    const focusedSection = sections.find((section) => section.title === focusedSectionTitle) ?? sections[0] ?? null

    const trimmedAnnouncement = (announcement ?? '').trim()
    return {
      startupProfile,
      planGoal,
      planDraft: {
        target: data.target,
        sections,
      },
      focusedSection,
      announcement: trimmedAnnouncement ? { text: trimmedAnnouncement } : null,
      selectedSupportProgram: linkedSupportProgram,
      ideaContext: linkedIdea,
      profileContext: {
        useStartupProfile: true,
        startupProfile,
      },
    }
  }

  if (featureId === 'operation') {
    const selectedSuggestion = buildOperationSuggestionObjects(data)
      .find((item) => item.title === selectedOperationSuggestionTitle) ?? null

    return {
      startupProfile,
      businessContext: {
        selectedIdea: linkedIdea,
        simulationContext: workspaceContext.simulationContext ?? null,
        selectedSupportProgram: linkedSupportProgram,
        planDraft: workspaceContext.planDraft ?? null,
      },
      operationInput: {
        source: 'user_input',
        period: data.period ?? '',
        kpis: clone(data.kpis ?? []),
        products: clone(data.products ?? []),
        channels: clone(data.channels ?? []),
        notes: data.notes ?? '',
      },
      operationReport: {
        source: 'operation-page',
        selectedSuggestion,
        suggestions: clone(data.suggestions ?? []),
      },
      contextPriority: [
        'operationInput',
        'operationReport',
        'businessContext',
        'startupProfile',
      ],
    }
  }

  if (featureId === 'sns') {
    return {
      startupProfile,
      campaignContext: {
        selectedIdea: linkedIdea,
        selectedSupportProgram: linkedSupportProgram,
        operationFocus: workspaceContext.operationContext?.selectedSuggestion
          ?? workspaceContext.operationContext?.highlightSuggestion
          ?? null,
        planDraft: workspaceContext.planDraft ?? null,
      },
      campaignDraft: {
        topic: data.topic,
        hook: data.hook,
        beats: clone(data.beats ?? []),
        tags: clone(data.tags ?? []),
        channel: data.channel ?? 'INSTAGRAM_REELS',
        tone: data.tone ?? 'FRIENDLY',
        objective: data.objective ?? 'CONVERSION',
        callToAction: data.callToAction ?? '',
        schedule: data.schedule,
      },
      contextPriority: [
        'campaignDraft',
        'campaignContext',
        'startupProfile',
      ],
    }
  }

  return {
    startupProfile,
    report: clone(data),
  }
}
