# Contexto del Proyecto: Café de Finca (MVP 1)

## Stack Tecnológico
- **Frontend:** React (SPA)
- **Backend:** Python con FastAPI (API RESTful asíncrona)
- **Capa de Datos:** SQLAlchemy (ORM)
- **Base de Datos:** MySQL
- **Automatización:** Sistema de tareas programadas (ej. APScheduler) para envíos agendados.

## Módulos Principales (Alcance del MVP 1)
1. **Autenticación y Roles (RBAC):** Gestión de accesos con JWT. Roles: Administrador, Operario, Cajero.
2. **Inventario Dual:** Trazabilidad estricta diferenciando "Café Verde" (Materia prima) de "Café Tostado" (Producto terminado).
3. **Producción (Tueste):** Registro de órdenes de tueste, calculando mermas y conversión automática de kilos de café verde a tostado.
4. **Clientes y Cuentas Corrientes:** Gestión de deudas, historial comercial y límites de crédito.
5. **Pedidos y Ventas:** Flujo de checkout rápido, pasarelas de pago y actualización de stock en tiempo real.
6. **Envíos Programados (Suscripciones B2B):** Funcionalidad donde se programan despachos de café para días específicos del calendario elegidos por el cliente. El sistema debe generar automáticamente los pedidos y hojas de ruta cuando llega la fecha acordada.

## Reglas de Arquitectura y Código

### Backend (FastAPI + SQLAlchemy)
- **Estructura de directorios:** Utilizar un patrón de diseño por dominios/módulos (vertical slice). Cada módulo agrupa sus propias capas (`router.py`, `models.py`, `schemas.py`, `crud.py`, `services.py`), y la comunicación entre módulos se hace vía servicios, nunca importando routers ajenos.

  ```text
  backend/
  ├── app/
  │   ├── core/            # config, security/JWT, sesión de DB, dependencias comunes (sin lógica de negocio)
  │   ├── modules/
  │   │   ├── auth/        # router.py, models.py, schemas.py, crud.py, services.py
  │   │   ├── inventario/
  │   │   ├── produccion/
  │   │   ├── clientes/
  │   │   ├── pedidos/
  │   │   └── envios/
  │   ├── tasks/           # APScheduler: dispara los jobs, no decide reglas de negocio
  │   └── main.py
  ├── alembic/             # migraciones de base de datos
  ├── tests/               # espeja app/modules
  └── requirements.txt
  ```
- **Capas por módulo:** Cada módulo separa responsabilidades así:
  - `router.py`: solo HTTP (validación de entrada, códigos de estado, dependencias). Sin reglas de negocio ni acceso directo a la sesión.
  - `schemas.py`: schemas Pydantic de entrada y salida.
  - `models.py`: modelos SQLAlchemy (tablas) del módulo.
  - `crud.py`: acceso a datos puro (queries sin reglas de negocio).
  - `services.py`: reglas de negocio y frontera transaccional (commit/rollback). Es la única capa que otros módulos pueden importar.
- **Modelos en un archivo por módulo:** Todas las tablas de un módulo viven en su `models.py` (ej. `inventario/models.py` con `LoteCafeVerde`, `LoteCafeTostado`, `MovimientoStock`). No crear subcarpetas `models/` por módulo salvo que un módulo supere 3-4 entidades o su `models.py` exceda ~250 líneas. En ese caso, convertir ese módulo a `models/` con un `__init__.py` que re-exporte los símbolos, de modo que `from app.modules.<módulo>.models import X` siga funcionando para el resto del código.
- **Núcleo acotado (`core/`):** Solo configuración, seguridad/JWT, sesión de base de datos y dependencias compartidas. Ninguna regla de negocio. Si aparece un helper realmente compartido, va en `core/` con nombre explícito; no crear `common/` ni `utils/` genéricos.
- **Tareas programadas:** `tasks/` solo programa y dispara (parseo de fecha, invocación del caso de uso, logging). El caso de uso de negocio vive en el módulo propietario: la generación diaria de despachos pertenece a `modules/envios/services/` y desde ahí coordina `pedidos`, `inventario` y `clientes` dentro de una única transacción.
- **Automatización de Calendario:** Crear un modelo (tabla) que almacene los días de entrega programados por cliente. Implementar un *cron job* o *background task* que corra diariamente, identifique los envíos agendados para ese día, genere el pedido, descuente el stock y lo sume a la cuenta corriente de forma transaccional. La generación diaria debe ser **transaccional e idempotente por (cliente, fecha)**: si el job corre más de una vez (reinicio o doble ejecución), no debe duplicar pedidos ni descontar stock dos veces. La idempotencia se respalda en la base con una restricción `UNIQUE (cliente_id, fecha_entrega)` sobre la tabla de entregas programadas, además de la verificación en la aplicación.
- **Validación de datos:** Usar siempre Pydantic para los schemas de entrada y salida.
- **Base de Datos:** No usar SQL crudo. Todas las interacciones deben hacerse mediante SQLAlchemy ORM. Garantizar el uso de transacciones (ACID) para operaciones financieras o de stock.
- **Tipado Estricto:** Obligatorio el uso de Type Hints en todas las funciones de Python.
- **Documentación:** Aprovechar la autogeneración de Swagger/OpenAPI de FastAPI.

## Arranque del Proyecto

A implementar.

#### Migraciones de Base de Datos

A implementar.

#### Testing

- **Ubicación:** Los tests espejan la estructura de módulos (`tests/modules/<módulo>/`) y los casos críticos de idempotencia y transacción se escriben contra la capa `services.py`, no contra los routers.

A implementar.

### Frontend (React)
- **Componentización:** Crear componentes modulares y reutilizables.
- **Diseño UI/UX (Estética Operativa):** Diseñar interfaces sobrias, limpias y orientadas a la usabilidad industrial. Evitar la estética visual genérica de "componentes generados por IA" (sin brillos, sombras exageradas, degradados excesivos o animaciones innecesarias). Priorizar un diseño de dashboard administrativo tradicional, con colores sólidos y jerarquía clara para agilizar el trabajo operativo.
- **Gestión de Calendario B2B:** Desarrollar una interfaz donde se pueda seleccionar en un calendario (o selector de días) la programación de entregas recurrentes para cada cliente, y una vista para que el equipo de logística vea la hoja de ruta generada automáticamente cada día.
- **Manejo de Errores:** Implementar manejo global de errores y feedback visual claro.

#### HTTP y Ruteo

A implementar.

### Reglas Generales
- **Respuestas Enfocadas:** Proveer solo las partes relevantes o modificadas, explicando el porqué de las decisiones de arquitectura y diseño.
- **Idioma:** Los comentarios, variables y commits deben estar en español. El título de cada commit debe estar en inglés.
- **Seguridad:** Usar variables de entorno (`.env`) para credenciales y JWT secrets.

### Control de Commits
- **Commit solo con aprobación explícita:** No ejecutar `git commit` de forma automática. Antes de cada commit, presentar el resumen de los cambios (archivos incluidos y propósito) y esperar la confirmación explícita del usuario.
- **Aprobación puntual:** La autorización vale únicamente para ese commit. No se extiende a commits posteriores sin volver a preguntar.
- **Sin operaciones remotas:** El `push`, la apertura de pull requests y el `merge` son siempre decisión del usuario y nunca se ejecutan sin autorización explícita.
- **Alcance:** Esta regla aplica al agente principal y a cualquier subagente que se despache.

## Instrucción de Inicio
Cuando se te asigne una tarea, primero analiza a qué módulo pertenece. Si es del módulo de envíos programados, asegúrate de cruzar correctamente el día agendado con el stock de café tostado disponible y la cuenta corriente del cliente antes de proponer el código.