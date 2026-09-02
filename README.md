<div align="center">

# 🎧 AI Call Agent

### A production-ready platform that gives every business an AI receptionist — on the phone, on the web, or anywhere.

**Django REST Framework · Channels · React · Vite · PostgreSQL · Celery · Redis**

[✨ Features](#-features) · [🧠 How it works](#-how-it-works) · [🏗️ Architecture](#️-architecture) · [🚀 Getting started](#-getting-started) · [🗣️ Templates](#️-agent-templates) · [📦 Deployment](#-deployment) · [🧪 Testing](#-testing)

</div>

---

## What is it?

**AI Call Agent** lets a business spin up an AI agent that behaves like a real receptionist — answering questions, checking appointment availability, booking appointments, looking up customers, and handing off to a human when needed.

It is **multi-channel by design**: the same agent can live on your **website** (chat widget), handle **phone calls** (Twilio/Telnyx), or be driven over an **API**. You can start with zero telephony and add a phone number whenever you're ready.

The AI talks naturally using an LLM, but it is **never trusted with the database** — every real-world action goes through a tightly controlled, validated backend tool layer.

---

## ✨ Features

### 🙋 An agent that actually does things
- Natural, conversational LLM responses
- **Tool calling** for real actions:
  - `check_appointment_availability` — verifies slots against the real schedule
  - `book_appointment` — creates confirmed bookings (only after the tool succeeds)
  - `list_services` — authoritative service names, durations, prices
  - `search_knowledge_base` — answers from *your* docs, not memory
  - `lookup_customer` — recognizes returning customers by phone
  - `transfer_to_human` — hands off when appropriate
- Multi-turn conversation memory persisted to Postgres

### 🌐 Multi-channel rollout
- **Website** — one-line install snippet → chat widget on your site (`/widget.js` + public chat API)
- **Phone** — Twilio (primary) or Telnyx, with TwiML loop and low-latency Media Streams websocket voice path
- **API** — drive the agent programmatically

### 🏢 Multi-tenant, per-business isolation
- `Organization` is the isolation boundary
- Each business gets its **own** agents, deployments, phone numbers, knowledge base, customers & appointments

### 🧪 Set-up wizard
- 5-step onboarding: **Channels → Agent → Services → Knowledge → Deploy**
- **8 industry prompt templates** with runtime variable injection — one template powers hundreds of businesses

---

## 🧠 How it works

```
Customer
   │
   ▼
Website widget · Phone call · API
   │
   ▼
        ┌────────────── AI Agent────────────────┐
        │  ┌─────┐   ┌──────────┐   ┌────────┐  │
        │  │ LLM │   │  Memory  │   │ Tools  │  │
        │  └─────┘   └──────────┘   └────────┘  │
        │                          │            │
        └──────────────────────────┼────────────┘
                                   ▼
                     ┌───────────────────────┐
                     │  Booking · CRM · KB   │
                     │      · Transfer       │
                     └───────────────────────┘
                                   │
                                   ▼
                              PostgreSQL
```

**The golden rule:** the LLM *reasons* and *chooses tools*, but the **backend is always in control** — it authenticates, validates, and owns every action.

---

## 🏗️ Architecture

```
ai-call-agent/
├── backend/                    # Django REST Framework + Channels
│   ├── config/                 # settings, URL routes, ASGI (Daphne)
│   ├── apps/
│   │   ├── accounts/           # users, JWT auth (SimpleJWT)
│   │   ├── tenancy/            # Organization & membership (tenant boundary)
│   │   ├── agents/             # agents, deployments, public widget/chat
│   │   ├── ai/                 # LLM orchestration + tool registry
│   │   │   ├── agent.py        # agent loop (LLM ↔ tools ↔ DB)
│   │   │   ├── prompt_render.py# runtime {{placeholder}} injection
│   │   │   ├── prompts.py      # default system prompt
│   │   │   ├── provider.py     # LLM provider abstraction
│   │   │   └── tools.py        # validated, registered tools only
│   │   ├── conversations/      # calls, messages, transcripts
│   │   ├── appointments/       # scheduling & availability
│   │   ├── crm/                # customers
│   │   ├── services/           # bookable services
│   │   ├── knowledge/          # RAG documents + search
│   │   ├── telephony/          # Twilio / Telnyx webhooks
│   │   ├── voice/              # STT / TTS / websocket streaming
│   │   ├── cms/                # landing-page copy + pricing
│   │   └── analytics/          # call analytics
│   └── docs/                   # architecture notes
│
├── frontend/                   # React 19 + Vite dashboard
│   └── src/
│       ├── pages/              # Onboarding, Deployments, Dashboard, etc.
│       └── lib/                # API client, landing defaults
│
├── nginx/                      # TLS + static + SPA reverse proxy
├── docker-compose.yml          # local dev: Postgres
└── docker-compose.production.yml  # full prod stack
```

### The backend stack in detail

```
Python 3.13 · Django 6.1 · DRF 3.18 · Channels 4 (Daphne)
PostgreSQL 17 · Redis 7 · Celery 5 · JWT · psycopg3
OpenAI-compatible LLM · Groq STT · edge-TTS / OpenAI TTS
Twilio · Telnyx
```

---

## 🚀 Getting started

> Happy path: run the **postgres** container for the database, then run the Django backend and the Vite frontend locally.

### 1. Prerequisites
- Python 3.13+
- Node.js 20+ & npm
- Docker (for local Postgres)

### 2. Start the database

```bash
docker compose up -d
```

This starts `call-agent-postgres` (PostgreSQL 17, network mode host). Database: `callagent` / `callagent` / `callagent`.

### 3. Configure & run the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env       # then fill in JWT_SECRET_KEY and LLM_API_KEY

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

The API (with an interactive Swagger UI at `/docs`) is now at `http://localhost:8000`.

### 4. Configure & run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open the dashboard at `http://localhost:5173`. The Vite dev server proxies API calls to the backend.

### 5. Create your first agent

1. Register an account (or log in).
2. Complete the **5-step onboarding wizard** — pick a template, add services, deploy to your website.
3. Paste the generated snippet into your website to go live.

---

## 🗣️ Agent templates

Each industry template is a **production-ready system prompt** that stays business-agnostic through runtime placeholder injection. One template powers many businesses — its own agents, services, knowledge and branding.

| Key | Label |
|------|-------|
| `generic` | General business |
| `realestate` | Real estate |
| `dental` | Dental clinic |
| `medical` | Medical practice |
| `legal` | Law firm |
| `salon` | Salon / studio |
| `homeservices` | Home services |
| `restaurant` | Restaurant |

Templates reference variables like `{{business_name}}`, `{{business_hours}}`, `{{services}}`; the backend renders them at conversation time from the organization's own data.

---

## 🔑 Environment variables

See `backend/.env.example` for the full annotated list. The essentials:

| Variable | Purpose |
|----------|---------|
| `JWT_SECRET_KEY` | Signs auth tokens (required) |
| `DATABASE_URL` | Postgres connection string |
| `LLM_API_KEY` | LLM provider API key |
| `LLM_MODEL` | e.g. `gpt-4o-mini` |
| `STT_PROVIDER` / `STT_MODEL` | Speech-to-text (defaults to OpenAI; point at Groq for whisper-large-v3-turbo) |
| `TTS_PROVIDER` / `TTS_MODEL` / `TTS_VOICE` | Text-to-speech (`edge` is free & keyless) |
| `TELEPHONY_PROVIDER` | `twilio` or `telnyx` |
| `VOICE_STREAMING_ENABLED` | 0/1 — low-latency websocket voice path |

> Never commit a real `.env`. Use `.env.example` as a documented reference.

---

## 📞 Telephony setup

After provisioning a number, point its voice settings at:

- **Inbound call** → `POST /telephony/webhook/inbound`
- **Status callback** → `POST /telephony/webhook/status`

For Telnyx, set `TELEPHONY_PROVIDER=telnyx` and provide `TELNYX_API_KEY`, `TELNYX_PUBLIC_KEY` and `TELNYX_CONNECTION_ID`. Live voice requires a **provisioned (non-trial)** number and a public HTTPS `PUBLIC_BASE_URL`.

---

## 📦 Deployment

A full production stack lives in `docker-compose.production.yml`:

```
nginx (TLS + static + SPA) ──> web (Daphne) ──> postgres
                                  │
                                  └──> worker (Celery) ──> redis
```

```bash
cp backend/.env.production.example backend/.env.production
# ...set strong values...
docker compose -f docker-compose.production.yml up -d --build
```

The backend image runs migrations + `collectstatic` on start, then serves via Daphne (ASGI), with Celery for background jobs.

---

## 🧪 Testing

```bash
cd backend
source .venv/bin/activate
python -m pytest            # full suite
python -m pytest apps/ai    # run one app's tests
```

---

## 🗺️ Roadmap

- [ ] Multi-agent per business
- [ ] Outbound calling
- [ ] Analytics & call outcomes
- [ ] WhatsApp & SMS channels
- [ ] RAG / vector knowledge base
- [ ] Subscription billing & plans

---

<div align="center">

Built with care for businesses that want an AI receptionist that **actually shows up**.

</div>
