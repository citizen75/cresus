import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { usePortfolioDetails, usePortfolioWatchlist, usePortfolioOrders } from '@/hooks/usePortfolio'
import { api } from '@/services/api'
import ResultsWidget from '@/components/ResultsWidget'
import PortfolioHoldingsWidget from '@/components/portfolio/PortfolioHoldingsWidget'
import PortfolioPerformanceWidget from '@/components/portfolio/PortfolioPerformanceWidget'
import OrdersWidget from '@/components/portfolio/OrdersWidget'
import TaskListWidget from '@/components/portfolio/TaskListWidget'
import TradingChartWidget from '@/components/TradingChartWidget'

const TABS = [
  { id: 'watchlist', label: 'Watchlist' },
  { id: 'positions', label: 'Positions' },
  { id: 'performance', label: 'Performance' },
]

export default function PortfolioDetail() {
  const { name = '' } = useParams()
  const { data: details, isLoading, refetch } = usePortfolioDetails(name)
  const { data: watchlistData, isLoading: isWatchlistLoading } = usePortfolioWatchlist(name)
  const { data: ordersData, isLoading: isOrdersLoading, refetch: refetchOrders } = usePortfolioOrders(name)

  const handleDeleteOrder = async (order: { fullId?: string; id: string }) => {
    await api.deletePortfolioOrder(name, order.fullId || order.id)
    await refetchOrders()
  }

  const [activeTab, setActiveTab] = useState<'watchlist' | 'positions' | 'performance'>('watchlist')
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortColumn, setSortColumn] = useState<string | null>('ticker')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [historicalData, setHistoricalData] = useState<{ [ticker: string]: any[] }>({})
  const [isRefreshing, setIsRefreshing] = useState(false)

  const watchlist = watchlistData?.watchlist || []
  const positions = details?.positions || []
  const strategyName = details?.strategy || name
  const hasAutoSelectedTab = useRef(false)

  // Default to the first watchlist ticker once data loads, falling back to the
  // first open position for portfolios with no strategy-generated watchlist
  // (manual / backtested portfolios typically have positions but no watchlist).
  useEffect(() => {
    if (selectedTicker) return
    if (watchlist.length > 0) {
      setSelectedTicker(watchlist[0].ticker)
    } else if (positions.length > 0) {
      setSelectedTicker(positions[0].ticker)
    }
  }, [watchlist, positions, selectedTicker])

  // If this portfolio has no watchlist data, the Watchlist tab is empty by
  // default - switch to Positions once so real data isn't hidden behind it.
  useEffect(() => {
    if (hasAutoSelectedTab.current || isWatchlistLoading || activeTab !== 'watchlist') return
    hasAutoSelectedTab.current = true
    if (watchlist.length === 0 && positions.length > 0) {
      setActiveTab('positions')
    }
  }, [isWatchlistLoading, watchlist, positions, activeTab])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await refetch()
    } finally {
      setIsRefreshing(false)
    }
  }

  if (isLoading) {
    return <div className="text-slate-400">Loading portfolio...</div>
  }

  if (!details) {
    return <div className="text-slate-400">Portfolio "{name}" not found</div>
  }

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-shrink-0">
        <div>
          <Link to="/portfolios" className="text-purple-400 hover:text-purple-300 text-sm">
            ← Back to portfolios
          </Link>
          <div className="flex items-center gap-3 mt-2">
            <h1 className="text-3xl font-bold text-white capitalize">{name} Portfolio</h1>
          </div>
          <p className="text-slate-400 text-sm mt-1">Strategy: {strategyName}</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium text-sm transition disabled:opacity-50"
          >
            {isRefreshing ? 'Refreshing...' : '↻ Refresh'}
          </button>
        </div>
      </div>

      {/* Top row (~70%) - 2-column 50/50 layout */}
      <div className="flex gap-6 flex-[7] min-h-0">
        {/* Left column */}
        <div className="w-1/2 flex flex-col bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
          <div className="border-b border-slate-800 flex-shrink-0">
            <div className="flex gap-6 px-4">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as 'watchlist' | 'positions' | 'performance')}
                  className={`px-1 py-4 font-medium text-sm transition border-b-2 whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'border-purple-600 text-white'
                      : 'border-transparent text-slate-400 hover:text-slate-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-hidden">
            {activeTab === 'watchlist' && (
              isWatchlistLoading ? (
                <div className="text-center py-12 text-slate-400">Loading watchlist...</div>
              ) : (
                <ResultsWidget
                  data={watchlist}
                  searchQuery={searchQuery}
                  onSearchChange={setSearchQuery}
                  sortColumn={sortColumn}
                  onSortChange={setSortColumn}
                  sortDirection={sortDirection}
                  onSortDirectionChange={setSortDirection}
                  historicalData={historicalData}
                  onSetHistoricalData={setHistoricalData}
                  onGetHistoricalData={api.getHistoricalData.bind(api)}
                  onSelectTicker={setSelectedTicker}
                />
              )
            )}

            {activeTab === 'positions' && (
              <div className="h-full p-4">
                <PortfolioHoldingsWidget
                  portfolioName={name}
                  onSelectTicker={setSelectedTicker}
                />
              </div>
            )}

            {activeTab === 'performance' && (
              <PortfolioPerformanceWidget portfolioName={name} />
            )}
          </div>
        </div>

        {/* Right column - Chart (always mounted so its controls sidebar is never hidden) */}
        <div className="w-1/2 flex flex-col bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
          <TradingChartWidget ticker={selectedTicker || ''} showControls title={selectedTicker || undefined} />
        </div>
      </div>

      {/* Bottom row (~30%) - Orders widget + portfolio tasks */}
      <div className="flex gap-6 flex-[3] min-h-0">
        <div className="w-1/2 min-h-0">
          <OrdersWidget
            orders={ordersData?.orders || []}
            isLoading={isOrdersLoading}
            currency={details?.currency || 'USD'}
            onDeleteOrder={handleDeleteOrder}
          />
        </div>
        <div className="w-1/2 min-h-0">
          <TaskListWidget portfolioName={name} />
        </div>
      </div>
    </div>
  )
}
