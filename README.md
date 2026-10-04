# La Victoria Foundation — Legal Assistance & Scheduling System

An enterprise-grade, bilingual (Spanish / English) legal community assistance, paperwork orientation, and automated appointment scheduling platform designed as a technical case study for **La Victoria Foundation**, operating across regional offices in Queens, NY and Dallas, TX.

> **Project Notice & Context**  
> This project is an **independent case study and proof of concept (PoC)** developed for an institutional presentation and technical feasibility evaluation for La Victoria Foundation. It is not an officially affiliated, contracted, or production-deployed platform of the organization. All attorney rosters, branch schedules, booking records, and user scenarios are simulated for demonstration and architectural validation purposes.

The system is engineered as a **Hybrid Monorepo** encompassing three integrated tiers:
1. **Conversational AI Agent (VictorIA):** Asynchronous Telegram bot (`aiogram 3.x`) powered by `LangGraph`, vector-based RAG (`pgvector`), deterministic UPL guardrails, and persistent multi-turn thread checkpoints stored in an isolated PostgreSQL schema.
2. **Administrative Operations Dashboard:** Responsive web dashboard built with `Next.js 14` (Google Stitch UI) delivering real-time multi-attorney agenda synchronization (`WebSockets`), manual booking administration, and instant bilingual localization.
3. **Backend Service & Data Layer:** Asynchronous `FastAPI` service with partitioned relational models, transactional locks for concurrent bookings, and embedded vector search capabilities.

---

## Table of Contents
- [Monorepo Architecture](#monorepo-architecture)
- [Technology Stack](#technology-stack)
- [Case Study Scope & Environment](#case-study-scope--environment)
- [Core Capabilities](#core-capabilities)
- [Business Logic & Scheduling Constraints](#business-logic--scheduling-constraints)
- [Legal Guardrail: Unauthorized Practice of Law (UPL)](#legal-guardrail-unauthorized-practice-of-law-upl)
- [Data Architecture & PostgreSQL Schemas](#data-architecture--postgresql-schemas)
- [Conversational State Machine & Persistence](#conversational-state-machine--persistence)
- [Administrative Dashboard](#administrative-dashboard)
- [Real-Time Event Dispatching (WebSockets)](#real-time-event-dispatching-websockets)
- [Security, Privacy & Cybersecurity Architecture](#security-privacy--cybersecurity-architecture)
- [Local Installation & Setup](#local-installation--setup)
- [Environment Configuration](#environment-configuration)
- [Infrastructure & Deployment (Railway)](#infrastructure--deployment-railway)
- [Attribution & Rights](#attribution--rights)

---

## Monorepo Architecture

```
la-victoria-monorepo/
├── apps/
│   ├── backend/                 # FastAPI service, LangGraph state machine, and Telegram bot
│   │   ├── app/
│   │   │   ├── agent/           # LangGraph graph, PostgresSaver integration, and UPL guardrails
│   │   │   ├── api/             # REST endpoints (/api/appointments, /api/branches)
│   │   │   ├── core/            # Configuration management via pydantic-settings
│   │   │   ├── db/              # SQLAlchemy session lifecycle (sync and async engines)
│   │   │   ├── models/          # Relational entities defined in the public schema (entities.py)
│   │   │   ├── rag/             # Markdown ingestion pipeline, embeddings, and similarity search
│   │   │   ├── services/        # WebSocket ConnectionManager and concurrency-locked booking service
│   │   │   └── telegram/        # aiogram bot handlers, message debounce, and anti-duplicate logic
│   │   ├── scripts/             # Database seeding scripts (branches, attorneys, initial appointments)
│   │   └── tests/               # Automated unit tests for UPL guardrails and business logic
│   └── frontend/                # Administrative dashboard built on Next.js 14
│       ├── public/              # Brand assets, vector icons, and static styles
│       └── src/
│           ├── app/
│           │   ├── api/auth/    # Authentication route handlers (session cookie lifecycle)
│           │   ├── dashboard/   # Multi-attorney agenda view, custom date popover, and MVP banner
│           │   └── login/       # Authentication screen with glassmorphic layout and disclaimer
│           └── middleware.ts    # Edge route protection for /dashboard/* endpoints
├── packages/
│   └── knowledge-base/          # Source documentation for RAG vectorization
│       ├── immigration_services.md
│       └── itin_faq.md
├── docker-compose.yml           # Local PostgreSQL 16 container definition with pgvector
└── railway.json                 # Declarative deployment specification via Nixpacks
```

---

## Technology Stack

| Layer | Technology | Operational Function |
|---|---|---|
| **LLM Inference** | OpenAI `gpt-5.6-luna` | Natural language understanding, intent classification, and entity extraction |
| **Vector Embeddings** | `text-embedding-3-small` | 1536-dimensional dense vector embeddings for semantic retrieval (RAG) |
| **Orchestration** | `LangGraph` + `LangChain` | Stateful conversation graphs with checkpointed PostgreSQL persistence |
| **Checkpointer** | `langgraph-checkpoint-postgres` | Graph snapshot serialization stored under the dedicated `langgraph` schema |
| **Backend Framework** | `FastAPI` + `Uvicorn` | Asynchronous REST endpoints and full-duplex WebSocket channels |
| **Bot Gateway** | `aiogram 3.x` | Asynchronous Telegram event loop handling polling and callback queries |
| **Database** | `PostgreSQL 16` + `pgvector` | ACID relational persistence with cosine distance vector indexing |
| **Persistence Driver** | `SQLAlchemy 2.x`, `psycopg 3` | Asynchronous connection pooling and schema-bound ORM mapping |
| **Frontend Framework** | `Next.js 14` (App Router) | Server-rendered React framework for administrative control |
| **Styling & UI** | `Tailwind CSS` + Vanilla CSS | Google Stitch design guidelines with smooth container curvature |
| **Icon Library** | `Lucide React` | Lightweight SVG icons |

---

## Case Study Scope & Environment

To maintain full transparency during technical reviews and evaluations, explicit indicators identify the non-production status of this project:

- **Authentication Screen (`/login`):**
  - Status indicator: `MVP ENVIRONMENT — DEMONSTRATION VERSION`.
  - Contextual disclaimer: *"This system is an MVP functional validation. All registered information, branch offices, and appointments correspond to simulated test data."*
- **Operational Dashboard (`/dashboard`):**
  - Persistent top notification banner supporting real-time language toggling:
    - **English:** `MVP ENVIRONMENT` — *"Demonstration Mode: All information, attorneys, and scheduled bookings are simulated test data."*
    - **Spanish:** `ENTORNO MVP` — *"Modo Demostración: Toda la información, abogados y citas registradas corresponden a datos de prueba simulados."*

---

## Core Capabilities

### 1. Virtual Community Assistant (VictorIA)
- **Zero-Friction Bilingual Interaction (ES/EN):** Accepts inquiries in Spanish or English without pre-selecting options. The agent automatically infers the input language and mirrors its response.
- **Unstructured Inquiry Support:** Users can ask questions in natural language regarding ITIN applications, affirmative asylum filings, family preference petitions (I-130), adjustment of status (I-485), and consular notary services.
- **Dynamic Action Injection:** Educational responses dynamically include contextual scheduling triggers (e.g., `[Schedule ITIN Appointment]`).
- **Self-Service Appointment Management (`/my_appointments` or `/mis_citas`):**
  - Real-time lookup of active bookings tied to the user's Telegram ID.
  - **Single-click cancellation:** Updates appointment status to `CANCELLED`, releases the schedule block in PostgreSQL, and broadcasts the release via WebSockets.
  - **Guided rescheduling:** Navigates the user through selecting a new valid date and available time slot.
- **Concurrency & Anti-Duplicate Controls:**
  - Fast drop of simultaneous or rapid-fire button taps via memory locks (`booking_locks`).
  - Pre-commit uniqueness checks preventing duplicate bookings for the same user within overlapping hours.
  - Immediate user feedback via `callback.answer("Processing your appointment...")`.

### 2. Administrative Operations Dashboard
- **Dynamic Branch Context:** Seamlessly switch between Queens, NY and Dallas, TX, dynamically reloading attorney rosters and schedule blocks.
- **Instant Interface Localization (`EN` / `ES`):** One-click toggle that updates 100% of interface labels, status indicators, schedule matrices, and modal dialogues.
- **Multi-Attorney Schedule Matrix:**
  - Dedicated operational lanes for all 3 branch attorneys.
  - Built-in institutional lunch hour (12:00 PM – 1:00 PM) distinctly indicated across all days.
  - Manual appointment creation by selecting any unoccupied block (`+ Schedule Appointment`).
  - Clean card design displaying client identifiers and confirmation status badges.
- **Custom Date Popover:** Tailored modal calendar with month/year navigation, active day highlighting, and a rapid reset to the current date.
- **Edge Route Protection:**
  - Edge middleware verifying an encrypted HTTP-only `session_token` cookie.
  - Automated redirection to `/login` for unauthenticated requests.
  - Explicit session termination via `POST /api/auth/logout`.

---

## Business Logic & Scheduling Constraints

1. **Regional Offices:**
   - `NY_QUEENS`: 37-53 90th Street, Queens, NY 11372 (3 active attorneys).
   - `TX_DALLAS`: 17762 Preston Rd, Ste 200, Dallas, TX 75252 (3 active attorneys).
2. **Operating Hours (Eastern Standard Time - EST):**
   - **Monday through Friday:** 09:00 AM to 05:00 PM (Available slots: 09:00, 10:00, 11:00, 13:00, 14:00, 15:00, 16:00). Capacity: **7 slots/attorney/day**.
   - **Saturday:** 09:00 AM to 12:00 PM (Available slots: 09:00, 10:00, 11:00). Capacity: **3 slots/attorney/day**.
   - **Sunday:** Closed (0 slots).
3. **Institutional Lunch Pause:** Systematically blocked from 12:00 PM to 01:00 PM on all operating days.
4. **Advance Notice Requirement:** **Strict 24-hour minimum** prior to slot start time. Same-day bookings are programmatically prohibited.
5. **Slot Duration:** Uniform 60-minute consultation blocks.
6. **Attorney Allocation Algorithm:** *First Available* priority dispatch (L1 -> L2 -> L3) within the designated branch, assigning the first available attorney without calendar collisions.

---

## Legal Guardrail: Unauthorized Practice of Law (UPL)

The agent integrates a **deterministic, non-bypassable guardrail** designed to prevent the unauthorized practice of law (UPL):
- **Absolute Restriction:** VictorIA is strictly prohibited from rendering legal assessments, evaluating probabilities of success (e.g., *"will I be deported?"*, *"what are my chances of obtaining asylum?"*), or providing actionable legal advice.
- **Empathetic Referral:** When an inquiry requests legal evaluation, VictorIA acknowledges the user's situation, explains its statutory limitations as an automated assistant, and offers an immediate referral to schedule an appointment with a licensed staff attorney.
- **Mandatory Notice:** All informational replies state that guidance is educational and does not constitute attorney-client privilege.

---

## Data Architecture & PostgreSQL Schemas

The database leverages **two isolated logical schemas** within PostgreSQL to decouple domain business entities from agent orchestration state:

### 1. Business Schema (`public`)
Manages transactional domain models, foreign relationships, and vector embeddings:

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
Dedicated storage managed by the `PostgresSaver` checkpointer:
- **`checkpoints`:** State graph execution snapshots indexed by conversation thread (`thread_id`).
- **`checkpoint_blobs`:** Binary serialization of graph channel states and variables.
- **`checkpoint_writes`:** Intermediate write operations and deltas produced during node execution.
- **`checkpoint_migrations`:** Framework-level schema version tracking.

---

## Conversational State Machine & Persistence

```mermaid
flowchart TD
    A[Incoming Telegram Message] --> B[Retrieve or Create Client Record]
    B --> C[Set Configurable Thread ID = telegram_id]
    C --> D[Detect Language & Classify Intent]
    
    D -->|Informational / Procedural Inquiry| E[RAG Node: pgvector Semantic Search]
    D -->|Direct Legal Advice Request| F[UPL Guardrail: Empathetic Referral]
    D -->|Scheduling Intent / Action Buttons| G[Guided Booking Subgraph]
    
    E --> H[gpt-5.6-luna Synthesis + Conversation Context]
    F --> I[Legal Notice + Consultation Scheduling Shortcut]
    G --> J[Step Sequence: Branch -> Service -> Date +24h -> Slot]
    
    H --> K[Inline Keyboard with Suggested Follow-ups]
    I --> K
    J --> L[Persist Appointment & Dispatch WebSocket Event]
    
    K --> M[PostgresSaver: Commit Snapshot to 'langgraph' Schema]
    L --> M
    M --> N[Transmit Telegram Message]
```

---

## Administrative Dashboard

- **Default Endpoint:** `http://localhost:3000/dashboard`
- **Login Experience (`/login`):**
  - Centered glassmorphic container with official brand marks and demonstration badge.
  - Fluid background animation utilizing CSS-rendered lighting orbs.
  - Demonstration access credential: `victoria`.
- **Route Authorization:** Enforced via [middleware.ts](file:///Users/jemoreno/DevLab/Cognitix/LaVictoria/apps/frontend/src/middleware.ts), intercepting unauthenticated access to `/dashboard/*`.
- **Runtime Performance:** Production builds (`next build && next start`) deliver sub-200ms route transitions.

---

## Real-Time Event Dispatching (WebSockets)

- **WebSocket Route:** `ws://localhost:8000/ws/appointments`
- **Event Protocol:** On any appointment creation, modification, or cancellation (originating either via the Telegram bot or the REST API), the `ConnectionManager` broadcasts an event payload:
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
- **Operational Result:** All active administrative sessions update schedule matrices immediately without requiring manual browser refreshes.

---

## Security, Privacy & Cybersecurity Architecture

The platform implements defense-in-depth principles across its application, data, and AI orchestration layers:

### 1. Application & Session Hardening
- **HTTP-Only Cookie Management:** Session tokens are delivered with `HttpOnly` and `SameSite=Lax` flags, preventing client-side script access and mitigating Cross-Site Scripting (XSS) token theft and Cross-Site Request Forgery (CSRF).
- **Edge Authentication Gate:** A Next.js edge middleware evaluates cryptographic tokens prior to route execution, blocking unauthorized access to `/dashboard/*` before server components render.
- **Strict CORS & API Filtering:** FastAPI is configured with explicit origin whitelists and credentials control, preventing unauthorized cross-origin requests.

### 2. Data Protection & Schema Segregation
- **SQL Injection Prevention:** All relational and vector operations leverage SQLAlchemy ORM and parameterized queries, entirely preventing SQL injection (SQLi) vectors.
- **Architectural Schema Partitioning:** Conversational snapshots and agent thread state reside in an isolated `langgraph` PostgreSQL schema, decoupling operational memory from core transactional entities in the `public` schema.
- **PII Minimization:** The system enforces strict data minimization. Sensitive government identifiers (such as SSNs or Alien Registration Numbers) are never requested or stored. Stored client data is limited to Telegram identifiers and booking logistics.

### 3. AI Safety & Prompt Injection Mitigation
- **Two-Tier Intent Classification Pipeline:** Incoming user inputs pass through a strict semantic classifier prior to generation, separating raw conversational inputs from execution subgraphs.
- **Deterministic Legal Guardrail (UPL Defense):** Programmatic guardrails detect inquiries demanding legal opinions or case merits, deterministically routing them to licensed human counsel and eliminating liability for unauthorized practice of law.
- **Constrained Execution Graphs:** The LangGraph state machine enforces deterministic node transitions, preventing generative models from executing unauthorized database modifications or uncontrolled tooling.

### 4. Concurrency & Denial-of-Service Defense
- **Atomic Booking Locks:** In-memory asynchronous locks (`booking_locks`) isolate concurrent callback events, preventing race conditions and double-booking attacks.
- **Telegram Debounce & Anti-Flooding:** Callback query debounce mechanisms instantly discard duplicated taps, preventing event loop starvation.

---

## Local Installation & Setup

### Prerequisites
- **Node.js:** v18.x or v20.x with `npm`
- **Python:** 3.9+ with virtual environment tooling (`venv`)
- **Docker & Docker Compose** (for PostgreSQL and pgvector)

### Step 1: Initialize Database Container
```bash
docker-compose up -d
```
*Initializes PostgreSQL on port 5432 with the pgvector extension enabled.*

### Step 2: Configure & Launch Backend Service
```bash
cd apps/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Populate baseline records (branches, attorneys, initial bookings)
python3 scripts/seed_db.py

# Ingest knowledge base documentation into vector store (RAG)
python3 -m app.rag.ingestion

# Start FastAPI server and Telegram bot polling
uvicorn app.main:app --port 8000 --host 0.0.0.0
```

### Step 3: Configure & Launch Frontend Application
```bash
cd apps/frontend
npm install
npm run build
npm run start
```
*The administrative dashboard is served at [http://localhost:3000](http://localhost:3000).*

---

## Environment Configuration

Create a `.env` file in the root directory:

```env
# LLM & Embedding Services
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.6-luna
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Telegram Integration
TELEGRAM_BOT_TOKEN=8721514801:...

# Database Connections
DATABASE_URL=postgresql+asyncpg://postgres:postgres_password_local@localhost:5432/lavictoriadb
DATABASE_URL_SYNC=postgresql://postgres:postgres_password_local@localhost:5432/lavictoriadb

# Administrative Authentication
ADMIN_PASSWORD=victoria
SESSION_SECRET=la_victoria_super_secret_session_key_2026_secure!
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Infrastructure & Deployment (Railway)

The codebase is structured for zero-configuration deployments via **Nixpacks** using [railway.json](file:///Users/jemoreno/DevLab/Cognitix/LaVictoria/railway.json):

1. **Backend Service:**
   - Root path: `apps/backend`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
2. **Frontend Service:**
   - Root path: `apps/frontend`
   - Build command: `npm run build`
   - Start command: `npm run start -p $PORT`
3. **Database Service:**
   - Railway managed PostgreSQL instance with `vector` extension and `langgraph` schema initialized on first run.

---

## Attribution & Rights

Designed and developed as an engineering case study for **La Victoria Foundation** © 2026. All rights reserved.
