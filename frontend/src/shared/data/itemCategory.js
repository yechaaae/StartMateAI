// 아이템 업종(business_type) 코드를 한글 라벨로 변환한다.
// 이미 한글이거나 매핑에 없는 값(지역명, 작업공간 등)은 그대로 반환한다.
const LABELS = {
  cafe: '카페',
  food: '푸드',
  commerce: '커머스',
  content: '콘텐츠',
  popup: '팝업',
  service: '서비스',
  other: '기타',
}

export const categoryLabel = (value) => {
  if (!value) return ''
  const key = String(value).trim().toLowerCase()
  return LABELS[key] ?? value
}
