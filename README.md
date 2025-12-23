# Inbox Copilot V1

Personal email assistant with AI-powered classification, daily recaps, and smart actions.

## Quick Start

### Backend
```bash
cd backend
python3 -m uvicorn backend.main:app --reload --port 8000
```

### Frontend
```bash
npm install
npm run dev
# Or if .next cache issues:
npm run dev:clean
```

Access: http://localhost:3000

## Key API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/today` | GET | Today's prioritized emails |
| `/api/recap/auto` | GET | Auto morning/evening recap |
| `/api/recap/morning` | GET | Morning recap |
| `/api/recap/evening` | GET | Evening recap |
| `/api/recaps/history` | GET | Recap history |
| `/api/memory/vips` | GET/POST/DELETE | VIP contacts management |
| `/api/settings/silence` | GET/POST | Silence mode settings |
| `/api/threads/{id}/status` | POST | Mark thread DONE/WAITING |

## Features Checklist

- [x] Mode Silence (MoonStar icon) - toggle in header
- [x] Search results as clickable cards
- [x] EmailDrawer for quick email actions
- [x] Mark DONE refreshes Aujourd'hui view
- [x] VIP badges on related email cards

## Troubleshooting

**CSS/styles not loading or webpack errors:**
```bash
npm run dev:clean
```

**Backend connection issues:**
```bash
# Check backend health
curl http://localhost:8000/api/health
```

## Environment Variables

Copy `.env.example` to `.env` and configure:
- `MONGODB_URI` - MongoDB connection string
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - Gmail OAuth
- `NEXT_PUBLIC_API_URL` - Backend URL (default: http://localhost:8000)
