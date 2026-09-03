---
trigger: always_on
---

DOCUMENTO DE DISENO DE SOFTWARE (SDD) - MVP LA VICTORIA FOUNDATION

PROYECTO: Agente de IA Asistente Legal y Sistema de Agendamiento
VERSION: 2.4.0 (Texto Plano - Monorepo Bilingue Hibrido)
FECHA: Septiembre 2026

VISION GENERAL Y ESPECIFICACIONES DEL SISTEMA

Modelo LLM de Produccion: gpt-5.6-luna (configurado en .env como OPENAI_MODEL=gpt-5.6-luna).

Modelo de Embeddings (RAG): text-embedding-3-small.

Experiencia Hibrida Bilingue (Espanol / Ingles):

Texto libre directo: El usuario puede preguntar desde el primer mensaje en espanol o ingles.

Auto-deteccion y respuesta espejada: Detecta el idioma del mensaje y responde dinamicamente en el mismo idioma.

Selector/Comando de Cambio: Comando /idioma o /language y boton de cambio de idioma.

Guardrail Legal (UPL): Prohibicion estricta de emitir opiniones o asesorias juridicas (Unauthorized Practice of Law). Si el usuario solicita dictamenes legales, el agente deriva a una cita presencial/virtual.

Tono: Profesional, institucional, empatico y preciso.

ESTRUCTURA DEL MONOREPO

la-victoria-monorepo/

apps/

frontend/ (Dashboard Next.js 14+ con Google Stitch UI)

backend/ (Servicio Python con FastAPI + LangGraph + Telegram aiogram)

packages/

knowledge-base/ (Documentacion de soporte: itin_faq.md, immigration_services.md)

docker-compose.yml (Entorno local con PostgreSQL y pgvector)

railway.json (Configuracion de despliegue automatizado via Nixpacks)

MODELO CONCEPTUAL DE DATOS (PostgreSQL + pgvector)

branches: 2 sedes activas (NY_QUEENS en Queens, NY y TX_DALLAS en Dallas, TX).

lawyers: Directorio de abogados (3 abogados asignados por sede, total 6).

clients: Registro de usuarios de Telegram (telegram_id, full_name, phone, language [es|en]).

appointments: Registro de citas (branch_id, lawyer_id, client_id, service_type, start_time, end_time, status [SCHEDULED, CANCELLED, COMPLETED, RESCHEDULED]).

faq_documents: Vector store para RAG bilingue con embeddings de text-embedding-3-small.

REGLAS DE NEGOCIO Y HORARIOS (EST)

Antelacion Minima: 24 Horas exactas antes del inicio de la cita.

Duracion de Cita: Bloques fijos de 1 Hora.

Pausa de Almuerzo: 12:00 PM a 1:00 PM (Inhabilitada en todos los dias).

Matriz de Disponibilidad:

Lunes a Viernes: 09:00, 10:00, 11:00, 13:00, 14:00, 15:00, 16:00 (7 slots/abogado/dia).

Sabados: 09:00, 10:00, 11:00 (3 slots/abogado/dia).

Domingos: Cerrado (0 slots).

Asignacion de Abogado: Algoritmo First Available (L1 -> L2 -> L3) de la sede seleccionada sin conflicto.

Gestion en Telegram (/mis_citas o /my_appointments):

Cancelar: Cambia estado a CANCELLED y libera el slot en la BD.

Reagendar: Inicia flujo de seleccion de nueva fecha/hora y actualiza a RESCHEDULED.

UX TELEGRAM HIBRIDA Y FLUJO LANGGRAPH

Inicio (/start): Mensaje bilingue inicial donde el usuario puede escribir su pregunta directamente o presionar botones principales.

Respuesta a Preguntas (RAG): Responde a la pregunta del usuario y anade botones interactivos al final (ej: Agendar Cita para ITIN).

Navegacion Guiada por Botones:

Sedes: Queens, NY / Dallas, TX.

Servicios: ITIN / Inmigracion / Notaria.

Fechas y Horas: Seleccion interactiva de slots disponibles (+24h).

Grafo de Estados (BotState):
Entrada -> Language Sync -> Intent Classification -> (RAG Node o Booking Flow) -> Persist DB -> Inline Keyboard Response.

SEGURIDAD DEL DASHBOARD ADMIN (Next.js Middleware)

Middleware (src/middleware.ts): Protege todas las rutas bajo /dashboard/*

Autenticacion Simple:

Redirige a /login si no existe la cookie session_token.

La pantalla /login valida la contrasena contra ADMIN_PASSWORD en .env.

Genera una cookie de sesion cifrada valida por 7 dias.

DESPLIEGUE EN RAILWAY

Sin Dockerfiles manuales: Despliegue automatizado conectando repositorio GitHub via Nixpacks.

Servicio 1: Backend Python (FastAPI + LangGraph) en apps/backend.

Servicio 2: Frontend Next.js en apps/frontend.

Servicio 3: Instancia PostgreSQL con extension pgvector.

PLAN DE EJECUCION SECUENCIAL

Paso 1: Scaffolding del monorepo (apps/frontend, apps/backend, packages/knowledge-base, docker-compose.yml).

Paso 2: Modelos SQLAlchemy/SQLModel y conexion a PostgreSQL + pgvector.

Paso 3: Modulo RAG bilingue (text-embedding-3-small) con base de conocimiento Markdown.

Paso 4: Construir grafo de LangGraph (nodos RAG, guardrails UPL, reglas agendamiento +24h y almuerzo).

Paso 5: Handler Telegram (aiogram) con soporte de texto libre, auto-deteccion de idioma e Inline Keyboards.

Paso 6: Frontend Dashboard en Next.js 14 (Google Stitch UI) con Middleware Auth y vistas de calendario/citas.

Paso 7: Validar railway.json para despliegue automatizado.