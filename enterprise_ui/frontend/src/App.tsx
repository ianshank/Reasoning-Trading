import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAppStore } from '@/stores/appStore'
import Layout from '@/components/layout/Layout'

// Page imports
import DashboardPage from '@/app/dashboard/page'
import PortfolioPage from '@/app/portfolio/page'
import AnalysisPage from '@/app/analysis/page'
import MCTSPage from '@/app/mcts/page'
import OrdersPage from '@/app/orders/page'
import RegimePage from '@/app/regime/page'
import LambdaPage from '@/app/lambda/page'
import SettingsPage from '@/app/settings/page'

function App() {
  const theme = useAppStore((state) => state.theme)

  // Apply theme on mount and when it changes
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [theme])

  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="portfolio" element={<PortfolioPage />} />
        <Route path="analysis" element={<AnalysisPage />} />
        <Route path="mcts" element={<MCTSPage />} />
        <Route path="orders" element={<OrdersPage />} />
        <Route path="regime" element={<RegimePage />} />
        <Route path="lambda" element={<LambdaPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  )
}

export default App
