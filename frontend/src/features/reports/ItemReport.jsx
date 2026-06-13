import { useEffect, useMemo, useRef, useState } from 'react'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'
import { loadKakaoMaps } from '../../shared/lib/kakaoMaps'
import { AgentReview } from './AgentReview'

const DEFAULT_POSITION = { lat: 35.1631, lng: 129.1635 }

// 지도는 한 번만 생성하고, location이 바뀔 때마다 재지오코딩해서 중심/마커를 옮긴다.
// (선택한 아이템이 바뀌면 상위에서 location을 바꿔 호출하므로 지도가 함께 이동한다.)
const RegionMap = ({ location, analysis }) => {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const markerRef = useRef(null)
  const geocoderRef = useRef(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    loadKakaoMaps()
      .then(() => {
        if (cancelled) return

        if (!mapInstanceRef.current) {
          const fallback = new window.kakao.maps.LatLng(DEFAULT_POSITION.lat, DEFAULT_POSITION.lng)
          mapInstanceRef.current = new window.kakao.maps.Map(mapRef.current, {
            center: fallback,
            level: 4,
            draggable: false,
            scrollwheel: false,
            disableDoubleClickZoom: true,
          })
          markerRef.current = new window.kakao.maps.Marker({ position: fallback, map: mapInstanceRef.current })
          geocoderRef.current = new window.kakao.maps.services.Geocoder()
        }

        if (!location) return

        geocoderRef.current.addressSearch(location, (result, status) => {
          if (cancelled) return
          if (status === window.kakao.maps.services.Status.OK && result[0]) {
            const pos = new window.kakao.maps.LatLng(Number(result[0].y), Number(result[0].x))
            mapInstanceRef.current.setCenter(pos)
            markerRef.current.setPosition(pos)
            window.setTimeout(() => mapInstanceRef.current.relayout(), 0)
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
        {(analysis ?? []).slice(0, 2).map(([label, value]) => (
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
  onCreateWorkspace,
  selectedIdeaRank,
  onSelectIdea,
}) => {
  const items = data.items ?? []

  // 선택된 아이템(없으면 첫 번째). 이 아이템의 location/analysis로 지도와 상권 지표를 보여준다.
  const selectedItem = useMemo(() => {
    const list = data.items ?? []
    return list.find((item) => item.rank === selectedIdeaRank) ?? list[0] ?? null
  }, [data.items, selectedIdeaRank])

  const mapLocation = selectedItem?.location ?? data.location
  const mapAnalysis = selectedItem?.analysis ?? data.analysis ?? []

  // 행을 누르면 그 아이템을 선택만 한다(지도/상권 지표가 바뀜). 워크스페이스 확정은 아래 버튼에서.
  const previewItem = (item) => {
    onSelectIdea?.(item.rank)
  }

  // '이 아이템으로 시작'을 누르면 그 아이템으로 새 워크스페이스를 만든다(워크스페이스 = 아이템).
  const confirmItem = (item) => {
    onSelectIdea?.(item.rank)
    onCreateWorkspace?.({
      rank: item.rank,
      title: item.title,
      score: item.score,
      reason: item.reason,
      category: item.category || '추천 아이템',
      location: item.location ?? data.location,
      estimatedInitialCost: item.estimatedInitialCost,
    })
  }

  return (
    <div className="report-stack">
      <AgentReview review={data.agentReview} />

      {mapLocation && (
        <Card className="item-region-card">
          <RegionMap location={mapLocation} analysis={mapAnalysis} />
          <h3>{mapLocation} 상권 분석</h3>
          <div className="metric-grid">
            {mapAnalysis.map(([label, value]) => (
              <div key={label}>
                <small>{label}</small>
                <b>{value}</b>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <h3>상권 + 내 프로필 기반 추천</h3>
        {items.length === 0 ? (
          <p className="item-list-hint">아직 추천 아이템이 없어요. AI가 리포트를 생성하면 후보가 채워집니다.</p>
        ) : (
          <>
            <p className="item-list-hint">아이템을 누르면 후보 상권과 지도가 함께 바뀌어요.</p>
            {items.map((item) => {
              const selected = selectedItem?.rank === item.rank
              return (
                <div
                  className={selected ? 'idea-option selectable selected' : 'idea-option selectable'}
                  key={item.rank}
                  onClick={() => previewItem(item)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      previewItem(item)
                    }
                  }}
                >
                  <span>{item.rank}</span>
                  <div>
                    <b>{item.title}</b>
                    <p>{item.reason}</p>
                    {item.location && <span className="idea-option-loc"><Icon name="pin" size={12} /> {item.location}</span>}
                  </div>
                  <em>적합도 {item.score}</em>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      confirmItem(item)
                    }}
                  >
                    이 아이템으로 시작 <Icon name="arrow" size={15} />
                  </button>
                </div>
              )
            })}
          </>
        )}
      </Card>
    </div>
  )
}
