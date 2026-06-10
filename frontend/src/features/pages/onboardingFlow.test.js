import test from 'node:test'
import assert from 'node:assert/strict'
import {
  getFirstIncompleteOnboardingField,
  getOnboardingProgress,
  getVisibleOnboardingFields,
  isOnboardingStepComplete,
} from './onboardingFlow.js'

const completeForm = {
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

test('checks required values for each onboarding step', () => {
  assert.equal(isOnboardingStepComplete(0, { ...completeForm, teamStatus: '' }), false)
  assert.equal(isOnboardingStepComplete(0, completeForm), true)

  assert.equal(isOnboardingStepComplete(1, { ...completeForm, initialBudget: '' }), false)
  assert.equal(isOnboardingStepComplete(1, { ...completeForm, initialBudget: '0' }), true)

  assert.equal(isOnboardingStepComplete(2, { ...completeForm, career: '' }), false)
  assert.equal(isOnboardingStepComplete(2, completeForm), true)
})

test('reports progress from the current onboarding step', () => {
  assert.deepEqual(getOnboardingProgress(0), { current: 1, total: 3, percent: 33 })
  assert.deepEqual(getOnboardingProgress(2), { current: 3, total: 3, percent: 100 })
})

test('finds the first incomplete field for the current onboarding step', () => {
  assert.equal(getFirstIncompleteOnboardingField(0, {
    ...completeForm,
    preferredBusinessType: '',
    teamStatus: '',
  }), 'preferredBusinessType')

  assert.equal(getFirstIncompleteOnboardingField(0, {
    ...completeForm,
    preferredBusinessType: 'ONLINE',
    teamStatus: '',
  }), 'teamStatus')

  assert.equal(getFirstIncompleteOnboardingField(1, {
    ...completeForm,
    major: '',
  }), 'major')

  assert.equal(getFirstIncompleteOnboardingField(2, completeForm), null)
})

test('reveals team status only after preferred business type is selected', () => {
  assert.deepEqual(getVisibleOnboardingFields(0, {
    ...completeForm,
    preferredBusinessType: '',
    teamStatus: '',
  }), ['preferredBusinessType'])

  assert.deepEqual(getVisibleOnboardingFields(0, {
    ...completeForm,
    preferredBusinessType: 'ONLINE',
    teamStatus: '',
  }), ['preferredBusinessType', 'teamStatus'])
})
