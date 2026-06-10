import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 카카오 콘솔에 등록한 도메인(http://localhost:5173)과 항상 일치시키기 위해 포트 고정.
    // strictPort: 5173이 사용 중이면 조용히 다른 포트로 바꾸지 않고 에러로 멈춤.
    port: 5173,
    strictPort: true,
  },
})
