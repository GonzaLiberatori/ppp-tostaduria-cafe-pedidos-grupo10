from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    TokenInvalidoError,
    crear_access_token,
    crear_refresh_token,
    decodificar_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.auth import crud
from app.modules.auth.models import Rol, Usuario


class CredencialesInvalidasError(Exception):
    """Usuario inexistente, inactivo o contraseña incorrecta."""


class RefreshInvalidoError(Exception):
    """Refresh token ausente, vencido, revocado o manipulado."""


def _ahora_utc_naive() -> datetime:
    """MySQL guarda DATETIME sin zona horaria; usamos UTC naive."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def autenticar(db: Session, username: str, password: str) -> Usuario:
    usuario = crud.obtener_usuario_por_username(db, username.strip())
    if usuario is None or not usuario.activo:
        raise CredencialesInvalidasError

    if not verify_password(password, usuario.password_hash):
        raise CredencialesInvalidasError

    return usuario


def _crear_par_de_tokens(
    db: Session,
    usuario: Usuario,
) -> tuple[str, str, int]:
    access_token, _ = crear_access_token(usuario.id, usuario.rol.value)
    refresh_token, jti, expira_en = crear_refresh_token(
        usuario.id, usuario.rol.value
    )

    crud.crear_refresh_token(
        db,
        usuario_id=usuario.id,
        jti=jti,
        token_hash=hash_token(refresh_token),
        expira_en=expira_en.replace(tzinfo=None),
    )

    return (
        access_token,
        refresh_token,
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def emitir_tokens(db: Session, usuario: Usuario) -> tuple[str, str, int]:
    """Emite un access token y un refresh token persistido."""
    try:
        tokens = _crear_par_de_tokens(db, usuario)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return tokens


def refrescar_tokens(db: Session, refresh_token: str) -> tuple[str, str, int]:
    """Valida, rota y persiste un nuevo par de tokens."""
    try:
        payload = decodificar_token(refresh_token, "refresh")
    except TokenInvalidoError as exc:
        raise RefreshInvalidoError from exc

    jti = payload.get("jti")
    if not isinstance(jti, str):
        raise RefreshInvalidoError

    registro = crud.obtener_refresh_por_jti(db, jti)
    if registro is None:
        raise RefreshInvalidoError

    # Reutilización de un token ya rotado: se revoca toda la familia del usuario.
    if registro.revocado_en is not None:
        crud.revocar_tokens_usuario(db, registro.usuario_id, _ahora_utc_naive())
        db.commit()
        raise RefreshInvalidoError

    if registro.expira_en <= _ahora_utc_naive():
        raise RefreshInvalidoError

    if registro.token_hash != hash_token(refresh_token):
        raise RefreshInvalidoError

    usuario = crud.obtener_usuario_por_id(db, registro.usuario_id)
    if usuario is None or not usuario.activo:
        raise RefreshInvalidoError

    try:
        nuevo_refresh, nuevo_jti, expira_en = crear_refresh_token(
            usuario.id, usuario.rol.value
        )

        registro.revocado_en = _ahora_utc_naive()
        registro.reemplazado_por = nuevo_jti
        crud.crear_refresh_token(
            db,
            usuario_id=usuario.id,
            jti=nuevo_jti,
            token_hash=hash_token(nuevo_refresh),
            expira_en=expira_en.replace(tzinfo=None),
        )
        access_nuevo, _ = crear_access_token(usuario.id, usuario.rol.value)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return (
        access_nuevo,
        nuevo_refresh,
        settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def revocar_refresh(db: Session, refresh_token: str) -> None:
    """Revoca el refresh token indicado. Es idempotente."""
    try:
        payload = decodificar_token(refresh_token, "refresh")
    except TokenInvalidoError:
        return

    jti = payload.get("jti")
    if not isinstance(jti, str):
        return

    registro = crud.obtener_refresh_por_jti(db, jti)
    if registro is None or registro.revocado_en is not None:
        return

    try:
        registro.revocado_en = _ahora_utc_naive()
        db.commit()
    except Exception:
        db.rollback()
        raise


def crear_usuario_inicial(db: Session) -> Usuario:
    """Crea el administrador inicial si todavía no existe."""
    usuario = crud.obtener_usuario_por_username(db, settings.ADMIN_USERNAME)
    if usuario is not None:
        return usuario

    try:
        usuario = crud.crear_usuario(
            db,
            username=settings.ADMIN_USERNAME,
            nombre=settings.ADMIN_NOMBRE,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            rol=Rol.ADMIN,
        )
        db.commit()
        db.refresh(usuario)
    except IntegrityError:
        db.rollback()
        raise

    return usuario
