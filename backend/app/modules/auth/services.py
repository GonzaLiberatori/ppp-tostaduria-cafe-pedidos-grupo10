from sqlalchemy.orm import Session
from typing import Optional
from app.modules.auth import models, schemas, crud
from app.core.security import create_access_token


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, user_data: schemas.UserCreate) -> models.Cuenta:
        existing = crud.get_user_by_email(self.db, user_data.email)
        if existing:
            raise ValueError("El email ya está registrado")
        return crud.create_user(self.db, user_data)

    def login(self, login_data: schemas.UserLogin) -> schemas.Token:
        user = crud.authenticate_user(self.db, login_data.email, login_data.password)
        if not user:
            raise ValueError("Credenciales inválidas")
        access_token = crud.create_token_for_user(user)
        return schemas.Token(access_token=access_token, token_type="bearer")