const API_BASE = import.meta.env.VITE_API_BASE?.replace(/\/$/, '') ?? ''
export const CHAT_USER_ID = Number(import.meta.env.VITE_CHAT_USER_ID ?? 1)

const buildUrl = (path) => `${API_BASE}${path}`

export const getFreeChatRoom = async (userId = CHAT_USER_ID) => {
  const response = await fetch(buildUrl(`/api/chat/free-room?userId=${userId}`))
  if (!response.ok) throw new Error('자유 상담실 정보를 불러오지 못했습니다.')
  return response.json()
}

export const getFreeChatRooms = async (userId = CHAT_USER_ID) => {
  const response = await fetch(buildUrl(`/api/chat/free-rooms?userId=${userId}`))
  if (!response.ok) throw new Error('자유 상담실 목록을 불러오지 못했습니다.')
  return response.json()
}

export const getFeatureChatRoom = async (userId = CHAT_USER_ID, targetFeature) => {
  const response = await fetch(buildUrl(`/api/chat/feature-room?userId=${userId}&targetFeature=${encodeURIComponent(targetFeature)}`))
  if (!response.ok) throw new Error('기능 채팅 정보를 불러오지 못했습니다.')
  return response.json()
}

export const getFeatureChatRooms = async (userId = CHAT_USER_ID, targetFeature) => {
  const response = await fetch(buildUrl(`/api/chat/feature-rooms?userId=${userId}&targetFeature=${encodeURIComponent(targetFeature)}`))
  if (!response.ok) throw new Error('기능 채팅 세션 목록을 불러오지 못했습니다.')
  return response.json()
}

export const createFreeChatRoom = async (userId = CHAT_USER_ID) => {
  const response = await fetch(buildUrl('/api/chat/free-rooms'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ userId }),
  })

  if (!response.ok) throw new Error('새 자유 상담실을 만들지 못했습니다.')
  return response.json()
}

export const createFeatureChatRoom = async (userId = CHAT_USER_ID, targetFeature) => {
  const response = await fetch(buildUrl('/api/chat/feature-rooms'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ userId, targetFeature }),
  })

  if (!response.ok) throw new Error('새 기능 채팅 세션을 만들지 못했습니다.')
  return response.json()
}

export const updateFreeChatRoomTitle = async (roomId, userId, title) => {
  const response = await fetch(buildUrl(`/api/chat/free-rooms/${roomId}`), {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ userId, title }),
  })

  if (!response.ok) throw new Error('세션 이름을 수정하지 못했습니다.')
  return response.json()
}

export const updateFeatureChatRoomTitle = async (roomId, userId, targetFeature, title) => {
  const response = await fetch(buildUrl(`/api/chat/feature-rooms/${roomId}`), {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ userId, targetFeature, title }),
  })

  if (!response.ok) throw new Error('세션 이름을 수정하지 못했습니다.')
  return response.json()
}

export const getChatMessages = async (roomId, userId = CHAT_USER_ID) => {
  const response = await fetch(buildUrl(`/api/chat/rooms/${roomId}/messages?userId=${userId}`))
  if (!response.ok) throw new Error('이전 대화를 불러오지 못했습니다.')
  return response.json()
}

export const sendChatMessage = async (roomId, body) => {
  const response = await fetch(buildUrl(`/api/chat/rooms/${roomId}/messages`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) throw new Error('메시지를 전송하지 못했습니다.')
  return response.json()
}

export const createChatEventSource = (roomId, userId = CHAT_USER_ID) =>
  new EventSource(buildUrl(`/api/chat/rooms/${roomId}/stream?userId=${userId}`))
