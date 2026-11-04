from datetime import datetime

from sqlalchemy.orm import Session
from typing import Optional

from app.modules.auth import models, schemas, crud
from app.modules.clientes.models import Cliente, Persona, TipoCliente


# Traducción del rol canónico al rol que usa el frontend.
ROLES_FRONTEND = {
    models.UserRole.ADMINISTRADOR: "admin",
    models.UserRole.CAJERO: "vendedor",
    models.UserRole.OPERARIO: "empleado",
    models.UserRole.CLIENTE: "cliente",
}


def _dividir_nombre(nombre: str) -> tuple[str, str]:
    """Parte un nombre completo en ``nombre`` y ``apellido``."""
    partes = (nombre or "").strip().split(maxsplit=1)
    return (partes[0] if partes else ""), (partes[1] if len(partes) > 1 else "")


def _nombre_por_defecto(correo: str) -> str:
    """Deriva un nombre visible a partir del correo cuando no se envía uno."""
    return correo.split("@", 1)[0]


def crear_cuenta_vinculada(
    db: Session,
    correo: str,
    password: str,
    rol: models.UserRole = models.UserRole.CLIENTE,
) -> models.Cuenta:
    """Crea una cuenta sin confirmar, para vincularla a una persona existente.

    La usa el módulo ``clientes`` cuando un Administrador da de alta un cliente
    con acceso al portal: la cuenta, la persona y el cliente deben confirmarse
    en una única transacción del llamador.
    """
    if crud.get_user_by_email(db, correo):
        raise ValueError("El email ya está registrado")
    return crud.crear_cuenta(db, correo, password, rol)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def _crear_cuenta_con_persona(
        self,
        correo: str,
        password: str,
        rol: models.UserRole,
        nombre: Optional[str],
        telefono: Optional[str],
        crear_cliente: bool,
    ) -> models.Cuenta:
        """Crea cuenta + persona (y cliente si corresponde) en una transacción.

        Si ya existe una ``Persona`` con ese correo (por ejemplo, un cliente
        cargado desde el panel), se vincula la cuenta nueva a esa persona en
        lugar de duplicarla.
        """
        if crud.get_user_by_email(self.db, correo):
            raise ValueError("El email ya está registrado")

        try:
            cuenta = crud.crear_cuenta(self.db, correo, password, rol)

            persona = (
                self.db.query(Persona)
                .filter(Persona.email == correo)
                .first()
            )

            if persona is not None:
                if persona.cuenta_id is not None:
                    raise ValueError(
                        "Ya existe una cuenta vinculada a este email"
                    )
                persona.cuenta_id = cuenta.id
                if telefono and not persona.telefono:
                    persona.telefono = telefono
            else:
                nombre_persona, apellido = _dividir_nombre(
                    nombre or _nombre_por_defecto(correo)
                )
                persona = Persona(
                    nombre=nombre_persona,
                    apellido=apellido,
                    email=correo,
                    telefono=telefono,
                    cuenta_id=cuenta.id,
                )
                self.db.add(persona)
                self.db.flush()

            if crear_cliente:
                existe_cliente = (
                    self.db.query(Cliente)
                    .filter(Cliente.persona_id == persona.id)
                    .first()
                )
                if existe_cliente is None:
                    self.db.add(
                        Cliente(
                            persona_id=persona.id,
                            tipo=TipoCliente.CONSUMIDOR_FINAL,
                            fecha_alta=datetime.utcnow(),
                        )
                    )

            self.db.commit()
            self.db.refresh(cuenta)
            return cuenta
        except Exception:
            self.db.rollback()
            raise

    def register(self, user_data: schemas.UserCreate) -> models.Cuenta:
        """Registro público: siempre crea una cuenta ``Cliente``.

        El rol enviado por el cliente se ignora a propósito. Así el endpoint
        público no puede usarse para escalar privilegios.
        """
        return self._crear_cuenta_con_persona(
            correo=user_data.email,
            password=user_data.password,
            rol=models.UserRole.CLIENTE,
            nombre=user_data.nombre,
            telefono=user_data.telefono,
            crear_cliente=True,
        )

    def crear_cuenta_interna(
        self, datos: schemas.UserAdminCreate
    ) -> models.Cuenta:
        """Alta de cuentas con cualquier rol desde el panel interno."""
        try:
            rol = models.UserRole(datos.role)
        except ValueError:
            raise ValueError(
                f"Rol inválido. Debe ser uno de: {[r.value for r in models.UserRole]}"
            )

        return self._crear_cuenta_con_persona(
            correo=datos.email,
            password=datos.password,
            rol=rol,
            nombre=datos.nombre,
            telefono=datos.telefono,
            crear_cliente=rol is models.UserRole.CLIENTE,
        )

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