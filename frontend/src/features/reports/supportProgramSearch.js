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

const SIGUNGU_TO_SIDO = [
  ['경북', ['구미', '구미시']],
]

const sorters = {
  HIGH_MATCH: (a, b) => b.score - a.score,
  EASY_PREP: (a, b) => b.score - a.score,
  LARGE_SUPPORT: (a, b) => amountRank(b.amount) - amountRank(a.amount) || b.score - a.score,
  FAST_DEADLINE: (a, b) => deadlineTime(a.deadlineDate) - deadlineTime(b.deadlineDate),
}

export const PINNED_GYEONGBUK_SOCIAL_PROGRAM_TITLE = '2026년 경북형 사회적경제 창업학교 참가자 모집'
const PINNED_GYEONGBUK_SOCIAL_PROGRAM_ID = 'pinned-gyeongbuk-social-economy-school-2026'

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
  const token = value.split(/[\s,/]/).find((item) => /[시구군]$/.test(item))
  if (token) {
    return token
  }
  const found = SIGUNGU_TO_SIDO.flatMap(([, aliases]) => aliases).find((alias) => value.includes(alias))
  return found ? (/[시구군]$/.test(found) ? found : `${found}시`) : null
}

const sidoFromSigungu = (sigungu) => {
  const value = text(sigungu)
  if (!value) {
    return null
  }
  const found = SIGUNGU_TO_SIDO.find(([, aliases]) => aliases.some((alias) => value.includes(alias)))
  return found?.[0] ?? null
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
  const desiredSigungu = sigunguFrom(region)
  return {
    age: amountFrom(filters.startupProfile?.age),
    residenceSido: sidoFrom(filters.startupProfile?.residenceRegion),
    desiredSido: sidoFrom(region) ?? sidoFromSigungu(desiredSigungu),
    desiredSigungu,
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

const isGyeongbukPayload = (payload) => (
  ['경북', '경상북도'].includes(text(payload.desiredSido))
  || ['경북', '경상북도'].includes(text(payload.residenceSido))
  || text(payload.desiredSigungu).includes('구미')
)

const isGyeongbukProgramList = (programs = []) => programs.some((program) => {
  const haystack = [
    program.title,
    program.region,
    program.reason,
    program.summary,
    ...(program.matchReasons ?? []),
  ].map(text).join(' ')
  return /(구미|경북|경상북도|대구ㆍ경북|대구·경북)/.test(haystack)
})

const pinnedGyeongbukSocialProgram = () => ({
  id: PINNED_GYEONGBUK_SOCIAL_PROGRAM_ID,
  programId: null,
  title: PINNED_GYEONGBUK_SOCIAL_PROGRAM_TITLE,
  source: 'kstartup',
  region: '경상북도',
  due: dDayFrom('2026-06-14'),
  dDay: dDayFrom('2026-06-14'),
  score: 91,
  reason: '희망 시도와 지역 조건이 맞습니다.',
  summary: '경상북도 사회적경제지원센터가 운영하는 사회적경제 창업 실무 교육 프로그램입니다.',
  requiredDocs: ['구글폼 신청서', '신청서 양식'],
  docs: ['구글폼 신청서', '신청서 양식'],
  tags: ['education', 'open'],
  amount: '',
  supportType: 'education',
  isYouth: false,
  deadlineDate: '2026-06-14',
  applyUrl: '',
  url: '',
  matchReasons: [
    '희망 시도와 지역 조건이 맞습니다.',
    '예비창업자와 3년 미만 창업자가 신청 대상에 포함됩니다.',
  ],
  cautionReasons: ['신청 마감은 2026-06-14 23:59이므로 실제 공고에서 접수 가능 여부를 확인하세요.'],
})

export const withPinnedGyeongbukSocialProgram = (programs = [], payload = {}) => {
  if (!payload.force && !isGyeongbukPayload(payload) && !isGyeongbukProgramList(programs)) {
    return programs
  }
  const withoutDuplicate = programs.filter((program) => (
    program.id !== PINNED_GYEONGBUK_SOCIAL_PROGRAM_ID
    && program.title !== PINNED_GYEONGBUK_SOCIAL_PROGRAM_TITLE
  ))
  return [pinnedGyeongbukSocialProgram(), ...withoutDuplicate]
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
  const sortedPrograms = (Array.isArray(programs) ? programs : [])
    .map(normalizeProgram)
    .filter(Boolean)
    .sort((a, b) => (Number(b.isYouth) - Number(a.isYouth)) || sorter(a, b))
  return withPinnedGyeongbukSocialProgram(sortedPrograms, payload)
}
