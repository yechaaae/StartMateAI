import assert from 'node:assert/strict'
import test from 'node:test'

import { decodeHtmlEntities } from './text.js'

test('decodeHtmlEntities는 따옴표 엔티티를 실제 문자로 바꾼다', () => {
  assert.equal(
    decodeHtmlEntities('부산 &lsquo;한정 메뉴&rsquo; 팝업'),
    '부산 ‘한정 메뉴’ 팝업',
  )
  assert.equal(decodeHtmlEntities('&ldquo;테스트&rdquo;'), '“테스트”')
})

test('숫자/16진수 엔티티도 디코딩한다', () => {
  assert.equal(decodeHtmlEntities('It&#39;s'), "It's")
  assert.equal(decodeHtmlEntities('It&#x27;s'), "It's")
})

test('일반 텍스트와 비문자열은 그대로 둔다', () => {
  assert.equal(decodeHtmlEntities('그냥 텍스트'), '그냥 텍스트')
  assert.equal(decodeHtmlEntities(''), '')
  assert.equal(decodeHtmlEntities(null), null)
  assert.equal(decodeHtmlEntities(undefined), undefined)
})

test('알 수 없는 엔티티는 원본을 유지한다', () => {
  assert.equal(decodeHtmlEntities('a &unknownentity; b'), 'a &unknownentity; b')
  assert.equal(decodeHtmlEntities('5 < 10 그대로'), '5 < 10 그대로')
})

test('&amp; 등 기본 엔티티도 처리한다', () => {
  assert.equal(decodeHtmlEntities('A &amp; B'), 'A & B')
})
