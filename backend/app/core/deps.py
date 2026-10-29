from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import TokenInvalidoError, decodificar_token
from app.modules.auth.models import Rol, Usuario

bearer_scheme = HTTPBearer(auto_error=False)

CREDENCIALES_INVALIDAS = "No autenticado o token inválido"


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Valida el access token y devuelve el usuario activo."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=CREDENCIALES_INVALIDAS,
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decodificar_token(credentials.credentials, "access")
        usuario_id = int(payload["sub"])
    except (TokenInvalidoError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=CREDENCIALES_INVALIDAS,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=CREDENCIALES_INVALIDAS,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return usuario


def require_roles(*roles: Rol) -> Callable[..., Usuario]:
    """Dependencia que exige uno de los roles indicados."""

    def dependency(
        usuario: Usuario = Depends(get_current_user),
    ) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para realizar esta acción",
            )
        return usuario

    return dependency
