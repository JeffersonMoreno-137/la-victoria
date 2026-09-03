import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.endpoints import router as api_router
from app.telegram.bot import bot, dp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Iniciar bot de Telegram en segundo plano si está configurado el token
    polling_task = None
    if bot:
        logger.info("Iniciando servicio de bot Telegram en modo Polling...")
        polling_task = asyncio.create_task(dp.start_polling(bot))
    else:
        logger.warning("TELEGRAM_BOT_TOKEN no configurado o en modo placeholder. Bot no iniciado.")

    yield

    if polling_task and not polling_task.done():
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
        if bot:
            await bot.session.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

# CORS para Dashboard Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "La Victoria Backend & AI Assistant",
        "model": settings.OPENAI_MODEL,
        "embedding_model": settings.OPENAI_EMBEDDING_MODEL
    }
