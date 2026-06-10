import test from 'node:test'
import assert from 'node:assert/strict'
import {
  canRevealNextAuthField,
  getNextAuthRevealCount,
  getVisibleAuthFieldNames,
  isAuthStepValueReady,
} from './authStepFlow.js'

const loginSteps = [
  { name: 'email' },
  { name: 'password' },
]

const signupSteps = [
  { name: 'email' },
  { name: 'nickname' },
  { name: 'password' },
  { name: 'passwordConfirm', revealWithPrevious: true },
]

test('checks whether individual auth values are ready to reveal the next field', () => {
  assert.equal(isAuthStepValueReady('email', 'founder@example.com'), true)
  assert.equal(isAuthStepValueReady('email', 'bad-email'), false)
  assert.equal(isAuthStepValueReady('nickname', '민서'), true)
  assert.equal(isAuthStepValueReady('password', 'secret123'), true)
  assert.equal(isAuthStepValueReady('password', '123'), false)
})

test('shows only the fields that the user has explicitly reached', () => {
  assert.deepEqual(getVisibleAuthFieldNames(loginSteps, 1), ['email'])
  assert.deepEqual(getVisibleAuthFieldNames(loginSteps, 2), [
    'email',
    'password',
  ])
})

test('reveals the next field only after the current visible field is completed', () => {
  assert.equal(canRevealNextAuthField(signupSteps, 1, { email: 'bad-email' }), false)
  assert.equal(canRevealNextAuthField(signupSteps, 1, { email: 'founder@example.com' }), true)
  assert.equal(canRevealNextAuthField(signupSteps, 2, {
    email: 'founder@example.com',
    nickname: '민서',
  }), true)
  assert.equal(canRevealNextAuthField(signupSteps, 4, {
    email: 'founder@example.com',
    nickname: '민서',
    password: 'secret123',
    passwordConfirm: 'secret123',
  }), false)
})

test('reveals grouped fields together when the next field has companions', () => {
  assert.equal(getNextAuthRevealCount(signupSteps, 1, { email: 'founder@example.com' }), 2)
  assert.equal(getNextAuthRevealCount(signupSteps, 2, {
    email: 'founder@example.com',
    nickname: '민서',
  }), 4)
})
