"""Dependencias compartidas de la aplicación.

Provee la sesión de base de datos, la autenticación JWT y otras dependencias
comunes que se inyectan en los endpoints de FastAPI vía ``Depends()``.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.models import Usuario
from app.modules.auth.services import AuthService

# ``get_db`` se reexporta desde acá para que los módulos que ya lo importaban
# desde ``app.core.deps`` sigan funcionando.
__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "get_current_admin_user",
    "oauth2_scheme",
]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")
auth_service = AuthService()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Obtiene el usuario actual desde el token JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = auth_service.get_by_id(int(user_id), db)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """Verifica que el usuario esté activo."""
    if not getattr(current_user, "activo", True):
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user


def get_current_admin_user(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """Verifica que el usuario sea administrador."""
    if getattr(current_user, "rol", None) != "admin":
        raise HTTPException(status_code=403, detail="Permisos insuficientes")
    return current_user
