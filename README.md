# Café de Finca — Sistema de gestión para tostaduría de café (MVP 1)

Café de Finca es un sistema de gestión integral para una tostaduría de café, desarrollado como MVP 1. Cubre el ciclo completo del negocio: inventario dual de café verde (materia prima) y tostado (producto terminado), producción con órdenes de tueste y cálculo automático de mermas, clientes con cuentas corrientes y límites de crédito, pedidos y ventas con cobranzas, y envíos programados B2B que generan pedidos y hojas de ruta automáticamente cada día. Combina un backend API (FastAPI) con un panel web (React) y roles diferenciados (RBAC) para administradores, operarios, cajeros y clientes.

## Descripción general

| Capa | Tecnología |
|------|------------|
| Frontend | React 18 + Vite 5, Tailwind CSS 3, React Router 6, Recharts |
| Backend | FastAPI + Pydantic, SQLAlchemy 2, Uvicorn |
| Base de datos | SQLite (archivo local, sin servidor) + Alembic (migraciones) |
| Automatización | APScheduler (envíos programados) |
| Testing | pytest (espeja la estructura de módulos del backend) |

### Módulos del backend

| Módulo | Responsabilidad |
|--------|-----------------|
| `auth` | Autenticación JWT y control de acceso por roles (RBAC) |
| `inventario` | Trazabilidad de café verde y tostado: lotes, blends, tipos de café |
| `produccion` | Órdenes de tueste: mermas y conversión verde → tostado |
| `clientes` | Alta de clientes, cuentas corrientes y límites de crédito |
| `pedidos` | Gestión de pedidos, estados e historial |
| `ventas` | Checkout, métodos de pago, cobranza y resumen contable |
| `gastos` | Gastos del panel de contabilidad |
| `envios` | Suscripciones B2B: entregas programadas y hoja de ruta diaria |

### Roles

| Rol | Permisos |
|-----|----------|
| **Administrador** | Acceso total al panel y a la configuración |
| **Operario** | Operación y consulta del panel interno; sin permisos para crear clientes ni registrar ventas |
| **Cajero** | Ventas, cobros y cobranza |
| **Cliente** | Portal propio: compras, suscripciones y cuenta corriente |

## Estructura del proyecto

```text
ppp-tostaduria-cafe-pedidos-grupo10/
├── backend/
│   ├── app/
│   │   ├── core/                  # config, security/JWT, sesión de BD, dependencias
│   │   ├── modules/               # arquitectura vertical slice (un módulo por dominio)
│   │   │   └── <módulo>/          # router · schemas · models · crud · services
│   │   ├── tasks/                 # APScheduler: dispara los jobs de envíos
│   │   └── main.py                # app FastAPI, CORS y registro de routers
│   ├── alembic/                   # migraciones (versions/)
│   ├── scripts/
│   │   └── seed_demo.py           # datos demo idempotentes (cuentas, clientes, pedidos)
│   ├── tests/                     # espeja app/modules/<módulo>/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example               # plantilla de variables de entorno
│   └── db.sqlite                  # SQLite con datos demo (commiteado)
├── frontend/
│   ├── src/
│   │   ├── api/                   # cliente HTTP de inventario
│   │   ├── components/            # forms/ · layout/ · ui/
│   │   ├── context/               # AuthContext · DataContext · ThemeContext
│   │   ├── pages/                 # Dashboard, Stock, Tueste, Pedidos, ... + cliente/
│   │   ├── services/api.js        # cliente HTTP principal del panel
│   │   ├── hooks/ · utils/ · data/ · styles/
│   │   └── main.jsx
│   ├── Dockerfile
│   ├── vite.config.js
│   └── package.json
├── docs/                          # specs de features y diagramas
├── postman/                       # colecciones de la API
├── openspec/                      # specs y cambios (workflow OpenSpec)
├── docker-compose.yml
├── AGENTS.md                      # convenciones de arquitectura y código
└── README.md
```

## Cómo levantar el proyecto

### Requisitos

- **Opción A (recomendada):** [Docker Desktop](https://www.docker.com/products/docker-desktop/) con Compose.
- **Opción B (manual):** Python 3.14 y Node 24.

### Opción A — Docker (con hot reload)

```bash
docker compose up --build
```

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| Swagger / API docs | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

- El hot reload está activo en ambos servicios: editás un archivo y se recarga solo.
- La base de datos SQLite vive en el host (`backend/db.sqlite`), no dentro del contenedor.
- Si cambiás `frontend/package-lock.json`, refrescá las dependencias del contenedor:

```bash
docker compose down -v && docker compose up --build
```

### Opción B — Manual

```bash
# Backend (Python 3.14)
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000

# Frontend (Node 24) — en otra terminal
cd frontend
npm install
npm run dev                     # http://localhost:3000
```

### Cuentas de prueba

Vienen cargadas en `backend/db.sqlite` y las crea `backend/scripts/seed_demo.py`:

| Rol | Email | Contraseña |
|-----|-------|------------|
| Administrador | `admin@cafedefinca.com` | `admin123` |
| Operario | `operario@cafedefinca.com` | `operario123` |
| Cajero | `cajero@cafedefinca.com` | `cajero123` |
| Cliente | `cliente@cafedefinca.com` | `cliente123` |

### Tests

```bash
docker compose exec backend python -m pytest -q
```

Los tests críticos (idempotencia de envíos, transacciones de stock y cobranza) se escriben contra la capa `services.py`, no contra los routers.

## Información importante

### Base de datos (SQLite)

- El archivo `backend/db.sqlite` está commiteado con datos demo; es la misma base que usan Docker y las corridas locales.
- Las rutas relativas de `DATABASE_URL` se resuelven contra `backend/`, sin importar desde dónde corras el proceso.
- El proyecto **rechaza activamente** cualquier motor distinto de SQLite: `app/core/config.py` valida que `DATABASE_URL` empiece con `sqlite:///`. Es una decisión de arquitectura del MVP, no una restricción temporal.

### Migraciones (Alembic)

> ⚠️ La base incluida ya tiene el esquema aplicado. **No corras `alembic upgrade head` sobre ella**: su `alembic_version` registra una revisión que fue renombrada (`009_detalle_pedido_tipo_lote` → `009_detalle_pedido_tipo_stock`) y Alembic fallará al no encontrarla. Inspeccioná con `alembic current` antes de migrar.

### Variables de entorno

- **Backend:** `backend/.env` (plantilla en `backend/.env.example`): `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `ACCESS_TOKEN_EXPIRE_MINUTES` y las opciones del scheduler (`SCHEDULER_ENABLED`, `SCHEDULER_HOUR`, `SCHEDULER_MINUTE`, `SCHEDULER_TIMEZONE`).
- **Frontend:** existen **dos variables distintas**:
  - `VITE_API_URL` — usada por `src/services/api.js` (default `http://localhost:8000/api/v1`).
  - `VITE_API_BASE_URL` — usada por `src/api/client.js` (default `http://localhost:8000/api/v1/inventario`).

  Cambiar solo una no reubica todos los requests.

### CORS

Por defecto el backend solo acepta requests de `http://localhost:3000` y `http://localhost:5173` (`CORS_ORIGINS` en `.env`).

### Envíos programados (APScheduler)

Deshabilitado por defecto (`SCHEDULER_ENABLED=false`). Al habilitarlo, corre todos los días a las 06:00 (`America/Argentina/Buenos_Aires`) y genera los pedidos y hojas de ruta del día de forma **transaccional e idempotente por (cliente, fecha)**: una doble ejecución no duplica pedidos ni descuenta stock dos veces.

### API y colecciones

- Documentación interactiva: `http://localhost:8000/docs` (Swagger).
- Colecciones Postman en `postman/` (clientes, pedidos, ventas y entorno de configuración).

### Convenciones

Antes de contribuir, leé `AGENTS.md`: arquitectura por módulos (vertical slice), capas `router` / `schemas` / `models` / `crud` / `services`, y el control de commits del proyecto.

### Postman
https://julianagustinvillaverde-2391323.postman.co/workspace/78b3fb2a-31e3-4c11-a6f0-9b9f3250f4f5
