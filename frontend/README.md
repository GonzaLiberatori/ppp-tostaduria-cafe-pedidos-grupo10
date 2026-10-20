# Café de Finca - Sistema de Gestión para Tostaduría

Interfaz frontend completa para la gestión de una tostaduría de café, desarrollada con React + Vite + Tailwind CSS.

## 🚀 Características

- **Stack Moderno**: React 18, Vite 5, Tailwind CSS 3
- **Tema Café**: Paleta de colores personalizada inspirada en tonos de café
- **Modo Claro/Oscuro**: Toggle persistente en localStorage
- **Persistencia Local**: Datos guardados en localStorage (simula backend)
- **4 Módulos Principales**:
  - **Stock**: Café verde y tostado con trazabilidad por lote
  - **Clientes**: B2B/B2C, historial, deudas, kilos comprados
  - **Pedidos**: Kanban + tabla, estados (Pendiente/Listo/Entregado), items múltiples
  - **Contabilidad**: Gráficos (Recharts), resumen mensual, gastos por categoría, exportación CSV
- **Dashboard**: Resumen ejecutivo con KPIs y alertas
- **Componentes Accesibles**: ARIA labels, focus management, keyboard navigation
- **Diseño Responsivo**: Mobile-first, sidebar colapsable

## 📦 Instalación

```bash
# Instalar dependencias
npm install

# Desarrollo
npm run dev

# Build producción
npm run build

# Preview build
npm run preview

# Linting
npm run lint
```

## 🏗️ Estructura del Proyecto

```
src/
├── components/
│   ├── ui/           # Componentes base (Button, Input, Modal, Table, etc.)
│   ├── layout/       # Layout, Sidebar, Header
│   └── forms/        # Formularios por módulo
├── pages/            # Páginas principales (Dashboard, Stock, Clientes, Pedidos, Contabilidad)
├── context/          # ThemeContext, DataContext (estado global + localStorage)
├── hooks/            # useLocalStorage, useToast
├── data/             # mockData.js, constants.js
├── utils/            # formatters.js, calculations.js
├── styles/           # globals.css (Tailwind + variables CSS café)
├── App.jsx           # Routing
└── main.jsx          # Entry point
```

## 🎨 Paleta de Colores "Café"

```css
coffee-50  #faf6f3   (crema clara)
coffee-100 #f0eae3   (beige suave)
coffee-200 #e1d5c9   (arena)
coffee-300 #c9b8a3   (café con leche)
coffee-400 #a89070   (café medio)
coffee-500 #8B6F47   ★ BRAND PRINCIPAL
coffee-600 #735839   (café oscuro)
coffee-700 #5d462e   (espresso)
coffee-800 #4a3726   (grano tostado)
coffee-900 #3d2e1f   (casi negro)
coffee-950 #221810   (negro café)
```

## 📊 Modelos de Datos

### Stock
```js
{ id, tipo: 'verde'|'tostado', variedad, origen, kilos, precioKg, fechaIngreso, lote }
```

### Cliente
```js
{ id, nombre, tipo: 'B2B'|'B2C', kilosComprados, tieneDeuda, montoDeuda, telefono, email, direccion, creadoEn }
```

### Pedido
```js
{ id, fecha, estado: 'Pendiente'|'Listo'|'Entregado', clienteId, items: [{stockId, variedad, kilos, precioKg}], medioContacto, observaciones, total }
```

### Gasto
```js
{ id, fecha, categoria: 'Producción'|'Operativo'|'Marketing'|'Otro', descripcion, monto }
```

## 🔧 Integración Backend (Próximos Pasos)

La arquitectura está preparada para conectar con FastAPI:

1. **Reemplazar DataContext** por llamadas a API (React Query / SWR)
2. **Endpoints sugeridos**:
   - `GET/POST/PUT/DELETE /api/stock`
   - `GET/POST/PUT/DELETE /api/clientes`
   - `GET/POST/PUT/DELETE /api/pedidos`
   - `GET/POST/PUT/DELETE /api/gastos`
   - `GET /api/contabilidad/mensual`
3. **Autenticación**: JWT en headers, refresh tokens
4. **WebSockets**: Para actualizaciones en tiempo real de pedidos

## 📝 Licencia

Proyecto educativo - Grupo 10