from sqlalchemy.orm import Session
from typing import Optional
from app.modules.auth import models, schemas, crud
from app.modules.clientes.models import Cliente, Persona
from app.core.security import create_access_token


# Traducción del rol canónico al rol que usa el frontend.
ROLES_FRONTEND = {
    models.UserRole.ADMINISTRADOR: "admin",
    models.UserRole.CAJERO: "vendedor",
    models.UserRole.OPERARIO: "empleado",
    models.UserRole.CLIENTE: "cliente",
}


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

    def obtener_perfil(self, email: str) -> schemas.UserMeResponse:
        """Devuelve el perfil del usuario, vinculando la cuenta con su persona.

        La relación es ``Persona.cuenta_id``; si esa persona además es cliente,
        se expone su ``persona_id`` como ``clienteId`` para el portal B2C.
        """
        cuenta = crud.get_user_by_email(self.db, email)
        if not cuenta:
            raise ValueError("Usuario no encontrado")

        persona = (
            self.db.query(Persona)
            .filter(Persona.cuenta_id == cuenta.id)
            .first()
        )
        cliente = (
            self.db.query(Cliente)
            .filter(Cliente.persona_id == persona.id)
            .first()
            if persona
            else None
        )

        nombre = (
            f"{persona.nombre} {persona.apellido}".strip()
            if persona
            else cuenta.correo
        )

        return schemas.UserMeResponse(
            id=cuenta.id,
            correo=cuenta.correo,
            rol=cuenta.rol.value,
            role=ROLES_FRONTEND.get(cuenta.rol, "cliente"),
            nombre=nombre,
            clienteId=str(cliente.persona_id) if cliente else None,
        )