# Razonamiento de Diseño — Frontend (React)

**Proyecto:** Café de Finca — Sistema de Gestión para Tostaduría (MVP 1)  
**Módulo:** Frontend (SPA React)  
**Estado:** Implementado  
**Fecha:** 04 de noviembre de 2026  
**Audiencia:** Desarrolladores, arquitectos, QA y nuevos integrantes del equipo

---

## 1. Propósito de este documento

Este documento explica el **por qué** de cada decisión de diseño del frontend, no solo el qué. Su objetivo es que cualquier desarrollador que se incorpore al proyecto entienda la intención detrás de la arquitectura, la separación de capas, el manejo de estado, el estilo visual y los puntos de integración con el backend, sin tener que inferirlos leyendo el código.

Está separado intencionalmente de la documentación del backend. Cada módulo (frontend y backend) tiene su propio razonamiento de diseño.

---

## 2. Stack tecnológico y criterios de selección

| Tecnología | Versión | Rol | Por qué se eligió |
|---|---|---|---|
| React | 18.2 | Interfaz de usuario | Estándar del equipo, ecosistema maduro, fácil contratación y mantenimiento. |
| Vite | 5.x | Bundler y dev server | Arranque en caliente muy rápido, build de producción ligero, configuración mínima. |
| Tailwind CSS | 3.x | Estilos | Utilidades CSS que permiten una estética operativa sobria sin escribir CSS custom en cada componente. |
| react-router-dom | 6.22 | Ruteo | Navegación SPA declarativa, soporte a rutas anidadas y protección por rol. |
| recharts | 2.12 | Gráficos | Librería de gráficos declarativa basada en React, ideal para el dashboard de contabilidad. |
| date-fns | 3.3 | Fechas | Funciones puras y tree-shakeable; evita el peso de moment.js. |
| lucide-react | 0.330 | Iconos | Conjunto de iconos consistente, ligero y fácil de personalizar con Tailwind. |

### Decisiones de exclusión deliberada

- **No TypeScript:** El MVP prioriza velocidad de entrega. Se acepta el riesgo de errores tipográficos en tiempo de ejecución, mitigados con validación en el backend y pruebas manuales. Se deja como deuda técnica para una futura versión.
- **No Redux / Zustand:** El alcance del estado global (clientes, pedidos, gastos, inventario, tema, autenticación) se cubre con la Context API nativa de React. Añadir una librería de estado extra añadiría complejidad sin beneficio proporcional en esta etapa.
- **No React Query / SWR:** No se implementó caché de servidor ni revalidación automática. Los datos se cargan al montar y se refrescan explícitamente tras mutaciones. Se deja como deuda técnica.
- **No WebSockets:** Las actualizaciones en tiempo real de pedidos no son un requisito crítico del MVP. El frontend consulta el backend bajo demanda.

---

## 3. Arquitectura de capas y flujo de datos

El frontend sigue una arquitectura por capas con responsabilidad única. Cada capa conoce solo a la inferior.

```
┌─────────────────────────────────────┐
│  Pages (UI)                         │  ← Presentación y captura de intención
├─────────────────────────────────────┤
│  Context + Hooks                    │  ← Estado global y efectos secundarios
├─────────────────────────────────────┤
│  Services / API (endpoints)         │  ← Definición de endpoints y JWT
├─────────────────────────────────────┤
│  api/client.js (fetch genérico)     │  ← Wrapper de fetch sin conocimiento de dominio
├─────────────────────────────────────┤
│  api/mappers.js                     │  ← Traducción backend ↔ frontend
└─────────────────────────────────────┘
                            │
                            ▼
                    Backend FastAPI
```

### 3.1 Pages (`src/pages/`)

Solo contienen presentación y captura de la intención del usuario. **No hacen llamadas directas a `fetch`** ni contienen reglas de negocio. Todas las mutaciones y consultas se delegan al `DataContext` o a los servicios de API.

Páginas principales:
- `Dashboard.jsx` — Resumen ejecutivo con KPIs y alertas.
- `Stock.jsx` — Gestión de café verde y tostado con trazabilidad por lote.
- `Clientes.jsx` — Gestión de clientes B2B/B2C, historial, deudas.
- `Pedidos.jsx` — Tabla y Kanban de pedidos, estados, ítems múltiples.
- `Contabilidad.jsx` — Gráficos, resumen mensual, gastos, exportación CSV.
- `Login.jsx` / `Register.jsx` — Autenticación.
- `src/pages/cliente/` — Portal del cliente (Comprar, Mis Pedidos, Perfil, Suscripciones).

### 3.2 Context y Hooks (`src/context/`, `src/hooks/`)

- **`DataContext.jsx`**: Estado global de cafés, clientes, pedidos, gastos, inventario y contabilidad. Contiene las acciones de mutación (`addPedido`, `updatePedido`, `consumirStockFIFO`, etc.) y consultas derivadas (`getContabilidadMensual`, `getTotalesGenerales`).
- **`AuthContext.jsx`**: Estado de autenticación (usuario, token, roles) y utilidades `hasRole()`.
- **`ThemeContext.jsx`**: Alternancia modo claro/oscuro, persistente en `localStorage`.
- **`useToast.jsx`**: Notificaciones globales de éxito/error.
- **`useLocalStorage.js`**: Lectura/escritura segura en `localStorage` con manejo de errores.

### 3.3 Services / API (`src/services/api.js`)

Define todos los endpoints consumidos por el frontend, centraliza la URL base (`VITE_API_URL`), el token JWT en `localStorage` y la traducción de errores de FastAPI al formato que consumen los contextos y formularios.

Cada expuesto de `api` corresponde a un endpoint del backend:
- Pedidos del panel: `/pedidos/panel`
- Clientes: `/clientes/`
- Inventario (contrato plano del panel): `/inventario/stock`
- Gastos: `/gastos/`
- Ventas (contabilidad): `/ventas/`, `/ventas/resumen-mensual`, `/ventas/cobrar`, etc.

### 3.4 `api/client.js` — Wrapper de fetch genérico

Es un cliente HTTP de bajo nivel que **no conoce el dominio del negocio**. Solo hace `fetch`, maneja códigos de estado HTTP, parsea JSON y lanza `ApiError` con `status`, `detail` y `data`. Se encarga de:
- Detectar errores de red (sin conexión al backend) y mostrar un mensaje amigable.
- Estandarizar el `detail` de FastAPI (string, array de errores de Pydantic o objeto) en un mensaje legible.

### 3.5 `api/mappers.js` — Traducción de modelos

El backend modela el inventario en tablas separadas (`TipoDeCafe`, `Blend`, `Lote`), mientras que el frontend necesita un modelo unificado de "café" para simplificar las páginas de stock y pedidos. Los mappers hacen la traducción bidireccional:

- `tipoDeCafeToFrontend` / `blendToFrontend`: Backend → Frontend.
- `ensamblarCafes`: Une tipos de café, blends y lotes en una lista unificada.
- `cafeSimpleToBackend` / `cafeBlendToBackend`: Frontend → Backend (para crear/actualizar).
- `loteToBackendCreate` / `loteToBackendUpdate`: Conversión de lotes para envío al backend.

Esta separación evita que el acoplamiento al modelo de datos del backend se filtre en las páginas y componentes.

---

## 4. Modelo de datos unificado del frontend

El frontend unifica `TipoDeCafe` y `Blend` en un solo objeto `café` con un discriminador `tipoProducto`:

```js
{
  id: string,
  tipoProducto: 'simple' | 'blend',
  variedad: string,
  nombre: string,
  precioKg: number,
  lotes: []
}
```

**Por qué:** Las páginas de stock y pedidos no necesitan distinguir si un producto es un tipo de café simple o un blend para mostrarlo en una lista. El discriminador se usa solo al momento de enviar datos al backend (para decidir si se llena `tipo_de_cafe_id` o `blend_id`).

### Identificador de stock (`stockId`)

El frontend usa un identificador plano para referenciar lotes:

```
tc-{id}-TOSTADO   → TipoDeCafe
bl-{id}-TOSTADO   → Blend
```

Esto evita exponer claves foráneas del backend directamente al usuario y simplifica la selección de productos en el formulario de pedidos.

---

## 5. Consumo FIFO de stock en el cliente

La función `consumirLotesFIFO` en `DataContext.jsx` calcula de forma anticipada qué lotes se consumirían al crear un pedido, para mostrar disponibilidad real antes de enviar la petición al backend.

**Orden de consumo:**
1. Lotes con estado `abierto` primero, luego `cerrado`.
2. Dentro de cada grupo, por antigüedad (`fechaCreación` ascendente).

**Solo se descuentan lotes de café tostado** (producto terminado), nunca café verde (materia prima).

**Importante:** Esta es una **validación anticipada del frontend**, no la fuente de verdad. El descuento definitivo y el control de stock ocurre en el backend (servicio de pedidos con FIFO por fecha de vencimiento).

---

## 6. Estado global y persistencia (`localStorage`)

### Qué se persiste en `localStorage`
- `clientes`, `pedidos`, `gastos`: se guardan para que la aplicación funcione sin backend (modo demo/desarrollo).
- `auth_token`, `user`: sesión de autenticación.
- Tema (claro/oscuro): preferencia visual del usuario.

### Qué NO se persiste en `localStorage`
- `cafes` e `inventario`: se consumen siempre de la API del backend porque son catálogos maestros que pueden ser modificados por otros usuarios. Persistirlos localmente provocaría datos desactualizados.

### Patrón `withLoading`
Las mutaciones en `DataContext` usan un wrapper `withLoading` que establece un estado de carga consistente, ejecuta la operación y limpia el estado, evitando que el usuario realice acciones duplicadas mientras una petición está en curso.

---

## 7. Autenticación y autorización por rol

### Flujo de autenticación
1. El usuario se autentica en `/login` o `/register`.
2. El JWT se guarda en `localStorage` bajo la clave `auth_token`.
3. `AuthContext` expone `user`, `loading`, `hasRole(roles)` y utilidades de cierre de sesión.
4. Cada petición autenticada incluye el header `Authorization: Bearer <token>`.

### Protección de rutas (`App.jsx`)
- `PublicRoute`: rutas de acceso libre (`/login`, `/register`). Si ya hay sesión, redirige al inicio según rol.
- `ProtectedRoute`: requiere autenticación y, opcionalmente, roles específicos. Si no se cumple, redirige al inicio del rol del usuario.

### Layouts separados
- **`Layout`** (staff): Sidebar con Dashboard, Stock, Clientes, Pedidos, Contabilidad. Roles permitidos: `admin`, `empleado`, `vendedor`.
- **`LayoutCliente`** (portal del cliente): Vistas de Comprar, Mis Pedidos, Perfil, Suscripciones. Rol permitido: `cliente`.

> **Nota de alcance:** La restricción por rol es de interfaz (frontend). El backend valida permisos por su cuenta. Esta duplicación es intencional en el MVP: el frontend ofrece una buena experiencia de usuario, pero la seguridad real reside en el backend.

---

## 8. Diseño visual y estética operativa

### Paleta de colores "café"
Definida como variables CSS en `src/styles/globals.css` y usada mediante clases de Tailwind:

| Variable | Valor | Uso |
|---|---|---|
| `coffee-50` | `#faf6f3` | Fondos claros |
| `coffee-100` | `#f0eae3` | Fondos suaves |
| `coffee-500` | `#8B6F47` | Color de marca principal |
| `coffee-800` | `#4a3726` | Texto principal |
| `coffee-950` | `#221810` | Fondos oscuros |

### Modo claro/oscuro
Alternancia persistente en `localStorage` vía `ThemeContext`. Las variables CSS se ajustan automáticamente.

### Estética operativa
Conforme a las reglas de `AGENTS.md`:
- Interfaces sobrias, limpias y orientadas a la usabilidad industrial.
- Colores sólidos y jerarquía clara.
- **Sin** brillos, sombras exageradas, degradados excesivos ni animaciones innecesarias.
- Diseño de dashboard administrativo tradicional para agilizar el trabajo operativo.

### Componentes UI base (`src/components/ui/`)
Botón, Input, Modal, Tabla y otros componentes base reutilizados por todas las páginas. Esto garantiza consistencia visual y reduce duplicación de código.

### Diseño responsivo
Enfoque mobile-first con sidebar colapsable. Las páginas de escritorio usan layout con sidebar; en pantallas pequeñas se adapta a navegación simplificada.

---

## 9. Manejo de errores y feedback

### `ApiError`
Clase personalizada que captura `status`, `detail` y `data` originales de la respuesta HTTP. Permite distinguir errores de backend (4xx, 5xx) de errores de red (sin conexión).

### Traducción de errores de FastAPI
FastAPI devuelve errores en formato `{ detail: "..." }` o `{ detail: [{ msg, loc, type }] }`. El frontend normaliza ambos formatos a un string legible para mostrar al usuario.

### Error 401 (sesión expirada)
Al recibir `401`, el cliente:
1. Limpia `localStorage` (token, usuario).
2. Dispara el evento `window.dispatchEvent(new Event('auth:expirada'))`.
3. Redirige al login.

### Feedback visual
- `useToast` + `<Toaster />`: toasts globales de éxito y error.
- Mensajes de stock insuficiente y errores de validación mostrados directamente en los formularios.

---

## 10. Integración con el backend

### Endpoints consumidos (vía `services/api.js`)

| Recurso | Endpoint | Método |
|---|---|---|
| Autenticación | `/auth/login`, `/auth/me` | POST, GET |
| Pedidos del panel | `/pedidos/panel`, `/pedidos/panel/cliente/{id}` | GET, POST, PATCH, DELETE |
| Clientes | `/clientes/`, `/clientes/{id}` | GET, POST, PATCH, DELETE |
| Inventario (panel) | `/inventario/stock`, `/inventario/stock/{id}` | GET, POST, PATCH, DELETE |
| Bolsas de stock | `/inventario/stock/{id}/bolsas` | POST, PATCH, DELETE |
| Gastos | `/gastos/`, `/gastos/{id}` | GET, POST, PATCH, DELETE |
| Ventas | `/ventas/`, `/ventas/resumen-mensual`, `/ventas/cobrar`, `/ventas/anular` | GET, POST |

### Endpoints de inventario maestro (vía `api/inventario.js`)

| Recurso | Endpoint |
|---|---|
| Tipos de café | `/tipos-de-cafe` |
| Blends | `/blends` |
| Lotes | `/lotes` (con filtro XOR `tipo_de_cafe_id` o `blend_id`) |

### Queda por implementar (próximos pasos)
Según el `README.md` del frontend:
1. Reemplazar `DataContext` por llamadas a API con React Query / SWR.
2. Autenticación con JWT en headers y refresh tokens.
3. WebSockets para actualizaciones en tiempo real de pedidos.

---

## 11. Decisiones diferidas y deuda técnica

| Área | Estado actual | Queda pendiente |
|---|---|---|
| Tipado | JavaScript dinámico | Migrar a TypeScript |
| Caché de servidor | Carga manual al montar | React Query / SWR |
| Validación de formularios | Validación local en componentes | Librería (react-hook-form / formik) |
| Pruebas automatizadas | No implementadas | Tests unitarios e integración |
| Tiempo real | Consultas bajo demanda | WebSockets |
| RBAC en backend | Solo restricción de interfaz | Validación de roles en endpoints |

---

## 12. Archivos de referencia

- `frontend/src/App.jsx` — Ruteo y protección por rol.
- `frontend/src/context/DataContext.jsx` — Estado global y acciones de negocio del frontend.
- `frontend/src/context/AuthContext.jsx` — Autenticación y autorización.
- `frontend/src/context/ThemeContext.jsx` — Tema claro/oscuro.
- `frontend/src/services/api.js` — Endpoints y manejo de JWT.
- `frontend/src/api/client.js` — Wrapper de fetch genérico.
- `frontend/src/api/mappers.js` — Traducción de modelos backend ↔ frontend.
- `frontend/src/api/inventario.js` — Endpoints de inventario maestro.
- `frontend/src/hooks/useToast.jsx` — Notificaciones globales.
- `frontend/src/styles/globals.css` — Paleta de colores y variables CSS.
- `frontend/README.md` — Stack, instalación y estructura general.
- `AGENTS.md` — Reglas de arquitectura y convenciones del proyecto.

---

*Fin del documento.*