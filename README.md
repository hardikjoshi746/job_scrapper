# JobHunt AI — AI-Powered Job Application Automation

A full-stack job hunt automation platform that helps you find jobs, tailor your resume with AI, track applications, and auto-fill ATS forms. Built with FastAPI + React.

**Live:** [job-scrapper-two.vercel.app](https://job-scrapper-two.vercel.app)

---

## Features

- **Job Search** — Search real job listings via Adzuna API with role + location filters
- **Application Tracker** — Track applications with statuses: saved → applied → interview → offer → rejected
- **AI Resume Tailoring** — Claude AI rewrites your resume bullets to match the job's exact keywords
- **ATS Score Evaluator** — OpenAI GPT scores your resume against the JD (0–100%) and identifies missing keywords
- **Agentic Refinement Loop** — Auto-regenerates the resume up to 3× until ATS score hits 95%+
- **Real-Time Progress** — Server-Sent Events stream live step updates (Generating → Evaluating → Refining)
- **Custom Job** — Paste any JD and get a tailored resume instantly without a saved application
- **Multi-Format Upload** — Accepts PDF and DOCX resumes
- **Cloud Storage** — AWS S3 for file storage in production (falls back to local disk in dev)
- **JWT Auth** — Secure email/password authentication with 30-day tokens

---

## Tech Stack

### Frontend

|                       |                                             |
| --------------------- | ------------------------------------------- |
| Framework             | React 19 + Vite                             |
| Routing               | React Router DOM v7                         |
| State / Data Fetching | TanStack Query (React Query)                |
| HTTP                  | Axios                                       |
| UI                    | Tailwind CSS, Lucide React, React Hot Toast |

### Backend

|            |                                                                              |
| ---------- | ---------------------------------------------------------------------------- |
| Framework  | FastAPI (async)                                                              |
| Server     | Uvicorn                                                                      |
| Database   | SQLAlchemy — SQLite (dev) / PostgreSQL (prod)                                |
| Auth       | JWT via python-jose, bcrypt via passlib                                      |
| AI         | Anthropic Claude Sonnet (resume generation), OpenAI GPT-5.5 (ATS evaluation) |
| PDF        | WeasyPrint (HTML → PDF), PyMuPDF + python-docx (text extraction)             |
| Storage    | AWS S3 via boto3                                                             |
| Automation | Playwright (local ATS auto-fill)                                             |

---

## Project Structure

```
app/
├── backend/
│   ├── main.py                  # FastAPI app, CORS, routers
│   ├── config.py                # Pydantic settings / env vars
│   ├── database.py              # SQLAlchemy engine + session
│   ├── models.py                # ORM: User, Application, BaseResume
│   ├── schemas.py               # Pydantic request/response models
│   ├── dependencies.py          # get_db(), get_current_user() (JWT)
│   ├── Dockerfile               # Production Docker image
│   ├── railway.toml             # Railway build config
│   ├── requirements.txt
│   ├── routers/
│   │   ├── auth.py              # Register, login, /me
│   │   ├── jobs.py              # Adzuna job search
│   │   ├── applications.py      # CRUD application tracker
│   │   ├── resume.py            # Upload, tailor, stream, download
│   │   └── apply.py             # Playwright auto-apply (local only)
│   └── services/
│       ├── claude.py            # Agentic resume tailoring loop
│       ├── jsearch.py           # Adzuna API client
│       ├── resume_parser.py     # PDF/DOCX text extraction
│       ├── pdf_generator.py     # HTML → PDF via WeasyPrint
│       ├── s3.py                # S3 upload + presigned URLs
│       └── playwright_apply.py  # Universal ATS form autofiller
│
└── frontend/
    ├── vercel.json              # SPA rewrite rules
    ├── vite.config.js           # Dev proxy /api → localhost:8000
    └── src/
        ├── App.jsx              # Router, auth guards, layout
        ├── api/client.js        # Axios instance + JWT interceptor
        ├── context/AuthContext.jsx
        ├── pages/
        │   ├── Login.jsx
        │   ├── Register.jsx
        │   ├── JobSearch.jsx
        │   ├── Applications.jsx
        │   ├── ResumeTailor.jsx
        │   └── CustomJob.jsx
        └── components/
            ├── Navbar.jsx
            ├── ATSResult.jsx       # Score ring + keyword badges
            ├── TailorProgress.jsx  # Animated SSE progress steps
            └── ApplyModal.jsx
```

---

## API Endpoints

### Auth — `/api/auth`

| Method | Path             | Description       |
| ------ | ---------------- | ----------------- |
| POST   | `/auth/register` | Create account    |
| POST   | `/auth/login`    | Login → JWT token |
| GET    | `/auth/me`       | Current user info |

### Jobs — `/api/jobs`

| Method | Path                                 | Description       |
| ------ | ------------------------------------ | ----------------- |
| GET    | `/jobs/search?role=&location=&page=` | Search via Adzuna |

### Applications — `/api/applications`

| Method | Path                 | Description           |
| ------ | -------------------- | --------------------- |
| GET    | `/applications`      | List all              |
| POST   | `/applications`      | Create                |
| GET    | `/applications/{id}` | Get one               |
| PATCH  | `/applications/{id}` | Update status / notes |
| DELETE | `/applications/{id}` | Delete                |

### Resume — `/api/resume`

| Method | Path                    | Description                     |
| ------ | ----------------------- | ------------------------------- |
| POST   | `/resume/upload`        | Upload PDF or DOCX              |
| GET    | `/resume/active`        | Get active resume               |
| POST   | `/resume/tailor`        | Tailor resume (blocking)        |
| POST   | `/resume/tailor/stream` | Tailor with SSE progress stream |
| GET    | `/resume/download/{id}` | Download tailored PDF           |

---

## How the AI Resume Loop Works

```
Upload Resume (PDF/DOCX)
        ↓
Extract Text (PyMuPDF / python-docx)
        ↓
┌─────────────────────────────────┐
│  Claude Sonnet generates HTML   │  ← iteration 1, 2, or 3
│  resume tailored to the JD      │
└─────────────────────────────────┘
        ↓
┌─────────────────────────────────┐
│  OpenAI GPT-5.5 evaluates ATS   │
│  Returns score + missing        │
│  keywords + suggestions         │
└─────────────────────────────────┘
        ↓
   Score ≥ 95%? ──Yes──→ Generate PDF → Done
        │
       No (up to 3 iterations)
        │
   Feed missing keywords + suggestions
   back to Claude as feedback context
        └──────────────────────────┘
```

Progress is streamed to the frontend via **Server-Sent Events** so users see each step in real time.

---

## Local Development

### Prerequisites

- Python 3.12+
- Node.js 18+
- macOS: `brew install pango cairo gdk-pixbuf libffi` (required for WeasyPrint)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env (see Environment Variables below)
uvicorn main:app --reload
# API at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# App at http://localhost:5173
```

The Vite dev server proxies `/api` → `http://localhost:8000` automatically.

---

## Environment Variables

Create `backend/.env`:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
SECRET_KEY=your-random-jwt-secret-key

# Optional — ATS evaluator (falls back to score=80 if not set)
OPENAI_API_KEY=sk-proj-...

# Optional — AWS S3 (uses local disk if not set)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
S3_BUCKET=your-bucket-name

# Optional — PostgreSQL (uses SQLite if not set)
DATABASE_URL=postgresql://user:pass@host/dbname
```

| Key                 | Where to get                                                         |
| ------------------- | -------------------------------------------------------------------- |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com)               |
| `OPENAI_API_KEY`    | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `ADZUNA_APP_ID/KEY` | [developer.adzuna.com](https://developer.adzuna.com)                 |

---

## Deployment

### Backend → Railway

1. Connect your GitHub repo to Railway
2. Set **Root Directory** to `backend`
3. Railway auto-detects the `Dockerfile`
4. Add all environment variables under **Variables**
5. Add a **PostgreSQL** plugin → Railway auto-sets `DATABASE_URL`
6. Generate a public domain → set target port to `8080`

### Frontend → Vercel

1. Import the GitHub repo in Vercel
2. Set **Root Directory** to `frontend`
3. Framework preset: **Vite**
4. No environment variables needed — the API URL is detected at runtime via `window.location.hostname`
5. `vercel.json` handles SPA routing automatically

---

## Database Schema

### `users`

| Column        | Type       | Notes  |
| ------------- | ---------- | ------ |
| id            | INTEGER PK |        |
| email         | VARCHAR    | Unique |
| password_hash | VARCHAR    | bcrypt |
| name          | VARCHAR    |        |
| created_at    | DATETIME   |        |

### `applications`

| Column                                    | Type       | Notes                                          |
| ----------------------------------------- | ---------- | ---------------------------------------------- |
| id                                        | INTEGER PK |                                                |
| user_id                                   | INTEGER FK |                                                |
| job_title, company, location              | VARCHAR    |                                                |
| job_url, job_description                  | TEXT       |                                                |
| status                                    | VARCHAR    | saved / applied / interview / offer / rejected |
| applied_date, follow_up_date              | DATE       |                                                |
| notes                                     | TEXT       |                                                |
| hiring_manager_name, hiring_manager_email | VARCHAR    |                                                |
| tailored_resume_path                      | TEXT       | S3 key or local path                           |
| created_at, updated_at                    | DATETIME   |                                                |

### `base_resumes`

| Column         | Type       | Notes                |
| -------------- | ---------- | -------------------- |
| id             | INTEGER PK |                      |
| user_id        | INTEGER FK |                      |
| filename       | VARCHAR    |                      |
| file_path      | TEXT       | S3 key or local path |
| extracted_text | TEXT       | Full resume text     |
| is_active      | BOOLEAN    | One active per user  |
| created_at     | DATETIME   |                      |

---

## Notes

- **Playwright auto-apply** works locally only — returns 503 in cloud deployments
- **S3 is optional** — falls back to local `uploads/` and `generated/` directories when `S3_BUCKET` is not set
- **CORS** uses `allow_origins=["*"]` with JWT in `Authorization` header (not cookies)
- **WeasyPrint** requires system-level libraries — the Dockerfile installs them via `apt-get`
- `bcrypt==4.0.1` is pinned — passlib is incompatible with bcrypt v5+
- `redirect_slashes=False` is set on the FastAPI app to prevent Railway's nginx from downgrading HTTPS redirects to HTTP
