import assert from 'node:assert/strict'
import test from 'node:test'
import { runSupportProgramSearch } from './supportProgramSearch.js'

test('runSupportProgramSearch sorts by support priority', async () => {
  const results = await runSupportProgramSearch({ priority: 'LARGE_SUPPORT', delayMs: 0 })

  assert.equal(results[0].title, '2026 청년 예비창업 패키지')
  assert.equal(results[0].amount, 100000000)
})

test('runSupportProgramSearch sorts by preparation ease priority', async () => {
  const results = await runSupportProgramSearch({ priority: 'EASY_PREP', delayMs: 0 })

  assert.equal(results[0].title, '1인 미디어 콘텐츠 창업 지원')
})

test('runSupportProgramSearch sorts by deadline priority', async () => {
  const results = await runSupportProgramSearch({ priority: 'FAST_DEADLINE', delayMs: 0 })

  assert.equal(results[0].title, '서울 소상공인 창업 성장 지원')
})
