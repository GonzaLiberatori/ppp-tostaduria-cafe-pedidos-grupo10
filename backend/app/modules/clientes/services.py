"""Reglas de negocio y frontera transaccional del módulo de clientes.

Traduce entre el contrato plano del panel (B2B/B2C, deuda y kilos calculados)
y el modelo canónico ``Persona`` + ``Cliente``. Es la única capa que otros
módulos deben importar.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.clientes import crud
from app.modules.clientes.models import Cliente, Persona, TipoCliente
from app.modules.clientes.schemas import (
    ClientePanelCreate,
    ClientePanelRead,
    ClientePanelUpdate,
)


class ClienteNoEncontrado(Exception):
    """El id recibido no corresponde a ningún cliente."""

    def __init__(self, cliente_id: int) -> None:
        self.cliente_id = cliente_id
        super().__init__(f"No existe un cliente con id {cliente_id}.")


class EmailDeClienteEnUso(Exception):
    """El correo ya pertenece a otra persona."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"El email '{email}' ya está registrado.")


class TelefonoDeClienteEnUso(Exception):
    """El teléfono ya pertenece a otra persona."""

    def __init__(self, telefono: str) -> None:
        self.telefono = telefono
        super().__init__(f"El teléfono '{telefono}' ya está registrado.")


class ClienteConPedidos(Exception):
    """El cliente no se puede borrar porque tiene pedidos asociados."""

    def __init__(self, cliente_id: int) -> None:
        self.cliente_id = cliente_id
        super().__init__(
            f"No se puede eliminar el cliente {cliente_id}: tiene pedidos asociados."
        )


def _dividir_nombre(nombre: str) -> tuple[str, str]:
    """Parte el nombre completo en ``nombre`` y ``apellido``.

    El panel maneja un solo campo y el modelo exige ambos. Para una razón
    social se guarda la primera palabra como nombre y el resto como apellido;
    al leer se vuelven a unir, así que el valor visible no cambia.
    """
    partes = nombre.strip().split(maxsplit=1)
    return partes[0], partes[1] if len(partes) > 1 else ""


def _a_contrato(cliente: Cliente, kilos: Decimal) -> ClientePanelRead:
    """Pasa el ORM al contrato plano del panel."""
    persona = cliente.persona
    saldo = cliente.saldo_cuenta_corriente or Decimal("0")
    tipo = "B2B" if cliente.es_b2b else "B2C"

    return ClientePanelRead(
        id=str(cliente.persona_id),
        nombre=f"{persona.nombre} {persona.apellido}".strip(),
        tipo=tipo,
        telefono=persona.telefono or "",
        email=persona.email or "",
        direccion=cliente.direccion_de_entrega or "",
        kilosComprados=float(kilos),
        tieneDeuda=saldo > 0,
        montoDeuda=float(saldo),
        limiteCredito=(
            float(cliente.limite_credito)
            if cliente.limite_credito is not None
            else None
        ),
        creadoEn=cliente.fecha_alta or datetime.utcnow(),
    )


def _validar_unicidad(
    db: Session,
    email: Optional[str],
    telefono: Optional[str],
    excluir_persona_id: Optional[int] = None,
) -> None:
    """Valida que email y teléfono no estén tomados por otra persona."""
    if email:
        existente = crud.obtener_persona_por_email(db, email)
        if existente and existente.id != excluir_persona_id:
            raise EmailDeClienteEnUso(email)

    if telefono:
        existente = crud.obtener_persona_por_telefono(db, telefono)
        if existente and existente.id != excluir_persona_id:
            raise TelefonoDeClienteEnUso(telefono)


def _tipo_canonico(tipo: str) -> TipoCliente:
    return TipoCliente.MAYORISTA if tipo == "B2B" else TipoCliente.CONSUMIDOR_FINAL


def listar_clientes(db: Session) -> list[ClientePanelRead]:
    """Lista todos los clientes con sus kilos comprados."""
    clientes = crud.listar_clientes(db)
    kilos_por_cliente = crud.kilos_comprados_de_clientes(db)
    return [
        _a_contrato(cliente, kilos_por_cliente.get(cliente.persona_id, Decimal("0")))
        for cliente in clientes
    ]


def obtener_cliente(db: Session, cliente_id: int) -> ClientePanelRead:
    """Lee un cliente por su ``persona_id``."""
    cliente = crud.obtener_cliente(db, cliente_id)
    if cliente is None:
        raise ClienteNoEncontrado(cliente_id)

    return _a_contrato(cliente, crud.kilos_comprados_de_cliente(db, cliente_id))


def crear_cliente(db: Session, datos: ClientePanelCreate) -> ClientePanelRead:
    """Da de alta persona y cliente en una sola transacción."""
    email = datos.email or None
    telefono = datos.telefono or None

    _validar_unicidad(db, email, telefono)

    nombre, apellido = _dividir_nombre(datos.nombre)
    saldo = Decimal("0")
    if datos.tieneDeuda and datos.montoDeuda is not None:
        saldo = datos.montoDeuda

    try:
        persona = Persona(
            nombre=nombre,
            apellido=apellido,
            email=email,
            telefono=telefono,
        )
        db.add(persona)
        db.flush()

        cliente = Cliente(
            persona_id=persona.id,
            tipo=_tipo_canonico(datos.tipo),
            direccion_de_entrega=datos.direccion or None,
            fecha_alta=datetime.utcnow(),
            saldo_cuenta_corriente=saldo,
            limite_credito=datos.limiteCredito,
        )
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
    except Exception:
        db.rollback()
        raise

    return _a_contrato(cliente, Decimal("0"))


def actualizar_cliente(
    db: Session, cliente_id: int, datos: ClientePanelUpdate
) -> ClientePanelRead:
    """Aplica solo los campos enviados con valor."""
    cliente = crud.obtener_cliente(db, cliente_id)
    if cliente is None:
        raise ClienteNoEncontrado(cliente_id)

    persona = cliente.persona
    email = datos.email if datos.email else None
    telefono = datos.telefono if datos.telefono else None

    _validar_unicidad(db, email, telefono, excluir_persona_id=persona.id)

    try:
        if datos.nombre is not None:
            nombre, apellido = _dividir_nombre(datos.nombre)
            persona.nombre = nombre
            persona.apellido = apellido
        if datos.email is not None:
            persona.email = email
        if datos.telefono is not None:
            persona.telefono = telefono
        if datos.tipo is not None:
            cliente.tipo = _tipo_canonico(datos.tipo)
        if datos.direccion is not None:
            cliente.direccion_de_entrega = datos.direccion or None
        if datos.limiteCredito is not None:
            cliente.limite_credito = datos.limiteCredito

        # La deuda del panel es el saldo de la cuenta corriente. El formulario
        # siempre envía montoDeuda, así que ese valor manda cuando está presente.
        if datos.montoDeuda is not None:
            cliente.saldo_cuenta_corriente = (
                datos.montoDeuda if datos.tieneDeuda is not False else Decimal("0")
            )
        elif datos.tieneDeuda is False:
            cliente.saldo_cuenta_corriente = Decimal("0")

        db.commit()
        db.refresh(cliente)
    except Exception:
        db.rollback()
        raise

    return _a_contrato(cliente, crud.kilos_comprados_de_cliente(db, cliente_id))


def eliminar_cliente(db: Session, cliente_id: int) -> None:
    """Borra el cliente y su persona si no tiene pedidos asociados."""
    cliente = crud.obtener_cliente(db, cliente_id)
    if cliente is None:
        raise ClienteNoEncontrado(cliente_id)

    if crud.contar_pedidos_de_cliente(db, cliente_id) > 0:
        raise ClienteConPedidos(cliente_id)

    try:
        persona = cliente.persona
        db.delete(cliente)
        db.flush()
        db.delete(persona)
        db.commit()
    except Exception:
        db.rollback()
        raise
