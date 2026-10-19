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
- **Estructura de directorios:** Utilizar un patrón de diseño por dominios/módulos (vertical slice). Cada módulo agrupa sus propias capas (`router.py`, `models.py`, `schemas.py`, `crud.py`), y la comunicación entre módulos se hace vía servicios, nunca importando routers ajenos.

  ```text
  app/
  ├── core/            # configuración, seguridad JWT, dependencias comunes
  ├── modules/
  │   ├── auth/
  │   ├── inventario/
  │   ├── produccion/
  │   ├── clientes/
  │   ├── pedidos/
  │   └── envios/
  ├── tasks/           # APScheduler
  └── main.py
  ```
- **Automatización de Calendario:** Crear un modelo (tabla) que almacene los días de entrega programados por cliente. Implementar un *cron job* o *background task* que corra diariamente, identifique los envíos agendados para ese día, genere el pedido, descuente el stock y lo sume a la cuenta corriente de forma transaccional. La generación diaria debe ser **transaccional e idempotente por (cliente, fecha)**: si el job corre más de una vez (reinicio o doble ejecución), no debe duplicar pedidos ni descontar stock dos veces.
- **Validación de datos:** Usar siempre Pydantic para los schemas de entrada y salida.
- **Base de Datos:** No usar SQL crudo. Todas las interacciones deben hacerse mediante SQLAlchemy ORM. Garantizar el uso de transacciones (ACID) para operaciones financieras o de stock.
- **Tipado Estricto:** Obligatorio el uso de Type Hints en todas las funciones de Python.
- **Documentación:** Aprovechar la autogeneración de Swagger/OpenAPI de FastAPI.

## Arranque del Proyecto

A implementar.

#### Migraciones de Base de Datos

A implementar.

#### Testing

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

## Instrucción de Inicio
Cuando se te asigne una tarea, primero analiza a qué módulo pertenece. Si es del módulo de envíos programados, asegúrate de cruzar correctamente el día agendado con el stock de café tostado disponible y la cuenta corriente del cliente antes de proponer el código.