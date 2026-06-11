import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from '@/hooks/usePortfolio'
import { getApiBaseUrl } from '@/services/api'
import { ConversationProvider } from '@/contexts/ConversationContext'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import Portfolios from '@/pages/Portfolios'
import PortfolioDetail from '@/pages/PortfolioDetail'
import HoldingsPage from '@/pages/HoldingsPage'
import TransactionsPage from '@/pages/TransactionsPage'
import StrategiesList from '@/pages/StrategiesList'
import StrategyDetail from '@/pages/StrategyDetail'
import StrategyBacktests from '@/pages/StrategyBacktests'
import BacktestRuns from '@/pages/BacktestRuns'
import BacktestBuilder from '@/pages/BacktestBuilder'
import BacktestDetail from '@/pages/BacktestDetail'
import BacktestComparator from '@/pages/BacktestComparator'
import Chart from '@/pages/Chart'
import Alerts from '@/pages/Alerts'
import Insights from '@/pages/Insights'
import Scheduler from '@/pages/Scheduler'
import Screener from '@/pages/Screener'
import ScreenerDetail from '@/pages/ScreenerDetail'
import WatchlistPage from '@/pages/WatchlistPage'
import Tasks from '@/pages/Tasks'

export default function App() {
  useEffect(() => {
    console.log(`%c[Cresus Frontend] API Server: ${getApiBaseUrl()}`, 'color: #4F46E5; font-weight: bold;')
  }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <ConversationProvider>
        <BrowserRouter>
          <Routes>
          <Route path="/" element={<Layout><Dashboard /></Layout>} />
          <Route path="/portfolios" element={<Layout><Portfolios /></Layout>} />
          <Route path="/portfolios/:name" element={<Layout><PortfolioDetail /></Layout>} />
          <Route path="/portfolios/:name/strategy" element={<Layout><PortfolioDetail /></Layout>} />
          <Route path="/portfolios/:name/watchlist" element={<Layout><PortfolioDetail /></Layout>} />
          <Route path="/portfolios/:name/backtest" element={<Layout><PortfolioDetail /></Layout>} />
          <Route path="/portfolios/:name/orders" element={<Layout><PortfolioDetail /></Layout>} />
          <Route path="/portfolios/:name/settings" element={<Layout><PortfolioDetail /></Layout>} />
          <Route path="/portfolios/:name/holdings" element={<Layout><HoldingsPage /></Layout>} />
          <Route path="/portfolios/:name/holdings/transactions" element={<Layout><TransactionsPage /></Layout>} />
          <Route path="/portfolios/:name/transactions" element={<Layout><TransactionsPage /></Layout>} />
          <Route path="/strategies" element={<Layout><StrategiesList /></Layout>} />
          <Route path="/strategies/:name" element={<Layout><StrategyDetail /></Layout>} />
          <Route path="/strategies/:name/backtests" element={<Layout><StrategyBacktests /></Layout>} />
          <Route path="/backtests" element={<Layout><BacktestRuns /></Layout>} />
          <Route path="/backtests/new" element={<Layout><BacktestBuilder /></Layout>} />
          <Route path="/backtests/compare" element={<Layout><BacktestComparator /></Layout>} />
          <Route path="/backtests/:strategy/:runId/:tab?" element={<Layout><BacktestDetail /></Layout>} />
          <Route path="/chart" element={<Layout><Chart /></Layout>} />
          <Route path="/chart/:ticker" element={<Layout><Chart /></Layout>} />
          <Route path="/alerts" element={<Layout><Alerts /></Layout>} />
          <Route path="/alerts/:name/edit" element={<Layout><Alerts /></Layout>} />
          <Route path="/alerts/:name" element={<Layout><Alerts /></Layout>} />
          <Route path="/alerts/:name/:resultId" element={<Layout><Alerts /></Layout>} />
          <Route path="/alerts/:name/:resultId/:view" element={<Layout><Alerts /></Layout>} />
          <Route path="/insights" element={<Layout><Insights /></Layout>} />
          <Route path="/scheduler" element={<Layout><Scheduler /></Layout>} />
          <Route path="/screener" element={<Layout><Screener /></Layout>} />
          <Route path="/screener/:name/:view?" element={<Layout><ScreenerDetail /></Layout>} />
          <Route path="/watchlist" element={<Layout><WatchlistPage /></Layout>} />
          <Route path="/tasks" element={<Layout><Tasks /></Layout>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </BrowserRouter>
      </ConversationProvider>
    </QueryClientProvider>
  )
}
