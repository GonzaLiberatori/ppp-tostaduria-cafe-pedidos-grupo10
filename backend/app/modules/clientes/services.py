from decimal import Decimal

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.clientes import crud
from app.modules.clientes.models import Cliente
from app.modules.clientes.schemas import ClienteCreate, ClienteUpdate


class ClienteNoEncontradoError(Exception):
    """No existe un cliente con el id indicado."""


class ClienteConRelacionesError(Exception):
    """El cliente tiene registros asociados y no puede eliminarse."""


class ModificacionDeudaNoPermitidaError(Exception):
    """Un usuario sin permisos intentó modificar la deuda pendiente."""


class DatosInvalidosError(Exception):
    """Datos de entrada inválidos que no detectó Pydantic."""


def _limpiar_texto(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


def listar_clientes(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Cliente]:
    return list(crud.listar_clientes(db, skip=skip, limit=limit))


def obtener_cliente(db: Session, cliente_id: int) -> Cliente:
    cliente = crud.obtener_cliente(db, cliente_id)
    if cliente is None:
        raise ClienteNoEncontradoError
    return cliente


def crear_cliente(db: Session, payload: ClienteCreate) -> Cliente:
    cliente = Cliente(
        nombre=payload.nombre,
        tipo=payload.tipo,
        kilos_comprados=payload.kilos_comprados,
        deuda_pendiente=payload.deuda_pendiente,
        telefono=_limpiar_texto(payload.telefono),
        email=str(payload.email) if payload.email else None,
        direccion=_limpiar_texto(payload.direccion),
    )

    try:
        crud.crear_cliente(db, cliente)
        db.commit()
        db.refresh(cliente)
    except SQLAlchemyError:
        db.rollback()
        raise

    return cliente


def actualizar_cliente(
    db: Session,
    cliente_id: int,
    payload: ClienteUpdate,
    *,
    es_admin: bool,
) -> Cliente:
    cliente = obtener_cliente(db, cliente_id)
    campos = payload.model_fields_set

    if "deuda_pendiente" in campos and not es_admin:
        raise ModificacionDeudaNoPermitidaError

    cambios: dict[str, object] = {}

    if "nombre" in campos:
        if payload.nombre is None:
            raise DatosInvalidosError("El nombre no puede ser nulo")
        cambios["nombre"] = payload.nombre

    if "tipo" in campos and payload.tipo is not None:
        cambios["tipo"] = payload.tipo

    if "kilos_comprados" in campos and payload.kilos_comprados is not None:
        cambios["kilos_comprados"] = payload.kilos_comprados

    if "deuda_pendiente" in campos and es_admin:
        cambios["deuda_pendiente"] = (
            payload.deuda_pendiente
            if payload.deuda_pendiente is not None
            else Decimal("0")
        )

    if "telefono" in campos:
        cambios["telefono"] = _limpiar_texto(payload.telefono)

    if "email" in campos:
        cambios["email"] = str(payload.email) if payload.email else None

    if "direccion" in campos:
        cambios["direccion"] = _limpiar_texto(payload.direccion)

    try:
        crud.actualizar_cliente(db, cliente, cambios)
        db.commit()
        db.refresh(cliente)
    except SQLAlchemyError:
        db.rollback()
        raise

    return cliente


def eliminar_cliente(db: Session, cliente_id: int) -> None:
    cliente = obtener_cliente(db, cliente_id)

    if crud.tablas_relacionadas(db, cliente_id):
        raise ClienteConRelacionesError

    try:
        crud.eliminar_cliente(db, cliente)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ClienteConRelacionesError from exc
    except SQLAlchemyError:
        db.rollback()
        raise
