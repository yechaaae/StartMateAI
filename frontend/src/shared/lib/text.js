// AI가 생성한 텍스트에 HTML 엔티티(&lsquo; &rsquo; &amp; &#39; 등)가 섞여 들어오는 경우가 있어,
// 화면에 그대로 노출되지 않도록 디코딩한다. (React 텍스트 노드는 엔티티를 자동 디코딩하지 않음)
// DOM에 의존하지 않아 어디서든 안전하게 호출 가능.
const NAMED_ENTITIES = {
  amp: '&',
  lt: '<',
  gt: '>',
  quot: '"',
  apos: "'",
  nbsp: ' ',
  lsquo: '‘',
  rsquo: '’',
  sbquo: '‚',
  ldquo: '“',
  rdquo: '”',
  bdquo: '„',
  hellip: '…',
  mdash: '—',
  ndash: '–',
  middot: '·',
  trade: '™',
  reg: '®',
  copy: '©',
}

export const decodeHtmlEntities = (text) => {
  if (typeof text !== 'string' || !text.includes('&')) {
    return text
  }
  return text.replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);/g, (match, code) => {
    if (code[0] === '#') {
      const isHex = code[1] === 'x' || code[1] === 'X'
      const codePoint = isHex ? parseInt(code.slice(2), 16) : parseInt(code.slice(1), 10)
      if (!Number.isFinite(codePoint) || codePoint <= 0) {
        return match
      }
      try {
        return String.fromCodePoint(codePoint)
      } catch {
        return match
      }
    }
    return NAMED_ENTITIES[code] ?? NAMED_ENTITIES[code.toLowerCase()] ?? match
  })
}
