from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_account, get_current_user
from app.modules.auth import schemas, services
from app.modules.auth.models import Cuenta, UserRole
from app.modules.auth.schemas import TokenData


router = APIRouter(prefix="/auth", tags=["Autenticación"])


def get_auth_service(db: Session = Depends(get_db)) -> services.AuthService:
    return services.AuthService(db)


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user: schemas.UserCreate,
    service: services.AuthService = Depends(get_auth_service)
):
    """Registro público: siempre crea una cuenta con rol Cliente."""
    try:
        db_user = service.register(user)
        return db_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/usuarios",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_usuario_interno(
    datos: schemas.UserAdminCreate,
    cuenta: Cuenta = Depends(get_current_account),
    service: services.AuthService = Depends(get_auth_service),
):
    """Crea una cuenta con rol interno. Solo Administrador."""
    if cuenta.rol is not UserRole.ADMINISTRADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un Administrador puede crear cuentas internas.",
        )
    try:
        return service.crear_cuenta_interna(datos)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=schemas.Token)
def login(
    login_data: schemas.UserLogin,
    service: services.AuthService = Depends(get_auth_service)
):
    try:
        token = service.login(login_data)
        return token
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=schemas.UserMeResponse)
def me(
    current_user: TokenData = Depends(get_current_user),
    service: services.AuthService = Depends(get_auth_service),
):
    """Devuelve el perfil del usuario autenticado y su rol para el panel."""
    try:
        return service.obtener_perfil(current_user.email)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))