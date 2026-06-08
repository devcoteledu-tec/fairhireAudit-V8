# FairHire — AI Hiring Fairness Auditor

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61dafb?logo=react&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-8-646cff?logo=vite&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ecf8e?logo=supabase&logoColor=white)
![Stripe](https://img.shields.io/badge/Stripe-Billing-635bff?logo=stripe&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-Apache%202.0-brightgreen)

FairHire is a SaaS platform that audits hiring datasets for AI-detectable bias. Upload a CSV or Excel file of recruitment data and get an instant, scored report across multiple fairness dimensions — gender disparity, caste/category bias, colorism signals, and proxy variable detection. Results render in an interactive React dashboard and export as a branded PDF report.

---

## 📄 Audit Report

See what a generated FairHire audit report looks like:

> **[View Example Report →](https://drive.google.com/file/d/1gnAtqkaaoLd1r7k3CS20LvEq9TSj_BaQ/view?usp=sharing)**

---

## ✨ Features

- **Multi-Dimension Bias Detection** — scores datasets across Gender AIR, Caste/Category, Colorism, and Proxy Bias modules
- **Statistical Audit Engine** — uses Fisher's Exact Test, Bonferroni-Holm multiple-comparison correction, and Wilson Confidence Intervals to produce statistically rigorous bias scores and narrative compliance commentary
- **Interactive Dashboard** — React SPA with charts, metric cards, per-module breakdowns, and drill-down views
- **PDF Report Export** — branded, downloadable audit reports ready to share with stakeholders
- **Audit History** — every audit is stored per user; revisit, compare, and re-download any past report
- **Stripe Subscription Billing** — Free, Pro, and Enterprise tiers with monthly audit limits and usage tracking
- **Cookie-Based Auth** — HttpOnly JWT access + refresh cookies; no tokens in localStorage
- **Email Verification & Password Reset** — powered by Resend with secure tokenized links
- **Docker-Ready** — single `docker compose up` gets the full stack running behind a hardened Nginx reverse proxy
- **Rate Limiting** — per-endpoint SlowAPI limits protect all authenticated and public routes

---

## 🏗 Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI 0.110, Python 3.11, psycopg2 |
| Database | Supabase (PostgreSQL + TIMESTAMPTZ-aware) |
| Audit Engine | Statistical methods: Fisher's Exact Test, Bonferroni-Holm, Wilson CI |
| Frontend | React 19, Vite 8, React Router v6 |
| Charts | Chart.js 4, react-chartjs-2 |
| Auth | HttpOnly cookies, JWT (access + refresh tokens) |
| Email | Resend API |
| Payments | Stripe (Checkout, Webhooks, Subscription) |
| PDF Reports | Server-side report generation |
| Deployment | Docker Compose, Nginx (reverse proxy + SPA routing) |

---

## 📁 Project Structure

```
fairhire-billing-full/
├── docker/                         # Production Docker configuration
│   ├── docker-compose.yml          # Orchestrates backend + dashboard services
│   ├── .env.example                # Environment variable template (copy to .env)
│   ├── backend/
│   │   ├── Dockerfile              # Multi-stage Python/FastAPI image
│   │   └── requirements.docker.txt # Pinned Python dependencies
│   └── dashboard/
│       ├── Dockerfile              # Multi-stage React + Nginx image
│       └── nginx.conf              # Hardened reverse proxy config
└── fairhire/
    ├── api.py                      # FastAPI application — all endpoints
    ├── audit_engine.py             # Bias detection and scoring logic
    ├── report_generator.py         # PDF report builder
    ├── stripe_webhook.py           # Stripe webhook handler
    ├── supabase_schema.sql         # Full database schema
    ├── requirements.txt            # Python dependencies
    ├── tests/                      # pytest test suite
    └── dashboard/                  # React frontend (Vite)
        └── src/
            ├── App.jsx             # Root app with React Router v6 routes
            ├── index.css           # Global styles + responsive breakpoints
            └── components/
                ├── AuthPage.jsx
                ├── HomePage.jsx
                ├── UploadPage.jsx
                ├── Dashboard.jsx
                ├── HistoryPage.jsx
                ├── Sidebar.jsx
                ├── VerifyEmailPage.jsx
                ├── ResetPasswordPage.jsx
                ├── CoreModules.jsx
                ├── AdvancedModules.jsx
                ├── ChartHelpers.jsx
                └── authUtils.js
```

---

## 🚀 Quick Start (Docker)

### 1. Clone the repository

```bash
git clone https://github.com/your-username/fairhire.git
cd fairhire
```

### 2. Configure environment variables

```bash
cp docker/.env.example docker/.env
```

Open `docker/.env` and fill in all required values (see [Environment Variables](#-environment-variables) below).

### 3. Build and start

```bash
docker compose -f docker/docker-compose.yml --env-file docker/.env up --build -d
```

### 4. Verify it's running

| Service | URL |
|---|---|
| Dashboard | http://localhost |
| API Health | http://localhost:8080/api/health |

---

## 🔧 Local Development (without Docker)

### Backend

```bash
cd fairhire
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn api:app --reload --port 8080
```

### Frontend

```bash
cd fairhire/dashboard
npm install
npm run dev
```

The Vite dev server starts on `http://localhost:5173`. Set `VITE_API_URL=http://localhost:8080` in a local `.env` file if not using the Nginx proxy.

---

## 🌍 Environment Variables

Copy `docker/.env.example` to `docker/.env` and configure:

### Database
| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection string |

### JWT Auth
| Variable | Description |
|---|---|
| `JWT_SECRET` | Random string, minimum 32 characters |
| `JWT_EXPIRE_HOURS` | Access token lifetime (default: `24`) |

### CORS
| Variable | Description |
|---|---|
| `ALLOWED_ORIGINS` | Comma-separated allowed origins (e.g. `https://your-domain.com`) |
| `VITE_API_URL` | Leave blank when using Nginx proxy; set to backend URL for local dev |

### Email (Resend)
| Variable | Description |
|---|---|
| `RESEND_API_KEY` | From [resend.com/api-keys](https://resend.com/api-keys) |
| `EMAIL_FROM` | Verified sender address (e.g. `noreply@your-domain.com`) |
| `APP_DOMAIN` | Public base URL used in email links (e.g. `https://your-domain.com`) |

### Auth / Cookie
| Variable | Description |
|---|---|
| `COOKIE_SECURE` | `true` in production (HTTPS); `false` for local HTTP dev only |

### Stripe Billing
| Variable | Description |
|---|---|
| `STRIPE_SECRET_KEY` | `sk_test_…` for dev, `sk_live_…` for production — [Stripe dashboard](https://dashboard.stripe.com/apikeys) |
| `STRIPE_WEBHOOK_SECRET` | From [Stripe webhooks](https://dashboard.stripe.com/webhooks) — verifies event authenticity |
| `STRIPE_PRO_PRICE_ID` | Price ID from Stripe dashboard: Products → Pro → Price ID |

---

## 🔌 API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/register` | Register new user (5/min rate limit) |
| `POST` | `/api/login` | Login and set HttpOnly cookies (10/min) |
| `GET` | `/api/verify-email` | Consume email verification token |
| `POST` | `/api/forgot-password` | Send password reset email (3/hour) |
| `POST` | `/api/reset-password` | Consume reset token and update password |
| `POST` | `/api/refresh` | Refresh access cookie (5/min) |
| `POST` | `/api/logout` | Clear auth cookies |
| `GET` | `/api/me` | Return current authenticated user |

### Audit
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/audit` | Upload dataset and run bias audit (5/hour) |
| `GET` | `/api/history` | Fetch all audits for the current user (30/min) |
| `POST` | `/api/report` | Generate and return PDF report (20/hour) |

### Billing
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/create-checkout-session` | Create Stripe Checkout session |
| `GET` | `/api/subscription-status` | Return current plan and usage |
| `POST` | `/api/stripe-webhook` | Stripe webhook receiver |

### System
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check with UTC timestamp |

---

## 🧪 Running Tests

```bash
cd fairhire
pip install -r requirements.txt
pytest tests/ -v
```

---

## 🔒 Security Highlights

- All auth cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` in production — never accessible to JavaScript
- Timezone-aware datetime comparisons throughout (`datetime.now(timezone.utc)`) — no naive/aware mixing bugs
- Per-endpoint rate limiting via SlowAPI on all public and authenticated routes
- Non-root Docker user (`appuser`, UID 10001) for the backend container
- Nginx security headers: `X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`
- Stripe webhook signature verification on every incoming event

---

## 📱 Responsive Design

The dashboard is fully responsive:

- **≤ 768px (tablet):** sidebar collapses to a hamburger-toggled overlay; content fills full width; grids go single-column
- **≤ 480px (mobile):** metric grid goes single-column; card padding reduces; font scales down ~10%; chart heights cap at 220px; sidebar shows icon only

---

## 🗺 Roadmap

- [ ] Multi-file batch audit
- [ ] Team/organization accounts
- [ ] Slack and webhook alert integrations
- [ ] CSV template download for standardized uploads
- [ ] Audit comparison view (before vs. after remediation)
- [ ] SOC 2 compliance logging

---

## 📄 License

APACHE © FairHire. See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change. Make sure tests pass before submitting a PR.

```bash
# Run linting
cd fairhire/dashboard && npm run lint

# Run backend tests
cd fairhire && pytest tests/ -v
```
