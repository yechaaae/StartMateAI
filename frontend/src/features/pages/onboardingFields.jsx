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

// ===== 지역 선택 (시·도 | 시·구·군 | 동·읍·면 3단 컬럼 + 검색) =====
// 행정구역 데이터는 모달을 처음 열 때 동적 import로 lazy-load 한다(약 66KB).
// 세부 주소·건물은 다루지 않고 "동" 단위 지역까지만 저장한다.
let regionsCache = null
const loadRegions = async () => {
  if (!regionsCache) {
    regionsCache = (await import('../../shared/data/regions.json')).default
  }
  return regionsCache
}

// 시·도 표시·저장용 짧은 이름 (예: 서울특별시 → 서울)
const SIDO_SHORT = {
  서울특별시: '서울', 부산광역시: '부산', 대구광역시: '대구', 인천광역시: '인천',
  광주광역시: '광주', 대전광역시: '대전', 울산광역시: '울산', 세종특별자치시: '세종',
  경기도: '경기', 충청북도: '충북', 충청남도: '충남', 전라북도: '전북', 전라남도: '전남',
  경상북도: '경북', 경상남도: '경남', 제주특별자치도: '제주', 강원특별자치도: '강원',
}
const shortSido = (full) => SIDO_SHORT[full] || full

// 저장 문자열은 "짧은시도 시군구 동" 형태 (세종은 시·군·구 생략).
const joinRegion = (sidoFull, sigungu, dong) => (
  [shortSido(sidoFull), sigungu && sigungu !== sidoFull ? sigungu : '', dong].filter(Boolean).join(' ')
)

// 저장된 문자열을 분해해 모달을 열 때 컬럼 선택을 복원한다(best-effort).
const parseRegionValue = (value, regions) => {
  if (!value || !regions) return { sido: '', sigungu: '' }
  const tokens = value.trim().split(/\s+/)
  const sido = Object.keys(regions).find((full) => shortSido(full) === tokens[0])
  if (!sido) return { sido: '', sigungu: '' }
  const keys = Object.keys(regions[sido])
  let sigungu = ''
  if (tokens.length >= 2) {
    if (keys.includes(tokens[1])) sigungu = tokens[1]
    else if (keys.length === 1) sigungu = keys[0] // 세종
  }
  return { sido, sigungu }
}

// 검색: "시 구 동" 라벨에 검색어(공백 무시)가 포함되는 후보를 최대 60개까지 모은다.
const searchRegions = (regions, query) => {
  const q = query.replace(/\s+/g, '')
  if (!q) return []
  const out = []
  for (const sidoFull of Object.keys(regions)) {
    const ss = shortSido(sidoFull)
    for (const sg of Object.keys(regions[sidoFull])) {
      const sgName = sg !== sidoFull ? sg : ''
      for (const dong of regions[sidoFull][sg]) {
        const itemLabel = [ss, sgName, dong].filter(Boolean).join(' ')
        if (itemLabel.replace(/\s+/g, '').includes(q)) {
          out.push(itemLabel)
          if (out.length >= 60) return out
        }
      }
    }
  }
  return out
}

export const AddressField = ({ targetName, label, value, onChange, placeholder }) => {
  const [open, setOpen] = useState(false)
  const [regions, setRegions] = useState(regionsCache)
  const [sido, setSido] = useState('')
  const [sigungu, setSigungu] = useState('')
  const [query, setQuery] = useState('')

  const openModal = async () => {
    setOpen(true)
    setQuery('')
    const data = regions || (await loadRegions())
    if (!regions) setRegions(data)
    const parsed = parseRegionValue(value, data)
    setSido(parsed.sido)
    setSigungu(parsed.sigungu)
  }

  const closeModal = () => setOpen(false)

  const commit = (next) => {
    onChange(next)
    setOpen(false)
  }

  const pickSido = (full) => {
    setSido(full)
    // 세종처럼 시·군·구가 1개(시·도와 동일)뿐이면 자동 선택해 동 컬럼을 바로 채운다.
    const keys = Object.keys(regions[full])
    setSigungu(keys.length === 1 ? keys[0] : '')
  }

  const resetSelection = () => {
    setSido('')
    setSigungu('')
    setQuery('')
  }

  const sidoList = regions ? Object.keys(regions) : []
  const sigunguList = regions && sido ? Object.keys(regions[sido]).filter((sg) => sg !== sido) : []
  const dongList = regions && sido && sigungu ? regions[sido][sigungu] : []
  const results = regions ? searchRegions(regions, query) : []
  const dongAllLabel = sigungu && sigungu !== sido ? sigungu : shortSido(sido)

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
              <p>지역을 클릭해 고르거나 위에서 검색하세요. 동 단위까지만 저장됩니다.</p>
            </div>

            {!regions ? (
              <p className="region-loading">지역 정보를 불러오는 중…</p>
            ) : (
              <>
                <div className="region-search">
                  <Icon name="compass" size={16} />
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="지역명 검색 (예: 해운대구, 우동)"
                  />
                </div>

                {query.trim() ? (
                  <div className="region-results">
                    {results.length === 0 ? (
                      <p className="region-results-empty">검색 결과가 없어요.</p>
                    ) : (
                      results.map((item) => (
                        <button type="button" key={item} className="region-result" onClick={() => commit(item)}>
                          {item}
                        </button>
                      ))
                    )}
                  </div>
                ) : (
                  <div className="region-columns">
                    <div className="region-col">
                      <div className="region-col-head">시·도</div>
                      <div className="region-col-list">
                        {sidoList.map((full) => (
                          <button
                            type="button"
                            key={full}
                            className={sido === full ? 'region-col-item on' : 'region-col-item'}
                            onClick={() => pickSido(full)}
                          >
                            {shortSido(full)}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="region-col">
                      <div className="region-col-head">시·구·군</div>
                      <div className="region-col-list">
                        {sido ? (
                          <>
                            <button type="button" className="region-col-item" onClick={() => commit(shortSido(sido))}>
                              {shortSido(sido)} 전체
                            </button>
                            {sigunguList.map((sg) => (
                              <button
                                type="button"
                                key={sg}
                                className={sigungu === sg ? 'region-col-item on' : 'region-col-item'}
                                onClick={() => setSigungu(sg)}
                              >
                                {sg}
                              </button>
                            ))}
                          </>
                        ) : (
                          <p className="region-col-empty">시·도를 먼저 선택하세요</p>
                        )}
                      </div>
                    </div>

                    <div className="region-col region-col-dong">
                      <div className="region-col-head">동·읍·면</div>
                      <div className="region-col-list">
                        {sigungu ? (
                          <>
                            <button type="button" className="region-col-item" onClick={() => commit(joinRegion(sido, sigungu, ''))}>
                              {dongAllLabel} 전체
                            </button>
                            {dongList.map((dong) => (
                              <button type="button" key={dong} className="region-col-item" onClick={() => commit(joinRegion(sido, sigungu, dong))}>
                                {dong}
                              </button>
                            ))}
                          </>
                        ) : (
                          <p className="region-col-empty">시·구·군을 먼저 선택하세요</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                <div className="region-modal-foot">
                  <button type="button" className="region-modal-reset" onClick={resetSelection}>
                    초기화
                  </button>
                </div>
              </>
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
