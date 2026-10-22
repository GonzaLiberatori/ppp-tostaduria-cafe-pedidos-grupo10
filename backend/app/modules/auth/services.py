from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.auth.models import Usuario
from app.core.security import verify_password, get_password_hash


class AuthService:
    """Servicio de autenticación."""

    def get_by_id(self, user_id: int, session: Session) -> Optional[Usuario]:
        """Obtiene usuario por ID."""
        stmt = select(Usuario).where(Usuario.id == user_id)
        return session.execute(stmt).scalar_one_or_none()

    def get_by_username(self, username: str, session: Session) -> Optional[Usuario]:
        """Obtiene usuario por username."""
        stmt = select(Usuario).where(Usuario.username == username)
        return session.execute(stmt).scalar_one_or_none()

    def authenticate(self, username: str, password: str, session: Session) -> Optional[Usuario]:
        """Autentica usuario con username y password."""
        user = self.get_by_username(username, session)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def create_user(
        self,
        session: Session,
        username: str,
        email: str,
        password: str,
        rol: str = "operador",
    ) -> Usuario:
        """Crea un nuevo usuario."""
        user = Usuario(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            rol=rol,
        )
        session.add(user)
        session.flush()
        return user