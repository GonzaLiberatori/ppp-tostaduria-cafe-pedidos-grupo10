from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.pedidos.router import router as pedidos_router
from app.modules.clientes.router import router as clientes_router
from app.modules.inventario.router import router as inventario_router
from app.modules.gastos.router import router as gastos_router


app = FastAPI(
    title=settings.APP_NAME,
    description="API para gestión de pedidos y ventas - Café de Finca",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(pedidos_router, prefix="/api/v1")
app.include_router(clientes_router, prefix="/api/v1")
app.include_router(inventario_router, prefix="/api/v1")
app.include_router(gastos_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": settings.APP_NAME}


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": f"Bienvenido a {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/health",
    }