from sqlalchemy.orm import Session
from typing import Optional
from app.modules.auth import models, schemas
from app.core.security import create_access_token, verify_token


def get_user_by_email(db: Session, email: str) -> Optional[models.Cuenta]:
    return db.query(models.Cuenta).filter(models.Cuenta.correo == email).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.Cuenta:
    # Validar rol
    try:
        role_enum = models.UserRole(user.role)
    except ValueError:
        raise ValueError(f"Rol inválido. Debe ser uno de: {[r.value for r in models.UserRole]}")
    
    db_user = models.Cuenta(
        correo=user.email,
        clave=user.password,
        rol=role_enum
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.Cuenta]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if user.clave != password:
        return None
    return user


def create_token_for_user(user: models.Cuenta) -> str:
    return create_access_token(data={"sub": user.correo, "role": user.rol.value})