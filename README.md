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

Build and run services with MySQL:

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost`
- Backend: `http://localhost:8080`
- MySQL: `localhost:3306` (`startmate` / `startmate`)

## Hackathon Data MVP APIs

- `POST /api/seeds/import`: demo seed data import
- `POST /api/support-programs/sync?source=all`: K-Startup / Bizinfo / YouthCenter sync, with demo fallback
- `POST /api/support-programs/recommend`: profile-based support program recommendation
- `POST /api/stores/import-csv`: SBIZ store CSV import, with demo fallback when `filePath` is blank
- `POST /api/commercial-areas/analyze`: area and industry competitor count
