// 카카오 지도 SDK 로더 (services 라이브러리 포함 — geocoder/places 주소 검색용).
// RoadviewPicker와 동일한 JavaScript 키를 재사용합니다.
const KAKAO_APP_KEY = import.meta.env.VITE_KAKAO_MAP_KEY || '2acaefd1805b94c10aa12a18f7680cbe'
const KAKAO_SCRIPT_ID = 'kakao-map-script'

let loaderPromise = null

export const loadKakaoMaps = () => {
  if (loaderPromise) {
    return loaderPromise
  }

  loaderPromise = new Promise((resolve, reject) => {
    if (window.kakao?.maps?.services) {
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

    if (window.kakao?.maps) {
      onReady()
    } else {
      script.addEventListener('load', onReady, { once: true })
      script.addEventListener('error', reject, { once: true })
    }
  })

  return loaderPromise
}
