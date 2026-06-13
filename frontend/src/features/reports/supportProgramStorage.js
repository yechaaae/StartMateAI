// v2: 개별 저장 구조로 전환하면서 키를 올려 기존에 누적된 저장분을 비운다(처음엔 아무것도 저장되지 않은 상태).
export const SUPPORT_PROGRAM_STORAGE_KEY = 'startmate.supportProgramRecommendations.v2'

const toStableId = (program) => program.id ?? program.title

export const buildSupportProgramStorageEntry = (program, filters, savedAt = new Date().toISOString()) => ({
  ...program,
  id: toStableId(program),
  savedAt,
  filters: { ...filters },
})

export const mergeSupportProgramHistory = (
  existingPrograms,
  recommendedPrograms,
  filters,
  savedAt = new Date().toISOString(),
) => {
  const mergedById = new Map((existingPrograms ?? []).map((program) => [toStableId(program), program]))

  ;(recommendedPrograms ?? []).forEach((program) => {
    const entry = buildSupportProgramStorageEntry(program, filters, savedAt)
    mergedById.set(entry.id, entry)
  })

  return [...mergedById.values()]
}

export const removeSupportProgramHistoryItem = (programs, targetId) => (
  (programs ?? []).filter((program) => toStableId(program) !== targetId)
)

export const readSupportProgramHistory = (storage = globalThis.localStorage) => {
  if (!storage) {
    return []
  }

  try {
    const rawValue = storage.getItem(SUPPORT_PROGRAM_STORAGE_KEY)
    if (!rawValue) {
      return []
    }

    const parsedValue = JSON.parse(rawValue)
    return Array.isArray(parsedValue) ? parsedValue : []
  } catch {
    return []
  }
}

export const writeSupportProgramHistory = (programs, storage = globalThis.localStorage) => {
  if (!storage) {
    return []
  }

  const normalizedPrograms = Array.isArray(programs) ? programs : []
  storage.setItem(SUPPORT_PROGRAM_STORAGE_KEY, JSON.stringify(normalizedPrograms))
  return normalizedPrograms
}
