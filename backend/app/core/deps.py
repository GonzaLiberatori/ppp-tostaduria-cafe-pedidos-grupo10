"""Dependencias compartidas de la aplicación.

Provee la sesión de base de datos y la autenticación JWT que se inyectan en los
endpoints de FastAPI vía ``Depends()``.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.schemas import TokenData

# ``get_db`` se reexporta desde acá para que los módulos que ya lo importaban
# desde ``app.core.deps`` sigan funcionando.
__all__ = ["get_db", "get_current_user", "oauth2_scheme"]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> TokenData:
    """Valida el token JWT y devuelve la identidad del usuario autenticado."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    return token_data
