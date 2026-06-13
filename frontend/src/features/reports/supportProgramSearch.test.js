import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import {
  buildSupportProgramRecommendationPayload,
  PINNED_GYEONGBUK_SOCIAL_PROGRAM_TITLE,
  runSupportProgramSearch,
} from './supportProgramSearch.js'

afterEach(() => {
  delete globalThis.fetch
})

test('buildSupportProgramRecommendationPayload uses profile and idea context', () => {
  const payload = buildSupportProgramRecommendationPayload({
    priority: 'LARGE_SUPPORT',
    startupProfile: {
      age: 28,
      residenceRegion: '서울 마포구',
      businessRegion: '부산 해운대구',
      interestField: '카페',
      initialBudget: 3000000,
    },
    selectedIdea: {
      title: '로컬 카페 브랜드',
    },
  })

  assert.equal(payload.age, 28)
  assert.equal(payload.residenceSido, '서울')
  assert.equal(payload.desiredSido, '부산')
  assert.equal(payload.desiredSigungu, '해운대구')
  assert.equal(payload.industryLarge, '음식점업')
  assert.equal(payload.industryMedium, '커피점/카페')
  assert.equal(payload.industrySmall, '카페')
  assert.equal(payload.requiredFundingAmount, 3000000)
  assert.deepEqual(payload.interestedSupportTypes, ['grant', 'loan'])
})

test('buildSupportProgramRecommendationPayload infers Gumi as Gyeongbuk region', () => {
  const payload = buildSupportProgramRecommendationPayload({
    startupProfile: {
      businessRegion: '구미시',
      interestField: '카페',
    },
  })

  assert.equal(payload.desiredSido, '경북')
  assert.equal(payload.desiredSigungu, '구미시')
})

test('runSupportProgramSearch calls backend and maps real response fields', async () => {
  let requestBody = null
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/support-programs/recommend')
    requestBody = JSON.parse(options.body)
    return {
      ok: true,
      status: 200,
      json: async () => [
        {
          programId: 2,
          title: '지역 창업 멘토링',
          source: 'bizinfo',
          summary: '멘토링 중심 지원',
          regionCondition: '부산',
          supportAmount: '',
          requiredDocuments: '',
          organization: '부산광역시',
          supportType: 'mentoring',
          status: 'open',
          matchScore: 72,
          matchReasons: ['희망 지역과 지역 조건이 맞습니다.'],
          cautionReasons: [],
          applicationEndDate: '2026-07-10',
          applyUrl: 'https://example.com/mentoring',
        },
        {
          programId: 1,
          title: '청년 사업화 지원',
          source: 'kstartup',
          summary: '사업화 자금 지원',
          regionCondition: '전국',
          supportAmount: '최대 5천만원',
          requiredDocuments: '사업계획서,개인정보동의서',
          organization: '창업진흥원',
          supportType: 'grant',
          status: 'open',
          matchScore: 91,
          matchReasons: ['창업 단계 조건에 맞을 가능성이 높습니다.'],
          cautionReasons: ['연령 조건은 원문 확인이 필요합니다.'],
          applicationEndDate: '2026-06-30',
          applyUrl: 'https://example.com/apply',
        },
      ],
    }
  }

  const results = await runSupportProgramSearch({
    priority: 'HIGH_MATCH',
    startupProfile: {
      businessRegion: '부산 해운대구',
      interestField: '카페',
    },
  })

  assert.equal(requestBody.desiredSido, '부산')
  assert.equal(results[0].title, '청년 사업화 지원')
  assert.equal(results[0].amount, '최대 5천만원')
  assert.deepEqual(results[0].requiredDocs, ['사업계획서', '개인정보동의서'])
  assert.equal(results[0].applyUrl, 'https://example.com/apply')
  assert.deepEqual(results[0].tags, ['창업진흥원', 'grant', 'open'])
})

test('runSupportProgramSearch pins Gyeongbuk social economy school for Gumi profile', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => [
      {
        programId: 20,
        title: '[대구ㆍ경북] 창업기업 맞춤형 멘토링 지원 공고',
        source: 'bizinfo',
        summary: '경북 지역 창업기업 멘토링 지원',
        regionCondition: '대구ㆍ경북',
        supportType: 'mentoring',
        status: 'open',
        matchScore: 84,
        matchReasons: ['경북 광역권 조건에 맞습니다.'],
        cautionReasons: [],
        applicationEndDate: '2026-06-30',
      },
    ],
  })

  const results = await runSupportProgramSearch({
    priority: 'HIGH_MATCH',
    startupProfile: {
      businessRegion: '경북 구미시',
      interestField: '카페',
    },
  })

  assert.equal(results[0].title, PINNED_GYEONGBUK_SOCIAL_PROGRAM_TITLE)
  assert.equal(results[0].supportType, 'education')
  assert.equal(results[1].title, '[대구ㆍ경북] 창업기업 맞춤형 멘토링 지원 공고')
})

test('runSupportProgramSearch pins Gyeongbuk social economy school when returned programs are local', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => [
      {
        programId: 21,
        title: '2026년 구미시 스타트업 해외시장 개척 지원사업 글로벌(CES 2027) 진출 창업기업 모집 재공고',
        source: 'bizinfo',
        summary: '구미시 창업기업 해외시장 개척 지원',
        regionCondition: '구미시',
        supportType: 'mentoring',
        status: 'open',
        matchScore: 88,
        matchReasons: ['희망 시도와 지역 조건이 맞습니다.'],
        cautionReasons: [],
        applicationEndDate: '2026-06-30',
      },
    ],
  })

  const results = await runSupportProgramSearch({
    priority: 'HIGH_MATCH',
    startupProfile: {
      interestField: '카페',
    },
  })

  assert.equal(results[0].title, PINNED_GYEONGBUK_SOCIAL_PROGRAM_TITLE)
  assert.equal(results[1].title, '2026년 구미시 스타트업 해외시장 개척 지원사업 글로벌(CES 2027) 진출 창업기업 모집 재공고')
})

test('runSupportProgramSearch can sort by nearest actual deadline', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => [
      {
        programId: 1,
        title: '늦은 마감 공고',
        matchScore: 95,
        matchReasons: [],
        cautionReasons: [],
        applicationEndDate: '2026-08-01',
      },
      {
        programId: 2,
        title: '빠른 마감 공고',
        matchScore: 80,
        matchReasons: [],
        cautionReasons: [],
        applicationEndDate: '2026-06-20',
      },
    ],
  })

  const results = await runSupportProgramSearch({ priority: 'FAST_DEADLINE' })

  assert.equal(results[0].title, '빠른 마감 공고')
})
