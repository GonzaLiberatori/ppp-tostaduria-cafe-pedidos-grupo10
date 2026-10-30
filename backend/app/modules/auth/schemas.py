from pydantic import BaseModel, field_validator
from typing import Optional


class TokenData(BaseModel):
    email: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    password: str
    role: str

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = ['Administrador', 'Cajero', 'Operario', 'Cliente']
        if v not in valid_roles:
            raise ValueError(f"Rol inválido. Debe ser uno de: {valid_roles}")
        return v


class UserResponse(BaseModel):
    id: int
    correo: str
    rol: str

    class Config:
        from_attributes = True


class UserMeResponse(BaseModel):
    """Perfil del usuario autenticado para el panel.

    ``rol`` es el valor canónico de la base (Administrador, Cajero, Operario,
    Cliente) y ``role`` es el alias que consume el frontend (admin, vendedor,
    empleado, cliente). ``clienteId`` solo viene poblado para clientes.
    """

    id: int
    correo: str
    rol: str
    role: str
    nombre: str
    clienteId: Optional[str] = None