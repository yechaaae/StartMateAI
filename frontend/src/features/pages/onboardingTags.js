// 전공/관심 분야 같은 태그 입력값을 쉼표 구분 문자열로 다루는 순수 헬퍼입니다.
export const parseTags = (value) => String(value ?? '')
  .split(',')
  .map((tag) => tag.trim())
  .filter(Boolean)

export const joinTags = (tags) => tags.join(', ')

export const addTag = (value, rawTag, max) => {
  const tag = String(rawTag ?? '').trim()
  if (!tag) {
    return value
  }
  const tags = parseTags(value)
  if (tags.length >= max) {
    return value
  }
  if (tags.some((existing) => existing.toLowerCase() === tag.toLowerCase())) {
    return value
  }
  return joinTags([...tags, tag])
}
