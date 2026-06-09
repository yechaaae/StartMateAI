const API_BASE = import.meta.env.VITE_API_BASE?.replace(/\/$/, '') ?? ''
export const CHAT_USER_ID = Number(import.meta.env.VITE_CHAT_USER_ID ?? 1)

const buildUrl = (path) => `${API_BASE}${path}`

export const getFreeChatRoom = async (userId = CHAT_USER_ID) => {
  const response = await fetch(buildUrl(`/api/chat/free-room?userId=${userId}`))
  if (!response.ok) throw new Error('자유 상담실 정보를 불러오지 못했습니다.')
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
