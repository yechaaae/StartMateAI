const stepFields = [
  ['preferredBusinessType', 'teamStatus'],
  ['major', 'interestField', 'residenceRegion', 'businessRegion', 'initialBudget'],
  ['career', 'strengthTags'],
]

const hasValue = (value) => {
  if (value === 0) {
    return true
  }

  return String(value ?? '').trim().length > 0
}

export const isOnboardingStepComplete = (stepIndex, form) => (
  stepFields[stepIndex]?.every((field) => hasValue(form[field])) ?? false
)

export const getFirstIncompleteOnboardingField = (stepIndex, form) => (
  stepFields[stepIndex]?.find((field) => !hasValue(form[field])) ?? null
)

export const getVisibleOnboardingFields = (stepIndex, form) => {
  if (stepIndex !== 0) {
    return stepFields[stepIndex] ?? []
  }

  if (!hasValue(form.preferredBusinessType)) {
    return ['preferredBusinessType']
  }

  return stepFields[0]
}

export const getOnboardingProgress = (stepIndex) => {
  const total = stepFields.length
  const current = Math.min(stepIndex + 1, total)

  return {
    current,
    total,
    percent: Math.round((current / total) * 100),
  }
}

export const onboardingStepCount = stepFields.length
