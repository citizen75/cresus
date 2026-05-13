import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/hooks/usePortfolio'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import Portfolios from '@/pages/Portfolios'
import PortfolioDetail from '@/pages/PortfolioDetail'
import HoldingsPage from '@/pages/HoldingsPage'
import TransactionsPage from '@/pages/TransactionsPage'
import BacktestRuns from '@/pages/BacktestRuns'
import BacktestBuilder from '@/pages/BacktestBuilder'
import BacktestRunning from '@/pages/BacktestRunning'
import BacktestDetail from '@/pages/BacktestDetail'
import BacktestComparator from '@/pages/BacktestComparator'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout><Dashboard /></Layout>} />
          <Route path="/portfolios" element={<Layout><Portfolios /></Layout>} />
          <Route path="/portfolios/:name" element={<Layout><PortfolioDetail /></Layout>} />
          <Route path="/portfolios/:name/strategy" element={<Layout><PortfolioDetail /></Layout>} />
          <Route path="/portfolios/:name/watchlist" element={<Layout><PortfolioDetail /></Layout>} />
          <Route path="/portfolios/:name/backtest" element={<Layout><PortfolioDetail /></Layout>} />
          <Route path="/portfolios/:name/orders" element={<Layout><PortfolioDetail /></Layout>} />
          <Route path="/portfolios/:name/holdings" element={<Layout><HoldingsPage /></Layout>} />
          <Route path="/portfolios/:name/holdings/transactions" element={<Layout><TransactionsPage /></Layout>} />
          <Route path="/portfolios/:name/transactions" element={<Layout><TransactionsPage /></Layout>} />
          <Route path="/backtests" element={<Layout><BacktestRuns /></Layout>} />
          <Route path="/backtests/new" element={<Layout><BacktestBuilder /></Layout>} />
          <Route path="/backtests/running" element={<BacktestRunning />} />
          <Route path="/backtests/compare" element={<Layout><BacktestComparator /></Layout>} />
          <Route path="/backtests/:strategy/:runId" element={<Layout><BacktestDetail /></Layout>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
