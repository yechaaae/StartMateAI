// 공고/신청서 양식에 맞춰 plan 페이지 UI가 '그 신청서 폼'으로 바뀌도록 하는 폼 스키마.
// 현재는 경북 사회적경제 창업학교 신청서를 고정 정의한다.
// 이 페이지에서는 AI가 채울 수 있는 항목(창업여부·창업 아이템·지원동기)만 보여주고,
// 공고 분석을 리포트 형식으로 함께 제공한다. (성명·연락처 등 개인정보 항목은 노출하지 않는다)

export const GYEONGBUK_APPLICATION_FORM = {
  programTitle: '2026년 경북형 사회적경제 창업학교 참가자 모집',
  title: '2026 경북형 사회적경제 창업학교 · 신청 항목 자동 작성',
  description: '아래 항목은 입력하신 프로필과 선택한 아이템을 바탕으로 자동 작성했어요. 확인 후 다듬어 신청서에 붙여넣으세요.',
  // 공고 분석 리포트(고정). 공고 내용을 요약·분석해 신청 전략을 정리한다.
  analysis: {
    title: '공고 분석 리포트',
    sections: [
      [
        '한눈에 보기',
        '경상북도 사회적경제지원센터(주관: 대구대학교 산학협력단)가 운영하는 사회적경제 창업교육 프로그램입니다. ' +
          '예비창업자·3년 미만 창업자가 대상이며, 접수기간은 2026.05.19 ~ 06.14입니다.',
      ],
      [
        '지원 내용',
        '· 기본교육: 사회적경제 기초 및 창업 실무 교육 (총 20시간)\n' +
          '· 사업화 지원: 우수창업팀 대상 총 5천만원 규모 사업비\n' +
          '· 창업공간 제공, 사회적경제기업 전환 컨설팅, 성장지원사업 연계 및 선배기업가 네트워킹\n' +
          '· 80% 이상 수강 시 수료증 발급(사회적경제기업 인·지정 및 타 지원사업 신청 시 활용 가능)',
      ],
      [
        '교육 일정·장소',
        '2026. 6. 20.(토) ~ 7. 11.(토) 총 4회 / 대구대학교 경산캠퍼스(경북 경산시 진량읍 대구대로 201).',
      ],
      [
        '신청 자격·방법',
        '사회적경제에 관심 있는 대한민국 국민 누구나(예비창업자·3년 미만 창업자 포함). ' +
          '이메일(gbsecenter@daum.net) 또는 온라인 구글폼으로 접수합니다.',
      ],
      [
        '전략 포인트',
        '· 별도 선정평가는 없지만, 사회적 가치와 실행 가능성을 분명히 보여줄수록 사업화·컨설팅 연계에 유리합니다.\n' +
          '· 수료증은 사회적경제기업 인·지정 및 타 지원사업 신청에 활용할 수 있으니 80% 이상 수강을 권장합니다.',
      ],
    ],
  },
  fields: [
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
    },
    {
      key: 'motivation',
      label: '지원동기',
      type: 'textarea',
      required: true,
      aiSource: '동기',
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
