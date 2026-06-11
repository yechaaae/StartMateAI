import assert from 'node:assert/strict'
import test from 'node:test'

import { loginFields, signupFields } from './authFormFields.js'

test('auth password fields opt out of browser password manager prompts', () => {
  const passwordFields = [...loginFields, ...signupFields]
    .filter((field) => field.type === 'password')

  assert.ok(passwordFields.length > 0)
  passwordFields.forEach((field) => {
    assert.equal(field.autoComplete, 'off')
    assert.equal(field.ignorePasswordManagers, true)
  })
})
