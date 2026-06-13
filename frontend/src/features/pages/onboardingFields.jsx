import { useRef, useState } from 'react'
import { Icon } from '../../shared/components/Icon'
import { loadKakaoMaps } from '../../shared/lib/kakaoMaps'
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

// ===== 주소 검색 (카카오 지도 services — RoadviewPicker와 동일한 키) =====
export const AddressField = ({ targetName, label, name, value, onChange, placeholder }) => {
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState([])
  const [message, setMessage] = useState('')
  const servicesRef = useRef(null)

  const ensureServices = async () => {
    if (servicesRef.current) {
      return servicesRef.current
    }
    await loadKakaoMaps()
    servicesRef.current = {
      geocoder: new window.kakao.maps.services.Geocoder(),
      places: new window.kakao.maps.services.Places(),
      Status: window.kakao.maps.services.Status,
    }
    return servicesRef.current
  }

  const runSearch = async () => {
    const keyword = String(value ?? '').trim()
    if (!keyword || loading) {
      return
    }
    setLoading(true)
    setMessage('검색 중…')
    setResults([])
    try {
      const { geocoder, places, Status } = await ensureServices()
      const byAddress = await new Promise((resolve) => {
        geocoder.addressSearch(keyword, (result, status) => resolve(status === Status.OK ? result : []))
      })
      let items = byAddress.map((item) => ({
        label: item.address_name,
        sub: item.road_address?.address_name || '',
        value: item.address_name,
      }))
      if (!items.length) {
        const byPlace = await new Promise((resolve) => {
          places.keywordSearch(keyword, (result, status) => resolve(status === Status.OK ? result : []))
        })
        items = byPlace.map((item) => ({
          label: item.place_name,
          sub: item.road_address_name || item.address_name || '',
          value: item.road_address_name || item.address_name || item.place_name,
        }))
      }
      if (!items.length) {
        setMessage('검색 결과가 없어요. 직접 입력해도 됩니다.')
        return
      }
      setResults(items.slice(0, 6))
      setMessage('')
    } catch {
      setMessage('주소 검색을 불러오지 못했어요. 직접 입력해주세요.')
    } finally {
      setLoading(false)
    }
  }

  const pick = (item) => {
    onChange(item.value)
    setResults([])
    setMessage('')
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      runSearch()
    }
  }

  return (
    <label className="onboarding-field" data-onboarding-target={targetName}>
      <span>{label}</span>
      <div className="onboarding-address-field">
        <div className="onboarding-address">
          <input
            name={name}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
          />
          <button type="button" className="onboarding-address-search" onClick={runSearch} disabled={loading}>
            <Icon name="compass" size={15} /> 주소 검색
          </button>
        </div>
        {message && <p className="onboarding-address-message">{message}</p>}
        {results.length > 0 && (
          <div className="onboarding-address-results">
            {results.map((item) => (
              <button type="button" key={`${item.value}-${item.sub}`} onClick={() => pick(item)}>
                <b>{item.label}</b>
                {item.sub && <span>{item.sub}</span>}
              </button>
            ))}
          </div>
        )}
      </div>
    </label>
  )
}

// ===== 초기 예산 (만원 단위 + 빠른 선택) =====
const BUDGET_PRESETS = [100, 300, 500, 1000, 3000]

export const BudgetField = ({ targetName, label, name, value, onChange }) => {
  const manwon = Number(value) || 0
  const won = manwon * 10000

  return (
    <label className="onboarding-field wide-field" data-onboarding-target={targetName}>
      <span>{label}</span>
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
          {manwon > 0 && (
            <button type="button" className="onboarding-budget-reset" onClick={() => onChange('')}>
              초기화
            </button>
          )}
        </div>
      </div>
    </label>
  )
}
