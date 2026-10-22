from pydantic import BaseModel, EmailStr
from typing import Optional


class UsuarioLogin(BaseModel):
    username: str
    password: str


class UsuarioCreate(UsuarioLogin):
    email: EmailStr
    rol: str = "operador"


class UsuarioRead(BaseModel):
    id: int
    username: str
    email: str
    rol: str
    activo: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str