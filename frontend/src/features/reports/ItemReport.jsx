import { useEffect, useRef, useState } from 'react'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'

const KAKAO_APP_KEY = import.meta.env.VITE_KAKAO_MAP_KEY || '2acaefd1805b94c10aa12a18f7680cbe'
const KAKAO_SCRIPT_ID = 'kakao-map-script'
const DEFAULT_POSITION = { lat: 35.1631, lng: 129.1635 }

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

const RegionMap = ({ location, analysis }) => {
  const mapRef = useRef(null)
  const initializedRef = useRef(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    loadKakao()
      .then(() => {
        if (cancelled || initializedRef.current) return
        initializedRef.current = true

        const fallback = new window.kakao.maps.LatLng(DEFAULT_POSITION.lat, DEFAULT_POSITION.lng)
        const map = new window.kakao.maps.Map(mapRef.current, {
          center: fallback,
          level: 4,
          draggable: false,
          scrollwheel: false,
          disableDoubleClickZoom: true,
        })
        const marker = new window.kakao.maps.Marker({ position: fallback, map })
        const geocoder = new window.kakao.maps.services.Geocoder()

        geocoder.addressSearch(location, (result, status) => {
          if (cancelled) return
          if (status === window.kakao.maps.services.Status.OK && result[0]) {
            const pos = new window.kakao.maps.LatLng(Number(result[0].y), Number(result[0].x))
            map.setCenter(pos)
            marker.setPosition(pos)
            window.setTimeout(() => map.relayout(), 0)
          }
        })
      })
      .catch(() => setError('카카오맵을 불러오지 못했습니다. 앱 키 설정을 확인해주세요.'))

    return () => {
      cancelled = true
    }
  }, [location])

  return (
    <div className="item-region-map">
      <div ref={mapRef} className="item-kakao-map" />
      <div className="item-map-overlay">
        <span><Icon name="pin" size={14} /> 창업 후보 지역</span>
        <b>{location}</b>
      </div>
      <div className="item-map-metrics">
        {analysis.slice(0, 2).map(([label, value]) => (
          <div key={label}>
            <small>{label}</small>
            <b>{value}</b>
          </div>
        ))}
      </div>
      {error && <div className="item-map-error">{error}</div>}
    </div>
  )
}

export const ItemReport = ({
  data,
  go,
  workspace,
  setWorkspace,
  selectedIdeaRank,
  onSelectIdea,
}) => {
  const selectIdea = (item) => {
    onSelectIdea?.(item.rank)
    setWorkspace?.({
      ...workspace,
      selectedIdea: {
        id: item.rank,
        rank: item.rank,
        title: item.title,
        score: item.score,
        reason: item.reason,
        category: item.category || '추천 아이템',
        estimatedInitialCost: item.estimatedInitialCost,
      },
    })
    go('simulator')
  }

  return (
    <div className="report-stack">
      <Card className="item-region-card">
        <RegionMap location={data.location} analysis={data.analysis} />
        <h3>{data.location} 상권 분석</h3>
        <div className="metric-grid">
          {data.analysis.map(([label, value]) => (
            <div key={label}>
              <small>{label}</small>
              <b>{value}</b>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h3>상권 + 내 프로필 기반 추천</h3>
        {data.items.map((item) => {
          const selected = selectedIdeaRank === item.rank
          return (
            <div className={selected ? 'idea-option selectable selected' : 'idea-option selectable'} key={item.rank}>
              <span>{item.rank}</span>
              <div>
                <b>{item.title}</b>
                <p>{item.reason}</p>
              </div>
              <em>적합도 {item.score}</em>
              <button
                type="button"
                onClick={() => selectIdea(item)}
              >
                시뮬레이터 <Icon name="arrow" size={15} />
              </button>
            </div>
          )
        })}
      </Card>
    </div>
  )
}
