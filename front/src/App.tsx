import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/hooks/usePortfolio'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import Portfolios from '@/pages/Portfolios'
import PortfolioDetail from '@/pages/PortfolioDetail'
import HoldingsPage from '@/pages/HoldingsPage'
import TransactionsPage from '@/pages/TransactionsPage'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout><Dashboard /></Layout>} />
          <Route path="/portfolios" element={<Layout><Portfolios /></Layout>} />
          <Route path="/portfolios/:name" element={<Layout><PortfolioDetail /></Layout>} />
          <Route path="/portfolios/:name/holdings" element={<Layout><HoldingsPage /></Layout>} />
          <Route path="/portfolios/:name/holdings/transactions" element={<Layout><TransactionsPage /></Layout>} />
          <Route path="/portfolios/:name/transactions" element={<Layout><TransactionsPage /></Layout>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
