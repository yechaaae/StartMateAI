// 온보딩 단계는 "창업 전 / 창업 후"(stage)에 따라 달라집니다.
// 0단계는 항상 stage 선택이고, 이후 단계는 stage에 맞춰 구성됩니다.
const STAGE_STEP = ['stage']

const PRE_STEPS = [
  ['preferredBusinessType', 'teamStatus'],
  ['major', 'interestField', 'residenceRegion', 'businessRegion', 'initialBudget'],
  ['career', 'strengthTags'],
]

const POST_STEPS = [
  ['currentItemName', 'currentIndustry', 'businessRegion', 'operatingPeriod'],
  ['preferredBusinessType', 'teamStatus'],
  ['major', 'interestField', 'residenceRegion'],
  ['career', 'strengthTags'],
]

export const getOnboardingSteps = (stage) => {
  if (stage === 'POST_STARTUP') {
    return [STAGE_STEP, ...POST_STEPS]
  }
  if (stage === 'PRE_STARTUP') {
    return [STAGE_STEP, ...PRE_STEPS]
  }
  return [STAGE_STEP]
}

export const getOnboardingStepCount = (stage) => getOnboardingSteps(stage).length

const hasValue = (value) => {
  if (value === 0) {
    return true
  }

  return String(value ?? '').trim().length > 0
}

export const isOnboardingStepComplete = (stepIndex, form) => (
  getOnboardingSteps(form?.stage)[stepIndex]?.every((field) => hasValue(form[field])) ?? false
)

export const getFirstIncompleteOnboardingField = (stepIndex, form) => (
  getOnboardingSteps(form?.stage)[stepIndex]?.find((field) => !hasValue(form[field])) ?? null
)

export const getVisibleOnboardingFields = (stepIndex, form) => {
  const fields = getOnboardingSteps(form?.stage)[stepIndex] ?? []

  // 선호 창업 형태를 고르기 전에는 팀 구성을 아직 노출하지 않습니다.
  if (fields.includes('preferredBusinessType') && fields.includes('teamStatus') && !hasValue(form?.preferredBusinessType)) {
    return ['preferredBusinessType']
  }

  return fields
}

export const getOnboardingProgress = (stepIndex, stage) => {
  const total = getOnboardingStepCount(stage)
  const current = Math.min(stepIndex + 1, total)

  return {
    current,
    total,
    percent: Math.round((current / total) * 100),
  }
}
