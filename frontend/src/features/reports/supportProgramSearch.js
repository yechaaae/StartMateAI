import { supportProgramApi } from '../../shared/api/client.js'

const SIDO_ALIASES = [
  ['서울', ['서울', '서울특별시']],
  ['부산', ['부산', '부산광역시']],
  ['대구', ['대구', '대구광역시']],
  ['인천', ['인천', '인천광역시']],
  ['광주', ['광주', '광주광역시']],
  ['대전', ['대전', '대전광역시']],
  ['울산', ['울산', '울산광역시']],
  ['세종', ['세종', '세종특별자치시']],
  ['경기', ['경기', '경기도']],
  ['강원', ['강원', '강원도', '강원특별자치도']],
  ['충북', ['충북', '충청북도']],
  ['충남', ['충남', '충청남도']],
  ['전북', ['전북', '전라북도', '전북특별자치도']],
  ['전남', ['전남', '전라남도']],
  ['경북', ['경북', '경상북도']],
  ['경남', ['경남', '경상남도']],
  ['제주', ['제주', '제주도', '제주특별자치도']],
]

const sorters = {
  HIGH_MATCH: (a, b) => b.score - a.score,
  EASY_PREP: (a, b) => b.score - a.score,
  LARGE_SUPPORT: (a, b) => amountRank(b.amount) - amountRank(a.amount) || b.score - a.score,
  FAST_DEADLINE: (a, b) => deadlineTime(a.deadlineDate) - deadlineTime(b.deadlineDate),
}

const text = (value) => String(value ?? '').trim()

const firstNonBlank = (...values) => values.map(text).find(Boolean) ?? ''

const sidoFrom = (raw) => {
  const value = text(raw)
  if (!value) {
    return null
  }
  const found = SIDO_ALIASES.find(([, aliases]) => aliases.some((alias) => value.includes(alias)))
  return found?.[0] ?? null
}

const sigunguFrom = (raw) => {
  const value = text(raw)
  const token = value.split(/[\s,/]/).find((item) => /[구군]$/.test(item))
  return token ?? null
}

const interestText = (filters) => firstNonBlank(
  filters.selectedIdea?.title,
  filters.selectedIdea?.industry,
  filters.startupProfile?.interestField,
  filters.startupProfile?.preferredBusinessTypeLabel,
)

const industryFields = (raw) => {
  const value = text(raw)
  if (/(카페|커피|디저트|음식|식당|베이커리)/.test(value)) {
    return {
      industryLarge: '음식점업',
      industryMedium: /(카페|커피)/.test(value) ? '커피점/카페' : null,
      industrySmall: /(카페|커피)/.test(value) ? '카페' : null,
    }
  }
  return {
    industryLarge: null,
    industryMedium: null,
    industrySmall: null,
  }
}

const desiredRegion = (filters) => {
  if (filters.regionBasis === 'RESIDENCE') {
    return filters.startupProfile?.residenceRegion
  }
  return firstNonBlank(
    filters.startupProfile?.businessRegion,
    filters.selectedIdea?.region,
    filters.selectedIdea?.location,
    filters.startupProfile?.residenceRegion,
  )
}

const supportTypes = (priority) => {
  if (priority === 'LARGE_SUPPORT') {
    return ['grant', 'loan']
  }
  if (priority === 'EASY_PREP') {
    return ['education', 'mentoring']
  }
  return ['grant', 'education', 'mentoring', 'space']
}

const amountFrom = (value) => {
  const number = Number(value)
  return Number.isFinite(number) && number > 0 ? number : null
}

const amountRank = (value) => {
  const raw = text(value).replace(/,/g, '')
  const number = Number(raw.match(/\d+(?:\.\d+)?/)?.[0] ?? 0)
  if (!number) {
    return 0
  }
  if (raw.includes('억')) {
    return number * 100000000
  }
  if (raw.includes('천') && raw.includes('만원')) {
    return number * 10000000
  }
  if (raw.includes('만원')) {
    return number * 10000
  }
  return number
}

export const buildSupportProgramRecommendationPayload = (filters = {}) => {
  const region = desiredRegion(filters)
  return {
    age: amountFrom(filters.startupProfile?.age),
    residenceSido: sidoFrom(filters.startupProfile?.residenceRegion),
    desiredSido: sidoFrom(region),
    desiredSigungu: sigunguFrom(region),
    founderType: 'pre_founder',
    businessRegistered: false,
    businessStartDate: null,
    businessStage: 'idea',
    ...industryFields(interestText(filters)),
    requiredFundingAmount: amountFrom(filters.startupProfile?.initialBudget),
    interestedSupportTypes: supportTypes(filters.priority),
  }
}

const dDayFrom = (dateString) => {
  if (!dateString) {
    return ''
  }
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const deadline = new Date(dateString)
  if (Number.isNaN(deadline.getTime())) {
    return ''
  }
  const diffDays = Math.ceil((deadline - today) / 86400000)
  return diffDays >= 0 ? `D-${diffDays}` : '마감'
}

const deadlineTime = (dateString) => {
  const time = new Date(dateString).getTime()
  return Number.isNaN(time) ? Number.MAX_SAFE_INTEGER : time
}

const splitDocuments = (raw) => {
  if (Array.isArray(raw)) {
    return raw.map(text).filter(Boolean)
  }
  return text(raw).split(/[,/|]/).map(text).filter(Boolean)
}

const YOUTH_RE = /청년|만\s?39\s?세|39세|만\s?34\s?세|34세|대학생|청소년|young/i

const normalizeProgram = (item) => {
  const title = text(item.title)
  if (!title) {
    return null
  }
  const deadlineDate = item.applicationEndDate ?? null
  const matchReasons = Array.isArray(item.matchReasons) ? item.matchReasons.filter(Boolean) : []
  const cautionReasons = Array.isArray(item.cautionReasons) ? item.cautionReasons.filter(Boolean) : []
  const supportType = text(item.supportType)
  const youthHaystack = [
    title,
    text(item.summary),
    text(item.regionCondition),
    text(item.organization),
    text(item.supportTarget),
    text(item.eligibility),
    ...matchReasons,
  ].join(' ')
  return {
    id: item.programId ? `support-program-${item.programId}` : title,
    programId: item.programId ?? null,
    title,
    source: item.source ?? '',
    region: item.regionCondition ?? '',
    due: dDayFrom(deadlineDate),
    dDay: dDayFrom(deadlineDate),
    score: Number(item.matchScore ?? 0),
    reason: firstNonBlank(matchReasons[0], item.summary),
    summary: item.summary ?? '',
    requiredDocs: splitDocuments(item.requiredDocuments),
    docs: splitDocuments(item.requiredDocuments),
    tags: [item.organization, supportType, item.status].map(text).filter(Boolean),
    amount: item.supportAmount ?? '',
    supportType,
    isYouth: YOUTH_RE.test(youthHaystack),
    deadlineDate,
    applyUrl: item.applyUrl ?? '',
    url: item.applyUrl ?? '',
    matchReasons,
    cautionReasons,
  }
}

export const runSupportProgramSearch = async (filters = {}) => {
  const payload = buildSupportProgramRecommendationPayload(filters)
  const programs = await supportProgramApi.recommend(payload)
  const sorter = sorters[filters.priority] ?? sorters.HIGH_MATCH
  // 청년 관련 사업을 최상위로 올리고, 그 안에서는 선택한 우선순위로 정렬한다.
  return (Array.isArray(programs) ? programs : [])
    .map(normalizeProgram)
    .filter(Boolean)
    .sort((a, b) => (Number(b.isYouth) - Number(a.isYouth)) || sorter(a, b))
}
