from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.auth.models import RefreshToken, Rol, Usuario


def obtener_usuario_por_username(db: Session, username: str) -> Usuario | None:
    return db.scalars(
        select(Usuario).where(Usuario.username == username)
    ).first()


def obtener_usuario_por_id(db: Session, usuario_id: int) -> Usuario | None:
    return db.get(Usuario, usuario_id)


def crear_usuario(
    db: Session,
    *,
    username: str,
    nombre: str,
    password_hash: str,
    rol: Rol,
    email: str | None = None,
) -> Usuario:
    usuario = Usuario(
        username=username,
        nombre=nombre,
        email=email,
        password_hash=password_hash,
        rol=rol,
    )
    db.add(usuario)
    db.flush()
    return usuario


def crear_refresh_token(
    db: Session,
    *,
    usuario_id: int,
    jti: str,
    token_hash: str,
    expira_en: datetime,
) -> RefreshToken:
    registro = RefreshToken(
        usuario_id=usuario_id,
        jti=jti,
        token_hash=token_hash,
        expira_en=expira_en,
    )
    db.add(registro)
    db.flush()
    return registro


def obtener_refresh_por_jti(db: Session, jti: str) -> RefreshToken | None:
    return db.scalars(
        select(RefreshToken).where(RefreshToken.jti == jti)
    ).first()


def revocar_tokens_usuario(
    db: Session,
    usuario_id: int,
    revocado_en: datetime,
) -> None:
    db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.usuario_id == usuario_id,
            RefreshToken.revocado_en.is_(None),
        )
        .values(revocado_en=revocado_en)
    )
