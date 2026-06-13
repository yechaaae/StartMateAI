import test from 'node:test'
import assert from 'node:assert/strict'
import { addTag, joinTags, parseTags } from './onboardingTags.js'

test('parseTags splits a comma string into trimmed non-empty tags', () => {
  assert.deepEqual(parseTags('디자인, 개발 ,, 마케팅'), ['디자인', '개발', '마케팅'])
  assert.deepEqual(parseTags(''), [])
  assert.deepEqual(parseTags(null), [])
})

test('addTag appends a trimmed tag and rejoins as a string', () => {
  assert.equal(addTag('디자인', '  개발 ', 10), '디자인, 개발')
  assert.equal(joinTags(['디자인', '개발']), '디자인, 개발')
})

test('addTag ignores empty input and case-insensitive duplicates', () => {
  assert.equal(addTag('디자인', '', 10), '디자인')
  assert.equal(addTag('Design', 'design', 10), 'Design')
})

test('addTag does not exceed the max tag count', () => {
  const full = joinTags(['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])
  assert.equal(addTag(full, '11', 10), full)
})
