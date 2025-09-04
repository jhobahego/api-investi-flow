from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api_v1.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configurar CORS
if settings.BACKEND_CORS_ORIGIN:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(settings.BACKEND_CORS_ORIGIN)],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/")
async def root() -> Dict[str, str]:
    return {"message": "InvestiFlow API - Backend funcionando correctamente!"}


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


# Incluir routers cuando estén creados
app.include_router(api_router, prefix=settings.API_V1_STR)
