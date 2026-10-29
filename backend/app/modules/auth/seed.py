from app.core.database import SessionLocal
from app.modules.auth import services


def main() -> None:
    """Crea el usuario administrador inicial definido en las variables de entorno."""
    with SessionLocal() as db:
        usuario = services.crear_usuario_inicial(db)
        print(f"Administrador disponible: {usuario.username}")


if __name__ == "__main__":
    main()
