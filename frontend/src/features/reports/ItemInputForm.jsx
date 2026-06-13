import { useState } from 'react'
import { Icon } from '../../shared/components/Icon'

// 이미 아이템이 있는 사용자가 직접 아이템을 입력하는 폼.
// 창업 후 프로필 값(currentItemName/currentIndustry/businessRegion)이 있으면 프리필한다.
// 확정하면 입력값을 선택 아이템(워크스페이스)으로 만들어 다음 단계로 넘긴다.
export const ItemInputForm = ({ prefill, onSubmit, onBack }) => {
  const [itemName, setItemName] = useState(prefill?.itemName ?? '')
  const [industry, setIndustry] = useState(prefill?.industry ?? '')
  const [region, setRegion] = useState(prefill?.region ?? '')

  const canSubmit = itemName.trim().length > 0

  const submit = () => {
    if (!canSubmit) {
      return
    }
    onSubmit?.({
      title: itemName.trim(),
      category: industry.trim() || '직접 입력 아이템',
      location: region.trim() || null,
      reason: '직접 입력한 운영/창업 아이템입니다.',
      score: null,
    })
  }

  return (
    <div className="item-input">
      <button type="button" className="item-input-back" onClick={onBack}>
        <Icon name="arrow" size={14} style={{ transform: 'rotate(180deg)' }} /> 다시 선택
      </button>

      <div className="item-input-head">
        <h2>내 아이템 입력</h2>
        <p>운영 중이거나 정해둔 아이템 정보를 입력하면 이 아이템으로 다음 단계를 진행해요.</p>
      </div>

      <div className="item-input-fields">
        <label className="item-input-field">
          <span>아이템 / 사업명 <em>*</em></span>
          <input
            type="text"
            value={itemName}
            placeholder="예: 연남동 수제 쿠키 공방"
            onChange={(event) => setItemName(event.target.value)}
          />
        </label>

        <label className="item-input-field">
          <span>업종</span>
          <input
            type="text"
            value={industry}
            placeholder="예: 디저트 카페, 온라인 커머스"
            onChange={(event) => setIndustry(event.target.value)}
          />
        </label>

        <label className="item-input-field">
          <span>사업 지역</span>
          <input
            type="text"
            value={region}
            placeholder="예: 서울 마포구 연남동"
            onChange={(event) => setRegion(event.target.value)}
          />
        </label>
      </div>

      <button type="button" className="item-input-submit" onClick={submit} disabled={!canSubmit}>
        이 아이템으로 시작하기 <Icon name="arrow" size={16} />
      </button>
      {!canSubmit && <span className="item-input-hint">아이템/사업명은 필수예요.</span>}
    </div>
  )
}
