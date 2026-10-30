"""Acceso a datos de cuentas de usuario."""

from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.modules.auth import models, schemas


def get_user_by_email(db: Session, email: str) -> Optional[models.Cuenta]:
    """Busca una cuenta por correo."""
    return db.query(models.Cuenta).filter(models.Cuenta.correo == email).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.Cuenta:
    """Crea una cuenta validando el rol y hasheando la contraseña."""
    try:
        role_enum = models.UserRole(user.role)
    except ValueError:
        raise ValueError(
            f"Rol inválido. Debe ser uno de: {[r.value for r in models.UserRole]}"
        )

    db_user = models.Cuenta(
        correo=user.email,
        clave=get_password_hash(user.password),
        rol=role_enum,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
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
