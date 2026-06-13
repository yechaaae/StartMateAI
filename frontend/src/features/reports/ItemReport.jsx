import { useEffect, useRef, useState } from 'react'
import { Card } from '../../shared/components/Card'
import { Icon } from '../../shared/components/Icon'
import { workspaceApi } from '../../shared/api/client'
import { AgentReview } from './AgentReview'

const KAKAO_APP_KEY = import.meta.env.VITE_KAKAO_MAP_KEY ?? ''
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
    if (!KAKAO_APP_KEY) {
      reject(new Error('VITE_KAKAO_MAP_KEY is required.'))
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
  const [confirmingRank, setConfirmingRank] = useState(null)

  const ideaSnapshot = (item) => ({
    id: item.rank,
    rank: item.rank,
    title: item.title,
    score: item.score,
    reason: item.reason,
    category: item.category || '추천 아이템',
    estimatedInitialCost: item.estimatedInitialCost,
  })

  // 시뮬레이터에서 먼저 검증 (메모리 상태만 반영)
  const exploreInSimulator = (item) => {
    onSelectIdea?.(item.rank)
    setWorkspace?.({ ...workspace, selectedIdea: ideaSnapshot(item) })
    go('simulator')
  }

  // 이 아이템으로 확정 → 현재 워크스페이스를 그 아이템으로 만들고 홈으로
  const confirmIdea = async (item) => {
    if (confirmingRank) return
    onSelectIdea?.(item.rank)
    setConfirmingRank(item.rank)
    const selectedIdea = {
      title: item.title,
      category: item.category || '추천 아이템',
      score: item.score,
      reason: item.reason,
    }
    try {
      let target = workspace
      if (!target?.id) {
        const list = await workspaceApi.list()
        target = list[list.length - 1] ?? await workspaceApi.create({ title: item.title })
      }
      const updated = await workspaceApi.update(target.id, { title: item.title, selectedIdea })
      setWorkspace?.(updated)
      go?.('home')
    } catch {
      setWorkspace?.({ ...workspace, title: item.title, selectedIdeaTitle: item.title, selectedIdea: ideaSnapshot(item) })
      go?.('home')
    } finally {
      setConfirmingRank(null)
    }
  }

  return (
    <div className="report-stack">
      <AgentReview review={data.agentReview} />

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
              <div className="idea-actions">
                <button
                  type="button"
                  className="idea-confirm"
                  onClick={() => confirmIdea(item)}
                  disabled={confirmingRank === item.rank}
                >
                  {confirmingRank === item.rank ? '확정 중…' : '이 아이템으로 시작'}
                  {confirmingRank !== item.rank && <Icon name="check" size={15} />}
                </button>
                <button
                  type="button"
                  className="idea-sim"
                  onClick={() => exploreInSimulator(item)}
                >
                  시뮬레이터로 검증 <Icon name="arrow" size={14} />
                </button>
              </div>
            </div>
          )
        })}
      </Card>
    </div>
  )
}
