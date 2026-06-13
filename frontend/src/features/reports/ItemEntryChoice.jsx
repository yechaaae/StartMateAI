import { Icon } from '../../shared/components/Icon'

// 아이템 기능 진입 시 두 갈래(추천 받기 / 직접 입력)를 고르는 화면.
// 사용자의 창업 단계(stage)로 기본 추천 갈래만 강조하고, 최종 선택은 사용자가 한다.
// stage가 아직 안 내려오면(백엔드 미반영) 추천 받기를 기본으로 둔다.
export const ItemEntryChoice = ({ stage, onChooseRecommend, onChooseInput }) => {
  const inputDefault = stage === 'POST_STARTUP'
  const recommendDefault = !inputDefault

  const stageHint = stage === 'POST_STARTUP'
    ? '이미 운영 중인 아이템이 있으니 직접 입력을 추천해요.'
    : stage === 'PRE_STARTUP'
      ? '아직 아이템을 정하기 전이라면 AI 추천부터 받아보세요.'
      : '원하는 방식으로 시작하세요. AI 추천을 먼저 받아도 좋아요.'

  return (
    <div className="item-entry">
      <div className="item-entry-head">
        <h2>어떻게 아이템을 정할까요?</h2>
        <p>{stageHint}</p>
      </div>
      <div className="item-entry-grid">
        <button
          type="button"
          className={recommendDefault ? 'card item-entry-card recommended' : 'card item-entry-card'}
          onClick={onChooseRecommend}
        >
          {recommendDefault && <span className="item-entry-badge">추천</span>}
          <Icon name="sparkle" size={28} />
          <h3>AI 아이템 추천 받기</h3>
          <p>프로필과 상권을 분석해 적합한 창업 아이템을 추천받고, 마음에 드는 걸 골라요.</p>
          <span className="item-entry-cta">추천 받기 <Icon name="arrow" size={15} /></span>
        </button>

        <button
          type="button"
          className={inputDefault ? 'card item-entry-card recommended' : 'card item-entry-card'}
          onClick={onChooseInput}
        >
          {inputDefault && <span className="item-entry-badge">추천</span>}
          <Icon name="edit" size={28} />
          <h3>내 아이템 직접 입력</h3>
          <p>이미 운영 중이거나 정해둔 아이템이 있다면 직접 입력해 바로 시작해요.</p>
          <span className="item-entry-cta">직접 입력 <Icon name="arrow" size={15} /></span>
        </button>
      </div>
    </div>
  )
}
