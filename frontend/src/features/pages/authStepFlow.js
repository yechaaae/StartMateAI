const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export const isAuthStepValueReady = (stepName, value) => {
  const trimmed = value.trim()

  if (stepName === 'email') {
    return emailPattern.test(trimmed)
  }

  if (stepName === 'nickname') {
    return trimmed.length >= 2
  }

  if (stepName === 'password' || stepName === 'passwordConfirm') {
    return value.length >= 8
  }

  return trimmed.length > 0
}

export const getVisibleAuthFieldNames = (steps, revealedCount = 1) => (
  steps.slice(0, Math.max(1, Math.min(revealedCount, steps.length))).map((step) => step.name)
)

export const canRevealNextAuthField = (steps, revealedCount, form) => {
  if (revealedCount >= steps.length) {
    return false
  }

  const currentField = steps[revealedCount - 1]
  return isAuthStepValueReady(currentField.name, form[currentField.name] ?? '')
}

export const getNextAuthRevealCount = (steps, revealedCount, form) => {
  if (!canRevealNextAuthField(steps, revealedCount, form)) {
    return revealedCount
  }

  let nextCount = Math.min(revealedCount + 1, steps.length)

  while (nextCount < steps.length && steps[nextCount].revealWithPrevious) {
    nextCount += 1
  }

  return nextCount
}
