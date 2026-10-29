from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.clientes.router import router as clientes_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="API de gestión de Café de Finca",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(clientes_router, prefix=settings.API_PREFIX)


@app.get("/health", tags=["Salud"])
def health() -> dict[str, str]:
    return {"status": "ok"}
