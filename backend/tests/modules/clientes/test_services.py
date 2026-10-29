"""Tests de clientes: CRUD, RBAC, deuda y borrado seguro."""

from collections.abc import Callable
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import ForeignKey, Integer, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.database import Base
from app.modules.auth.models import Usuario
from app.modules.clientes.models import Cliente
from tests.conftest import API

CAMPOS_ADMIN = {
    "id",
    "nombre",
    "tipo",
    "kilosComprados",
    "tieneDeuda",
    "montoDeuda",
    "telefono",
    "email",
    "direccion",
    "creadoEn",
}

CAMPOS_EMPLEADO = {
    "id",
    "nombre",
    "tipo",
    "kilosComprados",
    "telefono",
    "email",
    "direccion",
    "creadoEn",
}

DATOS_CLIENTE = {
    "nombre": "Café Central",
    "tipo": "B2B",
    "kilosComprados": 12.5,
    "montoDeuda": 250.75,
    "telefono": "555-1234",
    "email": "central@example.com",
    "direccion": "Calle 1 # 2-3",
}


class PedidoProbe(Base):
    """Tabla de prueba para validar la protección de integridad referencial.

    Simula la futura FK de ``pedidos`` hacia ``clientes`` sin tocar el módulo
    de pedidos, que por ahora está vacío.
    """

    __tablename__ = "pedidos_probe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id"),
        nullable=False,
    )


@pytest.fixture()
def crear_cliente(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
) -> Callable[..., dict[str, object]]:
    """Crea clientes como ADMIN y devuelve el JSON de respuesta."""

    headers = auth_headers(usuario_admin)

    def _crear(**cambios: object) -> dict[str, object]:
        payload = {**DATOS_CLIENTE, **cambios}
        respuesta = api.post(f"{API}/clientes", json=payload, headers=headers)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear


def test_admin_crea_cliente_con_campos_camelcase(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
) -> None:
    respuesta = api.post(
        f"{API}/clientes",
        json=DATOS_CLIENTE,
        headers=auth_headers(usuario_admin),
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert set(cuerpo) == CAMPOS_ADMIN
    assert cuerpo["nombre"] == "Café Central"
    assert cuerpo["tipo"] == "B2B"
    assert cuerpo["kilosComprados"] == 12.5
    assert cuerpo["montoDeuda"] == 250.75
    assert cuerpo["tieneDeuda"] is True
    assert cuerpo["email"] == "central@example.com"


def test_listar_y_obtener_cliente(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
    crear_cliente: Callable[..., dict[str, object]],
) -> None:
    primero = crear_cliente(nombre="Cliente A", montoDeuda=0)
    segundo = crear_cliente(nombre="Cliente B")
    headers = auth_headers(usuario_admin)

    listado = api.get(f"{API}/clientes", headers=headers)
    assert listado.status_code == 200
    ids = [cliente["id"] for cliente in listado.json()]
    assert ids == [primero["id"], segundo["id"]]

    detalle = api.get(f"{API}/clientes/{segundo['id']}", headers=headers)
    assert detalle.status_code == 200
    assert detalle.json()["montoDeuda"] == 250.75


def test_paginacion_de_clientes(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
    crear_cliente: Callable[..., dict[str, object]],
) -> None:
    for indice in range(3):
        crear_cliente(nombre=f"Cliente {indice}", montoDeuda=0)

    headers = auth_headers(usuario_admin)
    respuesta = api.get(
        f"{API}/clientes?skip=1&limit=1",
        headers=headers,
    )

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    assert respuesta.json()[0]["nombre"] == "Cliente 1"

    invalida = api.get(f"{API}/clientes?skip=-1", headers=headers)
    assert invalida.status_code == 422


def test_admin_actualiza_la_deuda(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
    crear_cliente: Callable[..., dict[str, object]],
) -> None:
    cliente = crear_cliente()

    respuesta = api.put(
        f"{API}/clientes/{cliente['id']}",
        json={"montoDeuda": 0},
        headers=auth_headers(usuario_admin),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["montoDeuda"] == 0.0
    assert respuesta.json()["tieneDeuda"] is False


def test_admin_puede_registrar_saldo_a_favor(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
    crear_cliente: Callable[..., dict[str, object]],
) -> None:
    headers = auth_headers(usuario_admin)

    creado = api.post(
        f"{API}/clientes",
        json={
            "nombre": "Cliente con crédito",
            "kilosComprados": 1,
            "montoDeuda": -50000,
        },
        headers=headers,
    )
    assert creado.status_code == 201
    assert creado.json()["montoDeuda"] == -50000.0
    assert creado.json()["tieneDeuda"] is False

    actualizado = api.put(
        f"{API}/clientes/{creado.json()['id']}",
        json={"montoDeuda": "-75000.50"},
        headers=headers,
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["montoDeuda"] == -75000.5
    assert actualizado.json()["tieneDeuda"] is False

    detalle = api.get(
        f"{API}/clientes/{creado.json()['id']}",
        headers=headers,
    )
    assert detalle.json()["montoDeuda"] == -75000.5


def test_empleado_sigue_sin_ver_el_saldo_a_favor(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_empleado: Usuario,
    crear_cliente: Callable[..., dict[str, object]],
) -> None:
    cliente = crear_cliente(montoDeuda=-50000)

    detalle = api.get(
        f"{API}/clientes/{cliente['id']}",
        headers=auth_headers(usuario_empleado),
    )

    assert detalle.status_code == 200
    assert "montoDeuda" not in detalle.text
    assert "-50000" not in detalle.text


def test_admin_puede_usar_alias_deuda_pendiente(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
    crear_cliente: Callable[..., dict[str, object]],
) -> None:
    cliente = crear_cliente(montoDeuda=0)

    respuesta = api.put(
        f"{API}/clientes/{cliente['id']}",
        json={"deudaPendiente": 99.5},
        headers=auth_headers(usuario_admin),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["montoDeuda"] == 99.5


def test_empleado_no_ve_la_deuda(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
    usuario_empleado: Usuario,
    crear_cliente: Callable[..., dict[str, object]],
) -> None:
    cliente = crear_cliente()
    headers = auth_headers(usuario_empleado)

    listado = api.get(f"{API}/clientes", headers=headers)
    detalle = api.get(f"{API}/clientes/{cliente['id']}", headers=headers)
    creado = api.post(
        f"{API}/clientes",
        json={"nombre": "Cliente sin deuda"},
        headers=headers,
    )
    actualizado = api.put(
        f"{API}/clientes/{cliente['id']}",
        json={"nombre": "Café Central Renombrado"},
        headers=headers,
    )

    assert listado.status_code == 200
    assert detalle.status_code == 200
    assert creado.status_code == 201
    assert actualizado.status_code == 200

    for respuesta in (listado, detalle, creado, actualizado):
        clientes = respuesta.json()
        if isinstance(clientes, list):
            clientes = clientes[0]
        assert set(clientes) == CAMPOS_EMPLEADO
        assert "250.75" not in respuesta.text
        assert "montoDeuda" not in respuesta.text


def test_empleado_no_puede_enviar_deuda_al_crear(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
    usuario_empleado: Usuario,
) -> None:
    respuesta = api.post(
        f"{API}/clientes",
        json={
            "nombre": "Intento de deuda",
            "montoDeuda": "999.99-secreto",
        },
        headers=auth_headers(usuario_empleado),
    )

    assert respuesta.status_code == 403
    assert "999.99-secreto" not in respuesta.text

    listado = api.get(
        f"{API}/clientes",
        headers=auth_headers(usuario_admin),
    )
    assert listado.json() == []


@pytest.mark.parametrize(
    "campo",
    ["montoDeuda", "monto_deuda", "deudaPendiente", "deuda_pendiente"],
)
def test_empleado_no_puede_modificar_deuda_por_ningun_alias(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_empleado: Usuario,
    crear_cliente: Callable[..., dict[str, object]],
    campo: str,
) -> None:
    cliente = crear_cliente()

    respuesta = api.put(
        f"{API}/clientes/{cliente['id']}",
        json={"nombre": "Cambio", campo: 0},
        headers=auth_headers(usuario_empleado),
    )

    assert respuesta.status_code == 403
    assert "250.75" not in respuesta.text


def test_empleado_actualiza_sin_alterar_la_deuda(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
    usuario_empleado: Usuario,
    crear_cliente: Callable[..., dict[str, object]],
) -> None:
    cliente = crear_cliente()

    actualizado = api.put(
        f"{API}/clientes/{cliente['id']}",
        json={"nombre": "Café Central Renombrado", "kilosComprados": 20},
        headers=auth_headers(usuario_empleado),
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["nombre"] == "Café Central Renombrado"

    detalle = api.get(
        f"{API}/clientes/{cliente['id']}",
        headers=auth_headers(usuario_admin),
    )
    assert detalle.json()["montoDeuda"] == 250.75


def test_vendedor_no_tiene_acceso_a_clientes(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
    usuario_vendedor: Usuario,
    crear_cliente: Callable[..., dict[str, object]],
) -> None:
    cliente = crear_cliente()
    headers = auth_headers(usuario_vendedor)

    respuestas = [
        api.get(f"{API}/clientes", headers=headers),
        api.get(f"{API}/clientes/{cliente['id']}", headers=headers),
        api.post(
            f"{API}/clientes",
            json={"nombre": "No permitido"},
            headers=headers,
        ),
        api.put(
            f"{API}/clientes/{cliente['id']}",
            json={"nombre": "No permitido"},
            headers=headers,
        ),
        api.delete(f"{API}/clientes/{cliente['id']}", headers=headers),
    ]

    assert [respuesta.status_code for respuesta in respuestas] == [403] * 5


@pytest.mark.parametrize(
    ("metodo", "ruta", "payload"),
    [
        ("get", f"{API}/clientes", None),
        ("post", f"{API}/clientes", {"nombre": "Sin token"}),
        ("get", f"{API}/clientes/1", None),
        ("put", f"{API}/clientes/1", {"nombre": "Sin token"}),
        ("delete", f"{API}/clientes/1", None),
    ],
)
def test_clientes_sin_autenticacion_devuelve_401(
    api: TestClient,
    metodo: str,
    ruta: str,
    payload: dict[str, str] | None,
) -> None:
    if payload is None:
        respuesta = getattr(api, metodo)(ruta)
    else:
        respuesta = getattr(api, metodo)(ruta, json=payload)
    assert respuesta.status_code == 401


def test_token_manipulado_devuelve_401(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
) -> None:
    headers = auth_headers(usuario_admin)
    headers["Authorization"] += "x"

    assert api.get(f"{API}/clientes", headers=headers).status_code == 401


@pytest.mark.parametrize(
    "cambios",
    [
        {"kilosComprados": -0.01},
        {"nombre": "   "},
        {"tipo": "MAYORISTA"},
        {"email": "correo-invalido"},
        {"kilosComprados": "mucho"},
    ],
)
def test_datos_invalidos_devuelven_422(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
    cambios: dict[str, object],
) -> None:
    respuesta = api.post(
        f"{API}/clientes",
        json={**DATOS_CLIENTE, **cambios},
        headers=auth_headers(usuario_admin),
    )
    assert respuesta.status_code == 422


def test_actualizar_cliente_inexistente_devuelve_404(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
) -> None:
    respuesta = api.put(
        f"{API}/clientes/999",
        json={"nombre": "Fantasma"},
        headers=auth_headers(usuario_admin),
    )
    assert respuesta.status_code == 404


def test_eliminar_cliente_sin_relaciones(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
    crear_cliente: Callable[..., dict[str, object]],
) -> None:
    cliente = crear_cliente()
    headers = auth_headers(usuario_admin)

    borrado = api.delete(f"{API}/clientes/{cliente['id']}", headers=headers)
    assert borrado.status_code == 204
    assert api.get(f"{API}/clientes/{cliente['id']}", headers=headers).status_code == 404
    assert api.delete(f"{API}/clientes/{cliente['id']}", headers=headers).status_code == 404


def test_no_elimina_cliente_con_registros_asociados(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
    crear_cliente: Callable[..., dict[str, object]],
    db: Session,
) -> None:
    cliente = crear_cliente()
    db.add(PedidoProbe(cliente_id=int(cliente["id"])))
    db.commit()

    respuesta = api.delete(
        f"{API}/clientes/{cliente['id']}",
        headers=auth_headers(usuario_admin),
    )

    assert respuesta.status_code == 409
    assert "registros asociados" in respuesta.json()["detail"]
    assert db.scalar(select(PedidoProbe)) is not None


def test_empleado_puede_eliminar_cliente_sin_relaciones(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_empleado: Usuario,
    crear_cliente: Callable[..., dict[str, object]],
) -> None:
    cliente = crear_cliente()

    respuesta = api.delete(
        f"{API}/clientes/{cliente['id']}",
        headers=auth_headers(usuario_empleado),
    )
    assert respuesta.status_code == 204


def test_la_base_permite_saldo_a_favor(db: Session) -> None:
    cliente = Cliente(
        nombre="Saldo a favor",
        deuda_pendiente=Decimal("-0.01"),
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)

    assert cliente.deuda_pendiente == Decimal("-0.01")
    assert cliente.tiene_deuda is False


def test_la_base_rechaza_kilos_negativos(db: Session) -> None:
    db.add(
        Cliente(
            nombre="Kilos negativos",
            kilos_comprados=Decimal("-1"),
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_la_deuda_se_guarda_como_decimal(
    api: TestClient,
    auth_headers: Callable[..., dict[str, str]],
    usuario_admin: Usuario,
    db: Session,
) -> None:
    respuesta = api.post(
        f"{API}/clientes",
        json={"nombre": "Decimal", "montoDeuda": "1234.56"},
        headers=auth_headers(usuario_admin),
    )

    assert respuesta.status_code == 201
    cliente = db.get(Cliente, respuesta.json()["id"])
    assert cliente is not None
    assert str(cliente.deuda_pendiente) == "1234.56"
    assert f"{cliente.deuda_pendiente:.2f}" == "1234.56"
