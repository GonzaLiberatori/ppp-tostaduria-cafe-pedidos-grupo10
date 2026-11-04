"""Acceso a datos de cuentas de usuario."""

from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.modules.auth import models


def get_user_by_email(db: Session, email: str) -> Optional[models.Cuenta]:
    """Busca una cuenta por correo."""
    return db.query(models.Cuenta).filter(models.Cuenta.correo == email).first()


def crear_cuenta(
    db: Session, correo: str, password: str, rol: models.UserRole
) -> models.Cuenta:
    """Agrega una cuenta a la sesión sin confirmar la transacción.

    El llamador (``AuthService``) es dueño del ``commit`` para poder crear la
    cuenta y su ``Persona``/``Cliente`` en una sola transacción.
    """
    db_user = models.Cuenta(
        correo=correo,
        clave=get_password_hash(password),
        rol=rol,
    )
    db.add(db_user)
    db.flush()
    return db_user


def authenticate_user(
    db: Session, email: str, password: str
) -> Optional[models.Cuenta]:
    """Valida credenciales y devuelve la cuenta si coinciden."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.clave):
        return None
    return user


def create_token_for_user(user: models.Cuenta) -> str:
    """Genera el JWT de acceso para una cuenta."""
    return create_access_token(data={"sub": user.correo, "role": user.rol.value})
