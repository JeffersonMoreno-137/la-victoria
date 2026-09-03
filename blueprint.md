## Blueprint Técnico de Arquitectura y Negocio - MVP La Victoria Foundation

Este documento consolida la arquitectura completa, las reglas de negocio, la estructura del monorepo, el flujo híbrido bilingüe y las especificaciones técnicas para la ejecución del MVP del Agente de IA e Interfaz de Gestión Administrativa.

## 1. Especificaciones del Sistema y Modelos de IA

- Ecosistema de IA: OpenAI

- Modelo LLM de Producción: gpt-5.6-luna (Configurado mediante la variable de entorno OPENAI_MODEL=gpt-5.6-luna ).

- Modelo de Embeddings (RAG): text-embedding-3-small .

- Soporte Bilingüe Nativo (Híbrido ES / EN):

- Texto Libre e Interacción Abierta: El usuario puede preguntar libremente desde su primer mensaje en español o inglés.

- Auto-Detección y Respuesta Espejada: El sistema identifica dinámicamente el idioma del usuario y responde en el mismo idioma.

- Comando y Selector de Idioma: Permite cambiar la preferencia en cualquier momento mediante /idioma o /language .

- Tono y Personalidad: Estrictamente profesional, institucional, empático y preciso. Sin tecnicismos informales.

- Guardrails de Inmigración (UPL - Unauthorized Practice of Law): Filtro estricto que prohíbe emitir opiniones o asesorías jurídicas. Si el usuario solicita dictámenes legales, el agente lo deriva amablemente a agendar una cita presencial/virtual con un abogado.

## 2. Estructura del Monorepo

\# Dashboard Next.js 14+ (Google Stitch UI)

\# Rutas de Next.js (Calendar, Citas, Leads)

\# UI Components (Shadcn + Stitch styling)

│ │ │ └── middleware.ts # Protección por Contraseña Simple (MVP Auth)

```
\# Servicio de Python (FastAPI + LangGraph + Tel
# Config, DB connection, OpenAI client
# LangGraph StateMachine, Nodos y Tools
# Vector store (pgvector) y RAG retriever
# Handler de aiogram + Inline Keyboards
# Endpoints REST para el Dashboard
```


```
│ ├── main.py
│ └── requirements.txt
│
├── packages/
│ └── knowledge-base/ # Documentación de soporte de La Victoria (FAQ,
│ ├── itin_faq.md
│ └── immigration_services.md
│
├── docker-compose.yml # Entorno local (PostgreSQL + pgvector)
└── railway.json # Configuración de despliegue automatizado (Nix
```

## 3. Reglas de Negocio de Agendamiento y Franjas Horarias

## Sedes y Capacidad

- 1. Sede Queens, NY: 37-53 90th Street, Queens, NY 11372 (3 Abogados asignados).

- 2. Sede Dallas, TX: 17762 Preston Rd, Ste 200, Dallas, TX 75252 (3 Abogados asignados).

## Matriz de Horarios Disponibles (Base EST)

- Antelación Mínima de Reserva:24 Horas exactas antes del inicio de la cita.

- Duración de la Cita: Bloques fijos de 1 Hora.

- Pausa de Almuerzo:12:00 PM a 1:00 PM (Inhabilitada en todos los días).

- Algoritmo de Asignación: First Available ( L1 → L2 → L3) para el slot seleccionado de la sede.

| Día | Horarios Válidos para Reserva (1h) | Citas / Abogado / |
| --- | --- | --- |
|   |   | Día |
| Lunes a | 09:00 , 10:00 , 11:00 , 13:00 , 14:00 , 15:00 , | 7 slots |
| Viernes | 16:00 |   |
| Sábados | 09:00 , 10:00 , 11:00 | 3 slots |
| Domingos Cerrado |   | 0 slots |

## Gestión de Citas por Telegram

El usuario tiene acceso en cualquier momento mediante el comando /mis_citas (o

/my_appointments ) a:

- Cancelar Cita: Actualiza el registro (status = 'CANCELLED' ) y libera el horario en la base de datos inmediatamente.

- Reagendar Cita: Inicia el flujo interactivo de selección de nueva fecha/hora y actualiza el registro (status = 'RESCHEDULED' ).


## 4. Experiencia de Usuario (UX) en Telegram: Hybrid UX & Inline Keyboards

Combinación de entrada libre de texto con guía interactiva mediante botones:

- 1. Entrada Libre e Intención: El usuario puede preguntar directamente sobre requisitos o solicitar agendamiento.

- 2. Selección de Sede:

- 3. Selección de Servicio / Trámite:

- 4. Selección de Fecha (Días disponibles +24h):

- Grilla interactiva: [ Mañana ] [ Jueves 10 ] [ Viernes 11 ] [ Sábado 12 ]

- 5. Selección de Hora:

- Muestra únicamente franjas libres en la BD (excluyendo de 12:00 a 1:00 PM y horarios ocupados).

- 6. Gestión de Citas Existentes:

- [ 🔄 Reagendar Cita / Reschedule ] [ ❌ Cancelar Cita / Cancel ] [ ❓ Hacer una pregunta / Ask Question ]

## 5. Seguridad del Dashboard Admin (Next.js Middleware)

- Mecanismo: Middleware en Next.js (src/middleware.ts ) que protege todas las rutas del dashboard.

- Flujo:

- 1. Verifica la existencia de la cookie session_token .

- 2. Si no existe, redirige automáticamente a la pantalla de autenticación /login .

- 3. La pantalla /login valida la clave contra la variable de entorno ADMIN_PASSWORD .

- 4. Emitirá una cookie de sesión cifrada válida por 7 días.

## 6. Diagrama de Estados de LangGraph (BotState )


## 7. Plan de Ejecución Secuencial

- 1. Scaffolding del Monorepo: Estructura de carpetas apps/frontend , apps/backend y packages/knowledge-base .

- 2. Base de Datos Local: Configuración de PostgreSQL + pgvector mediante docker- compose.yml .

- 3. Backend Base & Modelos: Definición de modelos SQLAlchemy/SQLModel y conexión a la BD.

- 4. Módulo RAG Bilingüe: Ingesta de base de conocimientos con text-embedding-3-small .

- 5. Grafo de LangGraph: Construcción de nodos de conversación, prompt bilingüe de "Luna" y guardrail UPL con gpt-5.6-luna .

- 6. Handler de Telegram (aiogram ): Soporte de texto libre, auto-detección e Inline Keyboards.

- 7. Dashboard Frontend: Next.js 14+ con Google Stitch UI y protección por Middleware Auth.

- 8. Configuración para Railway: Archivo railway.json para despliegue automatizado por Nixpacks.
