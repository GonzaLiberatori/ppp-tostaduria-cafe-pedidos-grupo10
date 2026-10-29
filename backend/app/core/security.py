import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

TipoToken = Literal["access", "refresh"]

password_hash = PasswordHash.recommended()


class TokenInvalidoError(Exception):
    """El token no es válido, expiró o no corresponde al tipo esperado."""


def hash_password(password: str) -> str:
    """Genera el hash Argon2 de una contraseña."""
    return password_hash.hash(password)


def verify_password(password: str, password_hash_almacenado: str) -> bool:
    """Verifica una contraseña contra su hash almacenado."""
    return password_hash.verify(password, password_hash_almacenado)


def hash_token(token: str) -> str:
    """Hash determinístico para almacenar refresh tokens sin el valor original."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _crear_token(
    usuario_id: int,
    rol: str,
    tipo: TipoToken,
    expira_en: datetime,
) -> tuple[str, str, datetime]:
    ahora = datetime.now(timezone.utc)
    jti = uuid4().hex
    payload: dict[str, Any] = {
        "sub": str(usuario_id),
        "rol": rol,
        "type": tipo,
        "jti": jti,
        "iat": ahora,
        "exp": expira_en,
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, jti, expira_en


def crear_access_token(usuario_id: int, rol: str) -> tuple[str, datetime]:
    """Crea un access token de corta duración."""
    expira_en = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    token, _, expira = _crear_token(usuario_id, rol, "access", expira_en)
    return token, expira


def crear_refresh_token(usuario_id: int, rol: str) -> tuple[str, str, datetime]:
    """Crea un refresh token y devuelve también su jti y vencimiento."""
    expira_en = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    return _crear_token(usuario_id, rol, "refresh", expira_en)


def decodificar_token(token: str, tipo: TipoToken) -> dict[str, Any]:
    """Valida firma, expiración y tipo del token."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "jti", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenInvalidoError("Token inválido o expirado") from exc

    if payload.get("type") != tipo:
        raise TokenInvalidoError("Tipo de token incorrecto")

    return payload
