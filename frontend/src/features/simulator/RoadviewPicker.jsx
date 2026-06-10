import { useCallback, useEffect, useRef, useState } from 'react'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'

const KAKAO_APP_KEY = import.meta.env.VITE_KAKAO_MAP_KEY || '2acaefd1805b94c10aa12a18f7680cbe'
const KAKAO_SCRIPT_ID = 'kakao-map-script'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

let kakaoLoaderPromise = null

const loadKakao = () => {
  if (kakaoLoaderPromise) return kakaoLoaderPromise

  kakaoLoaderPromise = new Promise((resolve, reject) => {
    if (window.kakao?.maps?.Map) {
      resolve()
      return
    }

    let script = document.getElementById(KAKAO_SCRIPT_ID)
    if (!script) {
      script = document.createElement('script')
      script.id = KAKAO_SCRIPT_ID
      script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_APP_KEY}&libraries=services&autoload=false`
      document.head.appendChild(script)
    }

    const onReady = () => window.kakao.maps.load(() => resolve())

    if (window.kakao?.maps) onReady()
    else {
      script.addEventListener('load', onReady, { once: true })
      script.addEventListener('error', reject, { once: true })
    }
  })

  return kakaoLoaderPromise
}

const formatNumber = (value) => Number(value || 0).toLocaleString('ko-KR')
const onlyDigits = (value) => value.replace(/[^\d]/g, '')

const buildRentQuery = ({ address, addressParts, areaM2 }) => {
  const params = new URLSearchParams()
  if (addressParts.sido) params.set('sido', addressParts.sido)
  if (addressParts.sigungu) params.set('sigungu', addressParts.sigungu)
  if (addressParts.dong) params.set('dong', addressParts.dong)
  if (address) params.set('address', address)
  if (areaM2) params.set('areaM2', String(areaM2))
  params.set('commercialType', '소규모상가')
  return params.toString()
}

export const RoadviewPicker = ({ onSelect }) => {
  const mapRef = useRef(null)
  const rvRef = useRef(null)
  const mapObjectRef = useRef(null)
  const markerRef = useRef(null)
  const roadviewRef = useRef(null)
  const roadviewClientRef = useRef(null)
  const geocoderRef = useRef(null)
  const placesRef = useRef(null)
  const initializedRef = useRef(false)
  const [address, setAddress] = useState('')
  const [addressParts, setAddressParts] = useState({})
  const [position, setPosition] = useState(null)
  const [panoId, setPanoId] = useState(null)
  const [areaM2, setAreaM2] = useState(66)
  const [rent, setRent] = useState(2000000)
  const [rentEstimate, setRentEstimate] = useState(null)
  const [rentLoading, setRentLoading] = useState(false)
  const [mapError, setMapError] = useState('')
  const [rentError, setRentError] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searchMessage, setSearchMessage] = useState('')

  const updateLocation = useCallback((pos, nextAddress = '') => {
    const next = { lat: pos.getLat(), lng: pos.getLng() }
    setPosition(next)
    markerRef.current?.setPosition(pos)
    mapObjectRef.current?.setCenter(pos)

    roadviewClientRef.current?.getNearestPanoId(pos, 80, (id) => {
      setPanoId(id || null)
      if (id) roadviewRef.current?.setPanoId(id, pos)
    })

    geocoderRef.current?.coord2Address(pos.getLng(), pos.getLat(), (result, status) => {
      if (status === window.kakao.maps.services.Status.OK) {
        const primary = result[0].address
        const road = result[0].road_address?.address_name
        const jibun = primary?.address_name
        setAddress(nextAddress || road || jibun || '')
        setAddressParts({
          sido: primary?.region_1depth_name || '',
          sigungu: primary?.region_2depth_name || '',
          dong: primary?.region_3depth_name || '',
        })
      } else if (nextAddress) {
        setAddress(nextAddress)
      }
    })
  }, [])

  const initMap = useCallback(() => {
    const defaultPos = new window.kakao.maps.LatLng(35.1631, 129.1635)
    const map = new window.kakao.maps.Map(mapRef.current, { center: defaultPos, level: 3 })
    const roadview = new window.kakao.maps.Roadview(rvRef.current)
    const roadviewClient = new window.kakao.maps.RoadviewClient()
    const geocoder = new window.kakao.maps.services.Geocoder()
    const places = new window.kakao.maps.services.Places()
    const marker = new window.kakao.maps.Marker({ position: defaultPos, map })

    mapObjectRef.current = map
    markerRef.current = marker
    roadviewRef.current = roadview
    roadviewClientRef.current = roadviewClient
    geocoderRef.current = geocoder
    placesRef.current = places

    window.kakao.maps.event.addListener(roadview, 'init', () => roadview.relayout())
    updateLocation(defaultPos)
    window.kakao.maps.event.addListener(map, 'click', (event) => updateLocation(event.latLng))
  }, [updateLocation])

  useEffect(() => {
    let cancelled = false

    loadKakao()
      .then(() => {
        if (cancelled || initializedRef.current) return
        initializedRef.current = true
        initMap()
      })
      .catch(() => setMapError('카카오 지도 SDK를 불러오지 못했습니다. 앱 키와 도메인 설정을 확인해주세요.'))

    return () => {
      cancelled = true
    }
  }, [initMap])

  useEffect(() => {
    if (!address || !addressParts.sido) return

    const controller = new AbortController()
    const estimateRent = async () => {
      setRentLoading(true)
      setRentError('')
      try {
        const query = buildRentQuery({ address, addressParts, areaM2 })
        const response = await fetch(`${API_BASE_URL}/api/rent-references/estimate?${query}`, {
          credentials: 'include',
          signal: controller.signal,
        })
        if (!response.ok) throw new Error('rent estimate failed')
        const data = await response.json()
        setRentEstimate(data)
        if (data.estimatedMonthlyRent) setRent(data.estimatedMonthlyRent)
      } catch (error) {
        if (error.name !== 'AbortError') {
          setRentEstimate(null)
          setRentError('임대료 기준 데이터를 불러오지 못했어요. 수동 입력값으로 진행할 수 있습니다.')
        }
      } finally {
        setRentLoading(false)
      }
    }

    estimateRent()
    return () => controller.abort()
  }, [address, addressParts, areaM2])

  const moveToSearchResult = (item) => {
    const lat = Number(item.y)
    const lng = Number(item.x)
    if (!lat || !lng) return
    const pos = new window.kakao.maps.LatLng(lat, lng)
    setSearchResults([])
    setSearchMessage('')
    updateLocation(pos, item.road_address_name || item.address_name || item.place_name || '')
  }

  const searchAddress = (keyword) => new Promise((resolve) => {
    geocoderRef.current.addressSearch(keyword, (result, status) => {
      if (status === window.kakao.maps.services.Status.OK) resolve(result)
      else resolve([])
    })
  })

  const searchPlaces = (keyword) => new Promise((resolve) => {
    placesRef.current.keywordSearch(keyword, (result, status) => {
      if (status === window.kakao.maps.services.Status.OK) resolve(result)
      else resolve([])
    })
  })

  const handleSearch = async (event) => {
    event.preventDefault()
    const keyword = searchKeyword.trim()
    if (!keyword || !window.kakao?.maps || !geocoderRef.current || !placesRef.current) return

    setSearchMessage('검색 중입니다.')
    const addressMatches = await searchAddress(keyword)
    const placeMatches = addressMatches.length ? addressMatches : await searchPlaces(keyword)
    const normalized = placeMatches.slice(0, 5)

    if (!normalized.length) {
      setSearchResults([])
      setSearchMessage('검색 결과가 없습니다. 도로명, 지번, 상권명을 조금 더 자세히 입력해주세요.')
      return
    }

    setSearchResults(normalized)
    setSearchMessage('')
    moveToSearchResult(normalized[0])
  }

  const handleRentChange = (event) => {
    const digits = onlyDigits(event.target.value)
    setRent(digits ? Number(digits) : 0)
  }

  const selectLocation = () => {
    onSelect({
      address,
      addressParts,
      lat: position?.lat,
      lng: position?.lng,
      panoId,
      areaM2,
      rent,
      rentReference: rentEstimate,
      name: address ? address.split(' ').slice(-2).join(' ') : '선택한 상가',
    })
  }

  return (
    <section className="sim-step-panel step-in">
      <div className="sim-section-copy">
        <h2>지도에서 상가 위치 고르기</h2>
        <p>지도에서 직접 클릭하거나 주소와 상권명을 검색해서 후보 위치를 선택하세요. 면적을 바꾸면 예상 월세도 다시 계산됩니다.</p>
      </div>

      {mapError && <div className="sim-alert">{mapError}</div>}

      <form className="sim-map-search" onSubmit={handleSearch}>
        <input
          value={searchKeyword}
          onChange={(event) => setSearchKeyword(event.target.value)}
          placeholder="주소, 지번, 상권명 검색"
        />
        <button type="submit">검색</button>
        {searchMessage && <span>{searchMessage}</span>}
      </form>
      {searchResults.length > 1 && (
        <div className="sim-search-results">
          {searchResults.map((item) => (
            <button type="button" key={`${item.x}-${item.y}-${item.address_name}`} onClick={() => moveToSearchResult(item)}>
              <b>{item.place_name || item.address_name}</b>
              <span>{item.road_address_name || item.address_name}</span>
            </button>
          ))}
        </div>
      )}

      <div className="sim-map-grid">
        <Card className="sim-map-card">
          <div className="sim-map-toolbar">
            <b>지도</b>
            <span>클릭해서 위치 선택</span>
          </div>
          <div ref={mapRef} className="sim-kakao-map" />
        </Card>
        <Card className="sim-map-card sim-roadview-card">
          <div className="sim-map-toolbar">
            <b>로드뷰</b>
            <span>{panoId ? '로드뷰 사용 가능' : '로드뷰 없는 위치'}</span>
          </div>
          <div ref={rvRef} className="sim-kakao-roadview" />
          {!panoId && <div className="sim-roadview-empty">근처에 로드뷰가 없어요. 다른 위치를 선택해보세요.</div>}
        </Card>
      </div>

      <Card className="sim-location-bar">
        <div className="sim-location-icon"><Icon name="pin" size={20} /></div>
        <div className="sim-location-text">
          <div>
            <b>{address || '위치를 선택해주세요'}</b>
            <span>{rentLoading ? '지역 평균 월세 계산 중' : rentError || '지역 평균 월세 자동 반영'}</span>
          </div>
        </div>
        <label className="sim-rent-input compact">
          <span>면적</span>
          <input type="number" value={areaM2} min="1" onChange={(event) => setAreaM2(Number(event.target.value))} />
          <em>m²</em>
        </label>
        <label className="sim-rent-input">
          <span>예상 월세</span>
          <input inputMode="numeric" value={formatNumber(rent)} onChange={handleRentChange} />
          <em>원</em>
        </label>
        <button className="sim-primary-btn sim-location-submit" onClick={selectLocation} disabled={!position}>
          이 위치로 시뮬레이션 시작 <Icon name="arrow" size={17} />
        </button>
      </Card>
    </section>
  )
}
