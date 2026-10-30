"""Aplicación FastAPI principal.

Configura la instancia de FastAPI, registra los routers de los módulos y
agrega middleware CORS para permitir el desarrollo del frontend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.clientes.router import router as clientes_router
from app.modules.gastos.router import router as gastos_router
from app.modules.inventario.router import router as inventario_router
from app.modules.pedidos.router import router as pedidos_router

# ---------------------------------------------------------------------------
# Instancia de FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Sistema de gestión para tostaduría de café",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS - Permite requests desde el frontend durante desarrollo
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Registro de routers por módulo
# ---------------------------------------------------------------------------
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(pedidos_router, prefix=settings.API_V1_STR)
app.include_router(clientes_router, prefix=settings.API_V1_STR)
app.include_router(gastos_router, prefix=settings.API_V1_STR)
app.include_router(
    inventario_router,
    prefix=f"{settings.API_V1_STR}/inventario",
)


# ---------------------------------------------------------------------------
# Endpoints de verificación
# ---------------------------------------------------------------------------
@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    """Endpoint raíz para verificar que la API está funcionando."""
    return {"message": f"Bienvenido a {settings.APP_NAME}", "docs": "/docs"}


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": settings.APP_NAME}
