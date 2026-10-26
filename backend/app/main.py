"""Aplicación FastAPI principal.

Configura la instancia de FastAPI, registra los routers de los módulos y
agrega middleware CORS para permitir el desarrollo del frontend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.inventario.router import router as inventario_router

# ---------------------------------------------------------------------------
# Instancia de FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Sistema de gestión para tostaduría de café",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS - Permite requests desde el frontend durante desarrollo
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite/React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Registro de routers por módulo
# ---------------------------------------------------------------------------
app.include_router(
    inventario_router,
    prefix=f"{settings.API_V1_STR}/inventario",
)

# ---------------------------------------------------------------------------
# Endpoint raíz para verificación de salud
# ---------------------------------------------------------------------------
@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    """Endpoint raíz para verificar que la API está funcionando."""
    return {"message": "Café de Finca API", "status": "ok"}
