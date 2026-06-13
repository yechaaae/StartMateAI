import test from 'node:test'
import assert from 'node:assert/strict'
import {
  getFirstIncompleteOnboardingField,
  getOnboardingProgress,
  getOnboardingStepCount,
  getVisibleOnboardingFields,
  isOnboardingStepComplete,
} from './onboardingFlow.js'

const prePartial = {
  major: '컴퓨터공학',
  career: '카페 매니저 1년',
  interestField: 'F&B',
  residenceRegion: '부산 해운대구',
  businessRegion: '부산',
  initialBudget: '3000000',
  teamStatus: 'SOLO',
  preferredBusinessType: 'ONLINE',
  strengthTags: '실행력, 디자인 감각',
}

const preForm = { ...prePartial, stage: 'PRE_STARTUP' }

const postForm = {
  stage: 'POST_STARTUP',
  major: '시각디자인',
  career: '카페 매니저 1년',
  interestField: 'F&B',
  residenceRegion: '부산 해운대구',
  businessRegion: '부산 해운대구 구남로',
  teamStatus: 'SOLO',
  preferredBusinessType: 'LOCAL_STORE',
  strengthTags: '브랜딩, SNS',
  currentItemName: '구남로 수제 쿠키',
  currentIndustry: '카페',
  operatingPeriod: 'SIX_TO_12M',
  initialBudget: '',
}

test('stage selection is the first step and gates the rest of the flow', () => {
  assert.equal(getOnboardingStepCount(''), 1)
  assert.equal(isOnboardingStepComplete(0, { stage: '' }), false)
  assert.equal(isOnboardingStepComplete(0, { stage: 'PRE_STARTUP' }), true)
})

test('pre-startup flow keeps the original 3 steps after stage selection', () => {
  assert.equal(getOnboardingStepCount('PRE_STARTUP'), 4)

  assert.equal(isOnboardingStepComplete(1, { ...preForm, teamStatus: '' }), false)
  assert.equal(isOnboardingStepComplete(1, preForm), true)
  assert.equal(isOnboardingStepComplete(2, { ...preForm, initialBudget: '' }), false)
  assert.equal(isOnboardingStepComplete(2, { ...preForm, initialBudget: '0' }), true)
  assert.equal(isOnboardingStepComplete(3, { ...preForm, career: '' }), false)
  assert.equal(isOnboardingStepComplete(3, preForm), true)
})

test('post-startup flow asks for current business info instead of initial budget', () => {
  assert.equal(getOnboardingStepCount('POST_STARTUP'), 5)

  // step 1: current business info
  assert.equal(isOnboardingStepComplete(1, { ...postForm, currentItemName: '' }), false)
  assert.equal(isOnboardingStepComplete(1, { ...postForm, operatingPeriod: '' }), false)
  assert.equal(isOnboardingStepComplete(1, postForm), true)

  // basics step (index 3) does not require initialBudget
  assert.equal(isOnboardingStepComplete(3, postForm), true)
})

test('reports progress relative to the selected stage step count', () => {
  assert.deepEqual(getOnboardingProgress(0, 'PRE_STARTUP'), { current: 1, total: 4, percent: 25 })
  assert.deepEqual(getOnboardingProgress(3, 'PRE_STARTUP'), { current: 4, total: 4, percent: 100 })
  assert.deepEqual(getOnboardingProgress(4, 'POST_STARTUP'), { current: 5, total: 5, percent: 100 })
})

test('finds the first incomplete field for the current onboarding step', () => {
  assert.equal(getFirstIncompleteOnboardingField(1, {
    ...preForm,
    preferredBusinessType: '',
    teamStatus: '',
  }), 'preferredBusinessType')

  assert.equal(getFirstIncompleteOnboardingField(1, {
    ...preForm,
    preferredBusinessType: 'ONLINE',
    teamStatus: '',
  }), 'teamStatus')

  assert.equal(getFirstIncompleteOnboardingField(2, { ...preForm, major: '' }), 'major')
  assert.equal(getFirstIncompleteOnboardingField(3, preForm), null)
})

test('reveals team status only after preferred business type is selected', () => {
  assert.deepEqual(getVisibleOnboardingFields(1, {
    ...preForm,
    preferredBusinessType: '',
    teamStatus: '',
  }), ['preferredBusinessType'])

  assert.deepEqual(getVisibleOnboardingFields(1, {
    ...preForm,
    preferredBusinessType: 'ONLINE',
    teamStatus: '',
  }), ['preferredBusinessType', 'teamStatus'])
})
