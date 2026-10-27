import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { DataProvider } from './context/DataContext'
import { ToastProvider, Toaster } from './hooks/useToast.jsx'
import Layout from './components/layout/Layout'
import LayoutCliente from './components/layout/LayoutCliente'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Stock from './pages/Stock'
import Clientes from './pages/Clientes'
import Pedidos from './pages/Pedidos'
import Contabilidad from './pages/Contabilidad'
import InicioCliente from './pages/cliente/InicioCliente'
import ComprarCliente from './pages/cliente/Comprar'
import MisPedidosCliente from './pages/cliente/MisPedidos'
import PerfilCliente from './pages/cliente/PerfilCliente'
import SuscripcionesCliente from './pages/cliente/Suscripciones'
import './styles/globals.css'

function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading, hasRole } = useAuth()
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-primary)]">
        <div className="w-8 h-8 border-4 border-coffee-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }
  
  if (!user) {
    return <Navigate to="/login" replace />
  }
  
  if (allowedRoles && !hasRole(allowedRoles)) {
    return <Navigate to="/" replace />
  }
  
  return children
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth()
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-primary)]">
        <div className="w-8 h-8 border-4 border-coffee-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }
  
  if (user) {
    return <Navigate to="/" replace />
  }
  
  return children
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={
        <PublicRoute>
          <Login />
        </PublicRoute>
      } />
      
      <Route element={<Layout />}>
        <Route path="/" element={
          <ProtectedRoute allowedRoles={['admin', 'empleado', 'vendedor']}>
            <Dashboard />
          </ProtectedRoute>
        } />
        <Route path="/stock" element={
          <ProtectedRoute allowedRoles={['admin', 'empleado']}>
            <Stock />
          </ProtectedRoute>
        } />
        <Route path="/clientes" element={
          <ProtectedRoute allowedRoles={['admin', 'empleado', 'vendedor']}>
            <Clientes />
          </ProtectedRoute>
        } />
        <Route path="/pedidos" element={
          <ProtectedRoute allowedRoles={['admin', 'empleado', 'vendedor']}>
            <Pedidos />
          </ProtectedRoute>
        } />
        <Route path="/contabilidad" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <Contabilidad />
          </ProtectedRoute>
        } />
      </Route>
      
      <Route element={<LayoutCliente />}>
        <Route path="/cliente" element={
          <ProtectedRoute allowedRoles={['cliente']}>
            <InicioCliente />
          </ProtectedRoute>
        } />
        <Route path="/cliente/comprar" element={
          <ProtectedRoute allowedRoles={['cliente']}>
            <ComprarCliente />
          </ProtectedRoute>
        } />
        <Route path="/cliente/mis-pedidos" element={
          <ProtectedRoute allowedRoles={['cliente']}>
            <MisPedidosCliente />
          </ProtectedRoute>
        } />
        <Route path="/cliente/perfil" element={
          <ProtectedRoute allowedRoles={['cliente']}>
            <PerfilCliente />
          </ProtectedRoute>
        } />
        <Route path="/cliente/suscripciones" element={
          <ProtectedRoute allowedRoles={['cliente']}>
            <SuscripcionesCliente />
          </ProtectedRoute>
        } />
      </Route>
      
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <DataProvider>
          <ToastProvider>
            <AppRoutes />
            <Toaster />
          </ToastProvider>
        </DataProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App