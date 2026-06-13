import test from 'node:test'
import assert from 'node:assert/strict'
import { buildCurrentResult, buildFeatureSeed, buildWorkspacePatch } from './featureChatContext.js'
import { PINNED_GYEONGBUK_SOCIAL_PROGRAM_TITLE } from '../reports/supportProgramSearch.js'

test('buildFeatureSeed reflects selected support for plan page', () => {
  const seed = buildFeatureSeed('plan', {
    selectedIdea: { rank: 2, title: '로컬 쿠키 브랜딩 스튜디오' },
    selectedSupportProgram: { title: '2026 청년 예비창업 패키지' },
    focusedSection: { title: '3. 해결 방안' },
    planGoal: 'CHECK_GAPS',
  })

  assert.equal(seed.data.target, '2026 청년 예비창업 패키지')
  assert.equal(seed.focusedSectionTitle, '3. 해결 방안')
  assert.equal(seed.planGoal, 'CHECK_GAPS')
})

test('buildWorkspacePatch stores selected idea and support program', () => {
  const itemPatch = buildWorkspacePatch({
    featureId: 'item',
    data: {
      items: [
        { rank: 1, title: 'A' },
        { rank: 2, title: 'B' },
      ],
    },
    selectedIdeaRank: 2,
  })

  const supportPatch = buildWorkspacePatch({
    featureId: 'support',
    data: {
      list: [
        { title: '지원사업 A' },
        { title: '지원사업 B' },
      ],
    },
    selectedSupportTitle: '지원사업 B',
    supportSearchMode: 'PROFILE_ONLY',
    supportUserGoal: 'EASY_PREP',
  })

  assert.equal(itemPatch.selectedIdea.title, 'B')
  assert.equal(supportPatch.selectedSupportProgram.title, '지원사업 B')
  assert.equal(supportPatch.supportSearchMode, 'PROFILE_ONLY')
  assert.equal(supportPatch.supportUserGoal, 'EASY_PREP')
})

test('buildWorkspacePatch can select the pinned support program even before searching', () => {
  const supportPatch = buildWorkspacePatch({
    featureId: 'support',
    data: {
      list: [],
    },
    selectedSupportTitle: PINNED_GYEONGBUK_SOCIAL_PROGRAM_TITLE,
    supportSearchMode: 'PROFILE_IDEA',
    supportUserGoal: 'HIGH_MATCH',
  })

  assert.equal(supportPatch.selectedSupportProgram.title, PINNED_GYEONGBUK_SOCIAL_PROGRAM_TITLE)
  assert.equal(supportPatch.selectedSupportProgram.score, 91)
})

test('buildCurrentResult for support includes startup profile and linked idea', () => {
  const result = buildCurrentResult({
    featureId: 'support',
    data: {
      list: [{ title: '지원사업 A' }],
    },
    selectedSupportTitle: '지원사업 A',
    supportSearchMode: 'PROFILE_IDEA',
    supportUserGoal: 'HIGH_MATCH',
    workspaceContext: {
      selectedIdea: { rank: 1, title: '선택된 아이템' },
    },
    startupProfile: {
      residenceRegion: '부산',
      initialBudget: 3000000,
    },
  })

  assert.equal(result.profileContext.startupProfile.residenceRegion, '부산')
  assert.equal(result.ideaContext.selectedIdea.title, '선택된 아이템')
  assert.equal(result.selectedSupportProgram.title, '지원사업 A')
})

test('buildCurrentResult for sns includes campaign context and priority', () => {
  const result = buildCurrentResult({
    featureId: 'sns',
    data: {
      topic: '쿠키 런칭',
      hook: '후킹 문구',
      beats: ['A'],
      tags: ['#tag'],
      schedule: '수요일 9시',
      channel: 'INSTAGRAM_REELS',
      tone: 'FRIENDLY',
      objective: 'CONVERSION',
      callToAction: '지금 예약 주문하기',
    },
    workspaceContext: {
      selectedIdea: { title: '쿠키 브랜드' },
      operationContext: {
        highlightSuggestion: {
          title: '광고 전환율 개선',
        },
      },
      planDraft: {
        target: '청년 창업 지원',
      },
    },
    startupProfile: {
      preferredBusinessType: 'ONLINE',
    },
  })

  assert.equal(result.campaignContext.selectedIdea.title, '쿠키 브랜드')
  assert.equal(result.campaignContext.operationFocus.title, '광고 전환율 개선')
  assert.equal(result.campaignContext.planDraft.target, '청년 창업 지원')
  assert.deepEqual(result.contextPriority, [
    'campaignDraft',
    'campaignContext',
    'startupProfile',
  ])
  assert.equal(result.campaignDraft.channel, 'INSTAGRAM_REELS')
  assert.equal(result.campaignDraft.objective, 'CONVERSION')
  assert.equal(result.campaignDraft.topic, '쿠키 런칭')
})

test('buildCurrentResult for operation prioritizes live operation input with business context', () => {
  const result = buildCurrentResult({
    featureId: 'operation',
    data: {
      period: '2026-06',
      kpis: [
        ['이번 달 매출', '2780000원', '+12%', true],
      ],
      products: [
        ['수제 쿠키', 21],
      ],
      channels: [
        ['인스타그램 광고', '전환율 1.8%, CPC 420원'],
      ],
      notes: '인스타 광고 효율이 이번 주 급감함',
      suggestions: [
        ['광고 전환율 개선', '광고 카피를 손보자', 'sns'],
      ],
    },
    workspaceContext: {
      selectedIdea: { title: '쿠키 브랜드', rank: 1 },
      simulationContext: { capital: 200, item: '쿠키 브랜드' },
      selectedSupportProgram: { title: '청년 창업 지원' },
      planDraft: { target: '청년 창업 지원' },
    },
    startupProfile: {
      residenceRegion: '부산',
    },
    selectedOperationSuggestionTitle: '광고 전환율 개선',
  })

  assert.deepEqual(result.contextPriority, [
    'operationInput',
    'operationReport',
    'businessContext',
    'startupProfile',
  ])
  assert.equal(result.operationInput.period, '2026-06')
  assert.equal(result.operationInput.notes, '인스타 광고 효율이 이번 주 급감함')
  assert.equal(result.operationReport.selectedSuggestion.title, '광고 전환율 개선')
  assert.equal(result.businessContext.selectedIdea.title, '쿠키 브랜드')
})
