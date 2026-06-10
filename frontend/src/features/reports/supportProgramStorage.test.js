import assert from 'node:assert/strict'
import test from 'node:test'
import {
  buildSupportProgramStorageEntry,
  mergeSupportProgramHistory,
  removeSupportProgramHistoryItem,
} from './supportProgramStorage.js'

test('mergeSupportProgramHistory saves new recommendations without duplicating existing ids', () => {
  const existing = [
    buildSupportProgramStorageEntry({ id: 'a', title: '기존 사업' }, { priority: 'HIGH_MATCH' }, '2026-06-10T10:00:00.000Z'),
  ]
  const next = mergeSupportProgramHistory(
    existing,
    [{ id: 'a', title: '업데이트 사업' }, { id: 'b', title: '신규 사업' }],
    { priority: 'FAST_DEADLINE' },
    '2026-06-10T11:00:00.000Z',
  )

  assert.equal(next.length, 2)
  assert.equal(next[0].id, 'a')
  assert.equal(next[0].title, '업데이트 사업')
  assert.equal(next[0].savedAt, '2026-06-10T11:00:00.000Z')
  assert.equal(next[1].id, 'b')
})

test('removeSupportProgramHistoryItem removes by stable id', () => {
  const existing = [
    { id: 'a', title: 'A' },
    { id: 'b', title: 'B' },
  ]

  assert.deepEqual(removeSupportProgramHistoryItem(existing, 'a'), [{ id: 'b', title: 'B' }])
})
