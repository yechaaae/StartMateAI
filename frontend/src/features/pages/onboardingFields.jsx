import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Icon } from '../../shared/components/Icon'
import { addTag, joinTags, parseTags } from './onboardingTags'

// ===== 태그 입력 (전공/관심 분야 등 쉼표로 저장되는 문자열을 태그로 다룸) =====
export const TagField = ({ targetName, label, name, value, onChange, placeholder, max = 10 }) => {
  const [draft, setDraft] = useState('')
  const tags = parseTags(value)
  const isFull = tags.length >= max

  const commitDraft = () => {
    const next = addTag(value, draft, max)
    if (next !== value) {
      onChange(next)
    }
    setDraft('')
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      commitDraft()
    } else if (event.key === 'Backspace' && !draft && tags.length) {
      onChange(joinTags(tags.slice(0, -1)))
    }
  }

  return (
    <label className="onboarding-field wide-field" data-onboarding-target={targetName}>
      <span>{label} <small className="onboarding-tag-count">{tags.length}/{max}</small></span>
      <div className="onboarding-tag-input">
        {tags.map((tag) => (
          <span className="onboarding-tag" key={tag}>
            {tag}
            <button type="button" onClick={() => onChange(joinTags(tags.filter((item) => item !== tag)))} aria-label={`${tag} 삭제`}>
              <Icon name="plus" size={12} style={{ transform: 'rotate(45deg)' }} />
            </button>
          </span>
        ))}
        {!isFull && (
          <input
            name={name}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={commitDraft}
            placeholder={tags.length ? '엔터로 추가' : placeholder}
          />
        )}
      </div>
    </label>
  )
}

// ===== 지역 선택 (시/도 → 시·군·구 → 읍·면·동 단계 선택) =====
// 행정구역 데이터는 모달을 처음 열 때 동적 import로 lazy-load 한다(약 66KB).
// 세부 주소·건물은 다루지 않고 "동" 단위 지역까지만 저장한다.
let regionsCache = null
const loadRegions = async () => {
  if (!regionsCache) {
    regionsCache = (await import('../../shared/data/regions.json')).default
  }
  return regionsCache
}

// 동 드롭다운의 "전체"(시·군·구 전체) 선택을 나타내는 sentinel 값.
const ALL_DONG = '__ALL__'

// 시·군·구가 시·도와 같은 경우(세종)는 시·군·구를 생략하고 합친다.
const joinRegion = (sido, sigungu, dong) => (
  [sido, sigungu !== sido ? sigungu : '', dong].filter(Boolean).join(' ')
)

// 저장된 문자열을 다시 시/도·구·동으로 분해해 모달을 열 때 이전 선택을 복원한다(best-effort).
const parseRegionValue = (value, regions) => {
  const empty = { sido: '', sigungu: '', dong: '' }
  if (!value || !regions) return empty
  const sido = Object.keys(regions).find((name) => value.startsWith(name))
  if (!sido) return empty
  const rest = value.slice(sido.length).trim()
  const sigunguList = Object.keys(regions[sido])
  const sigungu = sigunguList.find((sg) => sg !== sido && rest.startsWith(sg))
  if (sigungu) {
    const dong = rest.slice(sigungu.length).trim()
    return { sido, sigungu, dong: regions[sido][sigungu].includes(dong) ? dong : '' }
  }
  // 세종 등 시·군·구가 1개뿐인 경우
  const onlySigungu = sigunguList.length === 1 ? sigunguList[0] : ''
  return { sido, sigungu: onlySigungu, dong: onlySigungu && regions[sido][onlySigungu].includes(rest) ? rest : '' }
}

export const AddressField = ({ targetName, label, value, onChange, placeholder }) => {
  const [open, setOpen] = useState(false)
  const [regions, setRegions] = useState(regionsCache)
  const [sido, setSido] = useState('')
  const [sigungu, setSigungu] = useState('')

  const openModal = async () => {
    setOpen(true)
    const data = regions || (await loadRegions())
    if (!regions) setRegions(data)
    const parsed = parseRegionValue(value, data)
    setSido(parsed.sido)
    setSigungu(parsed.sigungu)
  }

  const closeModal = () => setOpen(false)

  const sidoList = regions ? Object.keys(regions) : []
  const sigunguList = regions && sido ? Object.keys(regions[sido]) : []
  const dongList = regions && sido && sigungu ? regions[sido][sigungu] : []

  const onSido = (next) => {
    setSido(next)
    // 시·군·구가 1개뿐이면(세종 등) 자동 선택해 바로 동 선택으로 넘어가게 한다.
    const list = Object.keys(regions[next])
    setSigungu(list.length === 1 ? list[0] : '')
  }

  const onDong = (next) => {
    if (!next) return
    // "전체"는 동 없이 시·군·구까지만 저장한다.
    onChange(next === ALL_DONG ? joinRegion(sido, sigungu, '') : joinRegion(sido, sigungu, next))
    setOpen(false)
  }

  // Esc로 닫기
  useEffect(() => {
    if (!open) return undefined
    const onKey = (event) => {
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  return (
    <div className="onboarding-field" data-onboarding-target={targetName}>
      <span>{label}</span>
      <div className="onboarding-address-control">
        <button
          type="button"
          className={value ? 'onboarding-address-trigger has-value' : 'onboarding-address-trigger'}
          onClick={openModal}
        >
          <Icon name="pin" size={16} />
          <span>{value || placeholder}</span>
          <i className="onboarding-address-trigger-action"><Icon name="chevron" size={15} /></i>
        </button>
        {value && (
          <button
            type="button"
            className="onboarding-address-clear"
            onClick={() => onChange('')}
            aria-label={`${label} 지우기`}
          >
            <Icon name="plus" size={14} style={{ transform: 'rotate(45deg)' }} />
          </button>
        )}
      </div>

      {open && createPortal(
        <div
          className="onboarding-modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeModal()
          }}
        >
          <div className="onboarding-modal address-modal" role="dialog" aria-modal="true">
            <button type="button" className="onboarding-modal-close" onClick={closeModal} aria-label="닫기">
              <Icon name="plus" size={18} style={{ transform: 'rotate(45deg)' }} />
            </button>
            <div className="onboarding-modal-head">
              <h2>{label} 선택</h2>
              <p>시/도 → 시·군·구 → 읍·면·동 순서로 골라주세요. 동 단위까지만 저장됩니다.</p>
            </div>

            {!regions ? (
              <p className="region-loading">지역 정보를 불러오는 중…</p>
            ) : (
              <div className="region-selects">
                <label className="region-select">
                  <span>시 / 도</span>
                  <select value={sido} onChange={(event) => onSido(event.target.value)}>
                    <option value="" disabled>선택</option>
                    {sidoList.map((name) => <option key={name} value={name}>{name}</option>)}
                  </select>
                </label>
                <label className="region-select">
                  <span>시 · 군 · 구</span>
                  <select
                    value={sigungu}
                    onChange={(event) => setSigungu(event.target.value)}
                    disabled={!sido}
                  >
                    <option value="" disabled>선택</option>
                    {sigunguList.map((name) => <option key={name} value={name}>{name}</option>)}
                  </select>
                </label>
                <label className="region-select">
                  <span>읍 · 면 · 동</span>
                  <select
                    value=""
                    onChange={(event) => onDong(event.target.value)}
                    disabled={!sigungu}
                  >
                    <option value="" disabled>선택</option>
                    {sigungu && <option value={ALL_DONG}>{sigungu} 전체</option>}
                    {dongList.map((name) => <option key={name} value={name}>{name}</option>)}
                  </select>
                </label>
              </div>
            )}
          </div>
        </div>,
        document.body,
      )}
    </div>
  )
}

// ===== 초기 예산 (만원 단위 + 빠른 선택) =====
const BUDGET_PRESETS = [100, 300, 500, 1000, 3000]

export const BudgetField = ({ targetName, label, name, value, onChange }) => {
  const manwon = Number(value) || 0
  const won = manwon * 10000

  return (
    <label className="onboarding-field wide-field" data-onboarding-target={targetName}>
      <span className="onboarding-budget-head">
        {label}
        {manwon > 0 && (
          <button type="button" className="onboarding-budget-reset" onClick={() => onChange('')}>
            초기화
          </button>
        )}
      </span>
      <div className="onboarding-budget">
        <div className="onboarding-budget-input">
          <input
            name={name}
            type="number"
            min="0"
            max="100000"
            step="10"
            inputMode="numeric"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="예: 300"
          />
          <span className="onboarding-budget-unit">만원</span>
        </div>
        <div className="onboarding-budget-hint">= {won.toLocaleString('ko-KR')}원</div>
        <div className="onboarding-budget-presets">
          {BUDGET_PRESETS.map((preset) => (
            <button
              type="button"
              key={preset}
              onClick={() => onChange(String(manwon + preset))}
            >
              +{preset.toLocaleString('ko-KR')}만원
            </button>
          ))}
        </div>
      </div>
    </label>
  )
}
