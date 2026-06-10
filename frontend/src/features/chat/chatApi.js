const API_BASE = import.meta.env.VITE_API_BASE?.replace(/\/$/, '') ?? ''

const buildUrl = (path) => `${API_BASE}${path}`

const fetchJson = (path, options = {}) => fetch(buildUrl(path), {
  credentials: 'include',
  ...options,
})

export const getFreeChatRoom = async () => {
  const response = await fetchJson('/api/chat/free-room')
  if (!response.ok) throw new Error('?먯쑀 ?곷떞???뺣낫瑜?遺덈윭?ㅼ? 紐삵뻽?듬땲??')
  return response.json()
}

export const getFreeChatRooms = async () => {
  const response = await fetchJson('/api/chat/free-rooms')
  if (!response.ok) throw new Error('?먯쑀 ?곷떞??紐⑸줉??遺덈윭?ㅼ? 紐삵뻽?듬땲??')
  return response.json()
}

export const getFeatureChatRoom = async (targetFeature) => {
  const response = await fetchJson(`/api/chat/feature-room?targetFeature=${encodeURIComponent(targetFeature)}`)
  if (!response.ok) throw new Error('湲곕뒫 梨꾪똿 ?뺣낫瑜?遺덈윭?ㅼ? 紐삵뻽?듬땲??')
  return response.json()
}

export const getFeatureChatRooms = async (targetFeature) => {
  const response = await fetchJson(`/api/chat/feature-rooms?targetFeature=${encodeURIComponent(targetFeature)}`)
  if (!response.ok) throw new Error('湲곕뒫 梨꾪똿 ?몄뀡 紐⑸줉??遺덈윭?ㅼ? 紐삵뻽?듬땲??')
  return response.json()
}

export const createFreeChatRoom = async () => {
  const response = await fetchJson('/api/chat/free-rooms', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({}),
  })

  if (!response.ok) throw new Error('???먯쑀 ?곷떞?ㅼ쓣 留뚮뱾吏 紐삵뻽?듬땲??')
  return response.json()
}

export const createFeatureChatRoom = async (targetFeature) => {
  const response = await fetchJson('/api/chat/feature-rooms', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ targetFeature }),
  })

  if (!response.ok) throw new Error('??湲곕뒫 梨꾪똿 ?몄뀡??留뚮뱾吏 紐삵뻽?듬땲??')
  return response.json()
}

export const updateFreeChatRoomTitle = async (roomId, title) => {
  const response = await fetchJson(`/api/chat/free-rooms/${roomId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  })

  if (!response.ok) throw new Error('?몄뀡 ?대쫫???섏젙?섏? 紐삵뻽?듬땲??')
  return response.json()
}

export const updateFeatureChatRoomTitle = async (roomId, targetFeature, title) => {
  const response = await fetchJson(`/api/chat/feature-rooms/${roomId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ targetFeature, title }),
  })

  if (!response.ok) throw new Error('?몄뀡 ?대쫫???섏젙?섏? 紐삵뻽?듬땲??')
  return response.json()
}

export const getChatMessages = async (roomId) => {
  const response = await fetchJson(`/api/chat/rooms/${roomId}/messages`)
  if (!response.ok) throw new Error('?댁쟾 ??붾? 遺덈윭?ㅼ? 紐삵뻽?듬땲??')
  return response.json()
}

export const sendChatMessage = async (roomId, body) => {
  const response = await fetchJson(`/api/chat/rooms/${roomId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) throw new Error('硫붿떆吏瑜??꾩넚?섏? 紐삵뻽?듬땲??')
  return response.json()
}

export const createChatEventSource = (roomId) =>
  new EventSource(buildUrl(`/api/chat/rooms/${roomId}/stream`), { withCredentials: true })
