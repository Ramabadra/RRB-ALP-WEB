# RRB ALP Mock Test Platform — Backend

Python · FastAPI · PostgreSQL (Supabase) · Deployed on Render

This is the **backend-only** service for the RRB ALP preparation platform.  
The frontend is a separate Next.js project that consumes this REST API.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (Python 3.12) |
| ORM | SQLAlchemy 2 (async) |
| Database | PostgreSQL via Supabase |
| Migrations | Alembic |
| Auth | Google OAuth 2.0 + JWT |
| Storage | Supabase Storage (S3-compatible) |
| PDF Processing | pdfplumber + pytesseract (OCR) |
| AI | Google Gemini 2.0 Flash |
| Background Jobs | Celery + Redis |
| Deployment | Render |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory + router registration
│   ├── core/
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── security.py          # JWT creation/verification
│   │   └── dependencies.py      # FastAPI dependency injectors
│   ├── api/                     # Route handlers (11 modules)
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── subjects.py
│   │   ├── topics.py
│   │   ├── questions.py
│   │   ├── mock_tests.py
│   │   ├── attempts.py
│   │   ├── results.py
│   │   ├── analytics.py
│   │   ├── mistakes.py
│   │   └── pdfs.py
│   ├── models/                  # SQLAlchemy ORM models (13 tables)
│   ├── schemas/                 # Pydantic v2 request/response schemas
│   ├── repositories/            # DB query layer (Phase 2+)
│   ├── services/                # Business logic layer (Phase 2+)
│   ├── auth/                    # Google OAuth implementation (Phase 2)
│   ├── pdf/                     # PDF extraction pipeline (Phase 5)
│   ├── ai/                      # AI service layer (Phase 6)
│   ├── exam/                    # Exam engine + scoring (Phase 4)
│   ├── workers/                 # Celery background tasks (Phase 5)
│   └── database/                # Engine + session factory
├── migrations/                  # Alembic migration files
│   ├── env.py
│   └── versions/
├── scripts/
│   └── seed.py                  # Idempotent DB seeder
├── tests/                       # pytest test suite
├── requirements.txt
├── alembic.ini
├── pyproject.toml               # pytest configuration
├── Dockerfile
├── .env.example
└── API_CONTRACT.md              # Complete API documentation
```

---

## Local Development Setup

### Prerequisites
- Python 3.12+
- PostgreSQL (or Supabase project)
- Redis (for Celery — Phase 5+)

### 1. Clone and set up environment

```bash
cd backend/

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your real values
```

Required variables (minimum to start):
```
DATABASE_URL=postgresql+asyncpg://postgres.xxxx:password@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
SECRET_KEY=<generate a 64-char random string>
FRONTEND_URL=http://localhost:3000
AI_API_KEY=<from Google AI Studio>
AI_MODEL=gemini-1.5-flash
```

### 3. Google OAuth 2.0 Configuration

The backend uses a **server-side redirect flow** for OAuth.

To configure this in Google Cloud Console (`APIs & Services` -> `Credentials` -> `OAuth 2.0 Client IDs`):

1. Set **Authorized JavaScript origins** to your `FRONTEND_URL` exactly.
   * Example (local): `http://localhost:3000`
   * Example (prod): `https://rrb-alp-prep.vercel.app`
2. Set **Authorized redirect URIs** to your backend's URL + `/api/auth/google/callback`.
   * Example (local): `http://localhost:8000/api/auth/google/callback`
   * Example (prod): `https://api.rrb-alp-prep.com/api/auth/google/callback`

Then add the credentials to `.env`:
```
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
```

### 4. Run database migrations

```bash
# Generate migration from current models (first time)
alembic revision --autogenerate -m "initial_schema"

# Apply migrations
alembic upgrade head
```

### 5. Seed subjects and topics

```bash
python -m scripts.seed
```

### 6. Start the development server

```bash
uvicorn app.main:app --reload --port 8000
```

Visit:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

---

## Database Migration Commands

```bash
# Create a new migration (after model changes)
alembic revision --autogenerate -m "describe_what_changed"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# View migration history
alembic history

# Check current revision
alembic current
```

---

## Running Tests

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_schemas.py -v

# Run Phase 1 tests only
pytest tests/test_health.py tests/test_schemas.py tests/test_config.py -v
```

---

## Render Deployment

### Environment Variables (set in Render dashboard)

```
DATABASE_URL=postgresql+asyncpg://...supabase.com.../postgres
SECRET_KEY=<production secret>
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
AI_API_KEY=...
FRONTEND_URL=https://your-frontend.vercel.app
STORAGE_ENDPOINT=https://xxxx.supabase.co/storage/v1/s3
STORAGE_ACCESS_KEY=...
STORAGE_SECRET_KEY=...
STORAGE_BUCKET=rrb-alp-pdfs
ENVIRONMENT=production
```

### Render Service Settings

| Setting | Value |
|---------|-------|
| Runtime | Docker |
| Dockerfile path | `backend/Dockerfile` |
| Health check path | `/health` |
| Start command | (defined in Dockerfile CMD) |

### Google OAuth Callback URL

In Google Cloud Console → Credentials → OAuth 2.0 Client:  
Add to **Authorized redirect URIs**:
```
https://your-backend.onrender.com/api/auth/google/callback
```

---

## API Overview

See [`API_CONTRACT.md`](./API_CONTRACT.md) for the complete endpoint reference.

| Group | Description | Phase |
|-------|-------------|-------|
| `GET /health` | Health check | 1 ✅ |
| `/api/auth` | Google OAuth + JWT | 2 |
| `/api/users` | User profile | 2 |
| `/api/subjects` | Subject list | 2 |
| `/api/topics` | Topic list | 2 |
| `/api/questions` | Question bank CRUD | 3 |
| `/api/mock-tests` | Test generation | 3 |
| `/api/attempts` | Exam sessions | 4 |
| `/api/results` | Scoring + results | 4 |
| `/api/pdfs` | PDF upload + processing | 5 |
| `/api/analytics` | Performance analytics | 7 |
| `/api/mistakes` | Mistake book | 7 |

---

## Development Phases

| Phase | Contents | Status |
|-------|----------|--------|
| 1 | Architecture · Database · API Contract | ✅ Done |
| 2 | Google Auth · Users · Subjects · Topics | ✅ Done |
| 3 | Question Bank · Mock Test Generation | ✅ Done |
| 4 | Attempts · Timer · Submission · Scoring | ✅ Done |
| 5 | PDF Upload · Storage · OCR · Parser | ⏳ Next |
| 6 | AI Validation · Classification · Generation | — |
| 7 | Analytics · Mistake Book · Security · Testing | — |

---

## Security Notes

- JWT tokens signed with `SECRET_KEY` — never expose this value
- Google passwords are **never** stored
- CORS is restricted to origins in `FRONTEND_URL` — no wildcard `*` in production
- PDF files are never stored in PostgreSQL
- SQL injection prevented by SQLAlchemy parameterized queries
- Stack traces never exposed in API error responses
- All secrets loaded from environment variables only
