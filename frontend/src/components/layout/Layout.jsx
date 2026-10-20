import { Outlet } from 'react-router-dom'
import TopTabs from './TopTabs'

export default function Layout() {
  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <TopTabs />
      
      <main className="pt-0 min-h-screen" role="main" tabIndex={-1}>
        <div className="container-app py-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}