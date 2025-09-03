from fastapi import APIRouter

from app.api.api_v1.endpoints import auth, projects, users

api_router = APIRouter()

# Incluir routers de endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(projects.router, prefix="/proyectos", tags=["projects"])
