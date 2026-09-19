from fastapi import APIRouter
from app.api.routes import conversations, fashion, memories, models, personas, providers, settings

api_router = APIRouter(prefix="/api")
api_router.include_router(settings.router)
api_router.include_router(memories.router)
api_router.include_router(personas.router)
api_router.include_router(providers.router)
api_router.include_router(models.router)
api_router.include_router(conversations.router)
api_router.include_router(fashion.router)
