# 🏛️ La Victoria Foundation — Legal Assistance & Scheduling System

Comprehensive bilingual (Spanish / English) legal community assistance, paperwork guidance, and intelligent appointment scheduling system built for **La Victoria Foundation**, with active branches in Queens, NY and Dallas, TX.

Architected as a **Hybrid Monorepo** integrating:
1. **Virtual Assistant Agent (VictorIA):** Conversational Telegram bot (`aiogram 3.x` + `LangGraph` + Vector RAG + UPL Guardrails + PostgreSQL Checkpointer in dedicated `langgraph` schema).
2. **Web Admin Dashboard:** Responsive admin panel built with `Next.js 14` (Google Stitch UI) featuring real-time multi-attorney calendar views (`WebSockets`), appointment management, MVP environment banners, and instant bilingual switching.
3. **Backend API & Database:** `FastAPI` + `PostgreSQL` structured with isolated schemas (`public` for business logic and `langgraph` for conversational state) with the `pgvector` vector extension.

---

## 📌 Table of Contents
- [Monorepo Architecture](#-monorepo-architecture)
- [Tech Stack](#-tech-stack)
- [Demo Notices & MVP Environment](#-demo-notices--mvp-environment)
- [Key Features](#-key-features)
- [Business Rules & Constraints](#-business-rules--constraints)
- [Legal Guardrail: UPL (Unauthorized Practice of Law)](#-legal-guardrail-upl-unauthorized-practice-of-law)
- [Data Model & PostgreSQL Schemas](#-data-model--postgresql-schemas)
- [Conversational Flow & LangGraph Persistence](#-conversational-flow--langgraph-persistence)
- [Web Admin Dashboard](#-web-admin-dashboard)
- [Real-Time Synchronization (WebSockets)](#-real-time-synchronization-websockets)
- [Local Installation & Setup](#-local-installation--setup)
- [Environment Variables](#-environment-variables)
- [Deployment Strategy (Railway)](#-deployment-strategy-railway)
- [License & Copyright](#-license--copyright)

---

## 🏗️ Monorepo Architecture

```
la-victoria-monorepo/
├── apps/
│   ├── backend/                 # FastAPI API, LangGraph Agent, and Telegram Bot
│   │   ├── app/
│   │   │   ├── agent/           # LangGraph graph with PostgresSaver, prompts, and UPL guardrails
│   │   │   ├── api/             # REST endpoints (/api/appointments, /api/branches)
│   │   │   ├── core/            # pydantic-settings configuration
│   │   │   ├── db/              # SQLAlchemy session and sync/async connectors
│   │   │   ├── models/          # Business models in public schema (entities.py)
│   │   │   ├── rag/             # Markdown ingestion, embeddings, and similarity search
│   │   │   ├── services/        # WebSocket ConnectionManager and booking_service with locks
│   │   │   └── telegram/        # aiogram bot with handlers, debounce, and anti-duplicate logic
│   │   ├── scripts/             # seed_db.py (Database seeding for branches, attorneys, and bookings)
│   │   └── tests/               # Unit tests for guardrails and business logic
│   └── frontend/                # Administrative Dashboard in Next.js 14
│       ├── public/              # Institutional logo, assets, and compiled CSS
│       └── src/
│           ├── app/
│           │   ├── api/auth/    # Route handlers for login (cookie-tolerant) and logout
│           │   ├── dashboard/   # Multi-attorney calendar, custom popover, and MVP banner
│           │   └── login/       # Login screen with glassmorphism card, animated orbs, and MVP disclaimer
│           └── middleware.ts    # Route protection for /dashboard/* via session cookie
├── packages/
│   └── knowledge-base/          # Markdown RAG knowledge base
│       ├── immigration_services.md
│       └── itin_faq.md
├── docker-compose.yml           # PostgreSQL 16 container with pgvector extension
└── railway.json                 # Automated Nixpacks deployment without custom Dockerfiles
```

---

## ⚡ Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| **LLM Model** | OpenAI `gpt-5.6-luna` | Conversational reasoning and entity extraction |
| **Embeddings** | `text-embedding-3-small` | Semantic search (RAG) with 1536 dimensions |
| **AI Orchestrator** | `LangGraph` + `LangChain` | Stateful graph execution with persistent PostgreSQL memory |
| **AI Checkpointer** | `langgraph-checkpoint-postgres` | Snapshots and conversational states in `langgraph` schema |
| **Backend REST & WS** | `FastAPI` + `Uvicorn` | High-throughput asynchronous API and bidirectional WebSockets |
| **Messaging Bot** | `aiogram 3.x` | Asynchronous Telegram interaction handler |
| **Database** | `PostgreSQL` + `pgvector` | ACID relational persistence and vector similarity search |
| **Database Driver** | `SQLAlchemy 2.x`, `psycopg 3` | ORM data modeling and transactional connection pooling |
| **Web Frontend** | `Next.js 14` (App Router) | Reactive administrative dashboard |
| **Styles & UI** | `Tailwind CSS` + Vanilla CSS | Google Stitch UI design system, smooth `rounded-3xl` corners |
| **Icons** | `Lucide React` | Clean, minimal vector iconography |

---

## ⚠️ Demo Notices & MVP Environment

Explicit visual notices are implemented across both authentication and the operational dashboard to clarify the MVP scope:
- **Login Screen (`/login`):**
  - Pulsing badge: `MVP ENVIRONMENT — DEMONSTRATION VERSION`.
  - Legal disclaimer: *"This system is an MVP functional validation. All registered information, branch offices, and appointments correspond to simulated test data."*
- **Scheduling Panel (`/dashboard`):**
  - Stylized top banner with bilingual toggle:
    - **EN:** `MVP ENVIRONMENT` — *"Demonstration Mode: All information, attorneys, and scheduled bookings are simulated test data."*
    - **ES:** `ENTORNO MVP` — *"Modo Demostración: Toda la información, abogados y citas registradas corresponden a datos de prueba simulados."*

---

## 🌟 Key Features

### 1. Virtual Community Assistant (VictorIA)
- **Native Bilingual Support (ES/EN):** Users can interact directly in Spanish or English; the bot automatically detects the language and mirrors responses accordingly.
- **Free-Form Text Input:** Users are never locked into rigid menus; they can freely inquire about ITIN applications, asylum processes, family petitions (I-130), adjustment of status (I-485), or notary services.
- **Interactive Quick-Action Buttons:** Responses append contextual booking buttons (e.g., `[📅 Schedule ITIN Appointment]`).
- **User Appointment Management (`/my_appointments` or `/mis_citas`):**
  - View active appointments and allocated time slots.
  - **Immediate cancellation:** Frees the slot in PostgreSQL and broadcasts the update to the dashboard.
  - **Interactive rescheduling:** Guides the user through picking a new valid date and time slot.
- **Anti-Duplicate & Concurrency Protection:**
  - Fast drop of simultaneous or rapid-fire button taps (`booking_locks`).
  - Pre-insert conflict validation preventing the same user from booking overlapping appointments.
  - Immediate user feedback via `callback.answer("Processing your appointment...")`.

### 2. Live Administrative Dashboard
- **Dynamic Branch Selector:** Seamlessly switch between Queens, NY and Dallas, TX, dynamically reloading attorneys and availability.
- **Bilingual Interface Switcher (`🌐 EN` / `🌐 ES`):** Instantly translates 100% of the UI, data tables, metrics, banners, and controls.
- **Polished Multi-Attorney Calendar:**
  - Dedicated column for each of the 3 branch attorneys.
  - Harmoniously integrated institutional lunch break (12:00 PM – 1:00 PM).
  - Quick manual booking by clicking any available slot (`+ Schedule Appointment`).
  - Clean appointment cards without redundant hour labels, showing client name and confirmation badge.
- **Custom Date Popover:** Tailor-made modern calendar picker, rounded, with institutional blue accents, month/year navigation, and a quick-return "Today" shortcut.
- **Session Security:**
  - Edge middleware validating encrypted `session_token` cookie.
  - Automatic redirect to `/login` for unauthenticated requests.
  - Secure session destruction via `POST /api/auth/logout`.

---

## ⚖️ Business Rules & Constraints

1. **Active Branches:**
   - `NY_QUEENS`: 37-53 90th Street, Queens, NY 11372 (3 active attorneys).
   - `TX_DALLAS`: 17762 Preston Rd, Ste 200, Dallas, TX 75252 (3 active attorneys).
2. **Operating Hours (EST Timezone):**
   - **Monday to Friday:** 09:00 AM to 05:00 PM (Slots at 09:00, 10:00, 11:00, 13:00, 14:00, 15:00, 16:00). Total: **7 slots/attorney/day**.
   - **Saturday:** 09:00 AM to 12:00 PM (Slots at 09:00, 10:00, 11:00). Total: **3 slots/attorney/day**.
   - **Sunday:** Closed (0 slots).
3. **Lunch Break:** Strictly blocked from 12:00 PM to 01:00 PM every day.
4. **Advance Notice Requirement:** **Strict 24-hour minimum** prior to the appointment start time. Same-day bookings are prohibited.
5. **Appointment Duration:** Fixed blocks of **1 hour**.
6. **Attorney Assignment Algorithm:** *First Available* based on priority order (L1 -> L2 -> L3) within the selected branch, automatically assigning the first unbooked attorney for the requested slot.

---

## 🛡️ Legal Guardrail: UPL (Unauthorized Practice of Law)

The platform enforces a **mandatory, non-bypassable guardrail** to strictly avoid the unauthorized practice of law (UPL):
- **Strict Prohibition:** The virtual assistant **VictorIA** never issues legal assessments, probability of success on a case (e.g., *"will I be deported?"*, *"what are my chances of winning asylum?"*), or binding legal advice.
- **Referral Protocol:** If a user requests legal counsel or an official opinion, VictorIA empathetically explains system limitations and redirects the user to schedule a consultation with the foundation's licensed attorneys.
- **Disclaimer Banner:** All guidance responses explicitly note that the provided information is for educational and community orientation purposes only.

---

## 🗄️ Data Model & PostgreSQL Schemas

To ensure clean separation of concerns, the database is partitioned into **two independent logical schemas**:

### 1. Business Schema (`public`)
Stores foundation entities and relational business logic:

```mermaid
erDiagram
    BRANCHES ||--o{ LAWYERS : "has"
    BRANCHES ||--o{ APPOINTMENTS : "hosts"
    LAWYERS ||--o{ APPOINTMENTS : "serves"
    CLIENTS ||--o{ APPOINTMENTS : "requests"

    BRANCHES {
        UUID id PK
        string code "NY_QUEENS | TX_DALLAS"
        string name
        string address
        string timezone
    }

    LAWYERS {
        UUID id PK
        UUID branch_id FK
        string full_name
        string email
        int priority_order "1 (L1), 2 (L2), 3 (L3)"
        boolean is_active
    }

    CLIENTS {
        UUID id PK
        string telegram_id "UK"
        string full_name
        string phone
        string language "es | en"
    }

    APPOINTMENTS {
        UUID id PK
        UUID branch_id FK
        UUID lawyer_id FK
        UUID client_id FK
        string service_type "ITIN | IMMIGRATION | NOTARY"
        datetime start_time
        datetime end_time
        string status "SCHEDULED | CANCELLED | COMPLETED | RESCHEDULED"
        text notes
    }

    FAQ_DOCUMENTS {
        UUID id PK
        string title
        string source_file
        string category "ITIN | IMMIGRATION | GENERAL"
        string language "es | en"
        text content
        vector embedding "1536 dims (text-embedding-3-small)"
    }
```

### 2. AI Orchestration Schema (`langgraph`)
Isolates the internal tables of the LangGraph persistent checkpointer:
- **`checkpoints`:** Snapshot history of state graphs indexed by user thread (`thread_id`).
- **`checkpoint_blobs`:** Serialized storage for channels and state payload variables.
- **`checkpoint_writes`:** Intermediate writes and state deltas generated by graph nodes.
- **`checkpoint_migrations`:** Framework schema versioning managed by LangGraph.

---

## 🧠 Conversational Flow & LangGraph Persistence

```mermaid
flowchart TD
    A[Incoming Telegram Message] --> B[Get or Create Client]
    B --> C[Configure Thread ID = telegram_id]
    C --> D[Detect Language & Classify Intent]
    
    D -->|Informational / Procedure Question| E[RAG Node: pgvector Vector Search]
    D -->|Direct Legal Inquiry| F[UPL Guardrail: Responsible Referral]
    D -->|Booking Intent / Inline Buttons| G[Guided Booking Flow]
    
    E --> H[gpt-5.6-luna Generation + LangGraph History]
    F --> I[Disclaimer Message + Booking Shortcut]
    G --> J[Selection: Branch -> Service -> Date +24h -> Slot]
    
    H --> K[Inline Keyboard with Suggested Actions]
    I --> K
    J --> L[Persist in PostgreSQL & Broadcast via WebSocket]
    
    K --> M[PostgresSaver: Commit Checkpoint to 'langgraph' Schema]
    L --> M
    M --> N[Send Formatted Response to Telegram]
```

---

## 🖥️ Web Admin Dashboard

- **Access URL:** `http://localhost:3000/dashboard`
- **Login Screen (`/login`):**
  - Centered glassmorphic card with official branding and MVP environment indicator.
  - Organic backdrop with subtle animated blue and white light orbs.
  - Default demo credential: `victoria`.
- **Protected Routes:** Handled by [middleware.ts](file:///Users/jemoreno/DevLab/Cognitix/LaVictoria/apps/frontend/src/middleware.ts), guarding `/dashboard/*` from unauthorized sessions.
- **Performance:** Production optimized via `next build && next start` with sub-200ms page transitions.

---

## 📡 Real-Time Synchronization (WebSockets)

- **WS Endpoint:** `ws://localhost:8000/ws/appointments`
- **Mechanism:** Whenever an appointment is created, cancelled, or rescheduled (from Telegram or through the dashboard REST API), the `ConnectionManager` broadcasts an event payload:
  ```json
  {
    "event": "APPOINTMENT_CREATED",
    "appointment": {
      "id": "appointment-uuid",
      "branch_code": "NY_QUEENS",
      "lawyer_id": "lawyer-uuid",
      "lawyer_name": "Carlos Mendoza, Esq.",
      "client_name": "Maria Gomez",
      "service_type": "ITIN Application (Form W-7)",
      "date": "2026-09-04",
      "hour": 10,
      "status": "SCHEDULED"
    }
  }
  ```
- **Outcome:** Connected client browsers update their schedule grids in real time with zero page refresh required.

---

## 🚀 Local Installation & Setup

### Prerequisites
- **Node.js:** v18.x or v20.x and `npm`
- **Python:** 3.9+ with `venv`
- **Docker & Docker Compose** (for PostgreSQL and pgvector)

### Step 1: Start the Database Container
```bash
docker-compose up -d
```
*This starts PostgreSQL on port 5432 with the pgvector extension pre-installed.*

### Step 2: Configure & Run the Backend
```bash
cd apps/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Seed the database (branches, attorneys, and initial demo bookings)
python3 scripts/seed_db.py

# Ingest Markdown documentation into the pgvector store (RAG)
python3 -m app.rag.ingestion

# Start the FastAPI API server and Telegram Bot
uvicorn app.main:app --port 8000 --host 0.0.0.0
```

### Step 3: Configure & Run the Frontend Dashboard
```bash
cd apps/frontend
npm install
npm run build
npm run start
```
*The dashboard will be accessible at [http://localhost:3000](http://localhost:3000).*

---

## 🔑 Environment Variables

Create a `.env` file in the root of the monorepo:

```env
# LLM & Embedding Settings
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.6-luna
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Telegram Bot Token
TELEGRAM_BOT_TOKEN=8721514801:...

# Database Connections
DATABASE_URL=postgresql+asyncpg://postgres:postgres_password_local@localhost:5432/lavictoriadb
DATABASE_URL_SYNC=postgresql://postgres:postgres_password_local@localhost:5432/lavictoriadb

# Admin Dashboard
ADMIN_PASSWORD=victoria
SESSION_SECRET=la_victoria_super_secret_session_key_2026_secure!
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## ☁️ Deployment Strategy (Railway)

The application is configured for deployment without manual Dockerfiles using **Nixpacks** via [railway.json](file:///Users/jemoreno/DevLab/Cognitix/LaVictoria/railway.json):

1. **Backend Service:**
   - Root directory: `apps/backend`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
2. **Frontend Service:**
   - Root directory: `apps/frontend`
   - Build command: `npm run build`
   - Start command: `npm run start -p $PORT`
3. **Database Service:**
   - Railway managed PostgreSQL instance with `vector` extension and `langgraph` schema auto-configured on startup.

---

## 📄 License & Copyright

Developed for **La Victoria Foundation** © 2026. All rights reserved.
