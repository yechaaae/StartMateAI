// 공고/신청서 양식에 맞춰 plan 페이지 UI가 '그 신청서 폼'으로 바뀌도록 하는 폼 스키마.
// 현재는 경북 사회적경제 창업학교 신청서를 고정 정의하고, AI가 생성한 답변(창업 아이템·지원동기)을
// 해당 칸에 채워 넣는다. 다른 공고도 같은 스키마 형태로 추가하면 UI가 그에 맞게 바뀐다.

export const GYEONGBUK_APPLICATION_FORM = {
  programTitle: '2026년 경북형 사회적경제 창업학교 참가자 모집',
  title: '2026 경북형 사회적경제 창업학교 참가 신청서',
  description: '* 표시는 필수 항목입니다. 창업 아이템·지원동기는 AI가 채워 두었으니 확인 후 다듬어 제출하세요.',
  fields: [
    { key: 'name', label: '성명', type: 'text', required: true },
    { key: 'phone', label: '연락처', type: 'text', required: true, placeholder: '010-0000-0000' },
    { key: 'email', label: '이메일', type: 'text', required: true },
    {
      key: 'region',
      label: '거주지역(시·군까지)',
      type: 'text',
      required: true,
      placeholder: '예: 경산, 대구, 청도군, 서울',
    },
    {
      key: 'startupStatus',
      label: '창업여부',
      type: 'radio',
      required: true,
      options: ['예비창업자', '기 창업자', '기타'],
    },
    {
      key: 'item',
      label: '창업 아이템(사회적가치를 담아 간단하게 작성)',
      type: 'textarea',
      required: true,
      aiSource: '아이템',
    },
    {
      key: 'motivation',
      label: '지원동기',
      type: 'textarea',
      required: true,
      aiSource: '동기',
    },
    {
      key: 'attendance',
      label: '주차별 교육 참가 확인',
      type: 'checkboxGroup',
      defaultAll: true,
      options: [
        '(1차시) 6. 20.(토) 13:00~17:00',
        '(2차시) 6. 27.(토) 13:00~17:00',
        '(3차시) 7. 4.(토) 13:00~17:00',
        '(4차시) 7. 11.(토) 13:00~17:00',
        '온라인 교육(4시간)',
      ],
    },
    {
      key: 'channel',
      label: '경북형 사회적경제 창업학교를 알게 된 경로',
      type: 'radio',
      options: ['SNS', '홈페이지', '지인 추천', '교내·외 홍보물(포스터, 현수막 등)', '기타'],
    },
    {
      key: 'consent',
      label: '개인정보 수집·이용·제공 및 활용 동의',
      type: 'consent',
      consentText: '동의 함',
    },
  ],
}

const FORMS = [GYEONGBUK_APPLICATION_FORM]

// 연결된 지원사업/공고 텍스트로 해당하는 신청서 폼을 고른다. 없으면 null(일반 사업계획서 모드).
export const applicationFormForContext = ({ program = null, announcement = '' } = {}) => {
  const programTitle = program?.title ?? ''
  const text = announcement ?? ''
  return (
    (programTitle && FORMS.find((form) => form.programTitle === programTitle))
    || (text.includes('경북형 사회적경제 창업학교') ? GYEONGBUK_APPLICATION_FORM : null)
  )
}
