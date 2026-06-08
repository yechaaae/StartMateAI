# StartMateAI
SSAFY X Kakao Tech Bootcamp AI Hackathon 소상공인 AI 창업·경영 컨설턴트 주제

## Project Structure

- `backend/`: backend source
- `frontend/`: Vite + React frontend app

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Production build:

```bash
cd frontend
npm run build
```

## Docker Compose

Build and run both services:

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost`
- Backend: `http://localhost:8080`
