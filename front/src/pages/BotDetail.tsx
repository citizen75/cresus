import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useBot, useBotWatchlist, useBotOrders } from '@/hooks/useBots'
import { api } from '@/services/api'
import ResultsWidget from '@/components/ResultsWidget'
import PortfolioHoldingsWidget from '@/components/portfolio/PortfolioHoldingsWidget'
import PortfolioPerformanceWidget from '@/components/portfolio/PortfolioPerformanceWidget'
import OrdersWidget from '@/components/portfolio/OrdersWidget'
import TradingChartWidget from '@/components/TradingChartWidget'

const TABS = [
  { id: 'watchlist', label: 'Watchlist' },
  { id: 'positions', label: 'Positions' },
  { id: 'performance', label: 'Performance' },
]

export default function BotDetail() {
  const { name = '' } = useParams()
  const { data: bot, isLoading, refetch } = useBot(name)
  const { data: watchlistData, isLoading: isWatchlistLoading } = useBotWatchlist(name)
  const { data: ordersData, isLoading: isOrdersLoading, refetch: refetchOrders } = useBotOrders(name)

  const handleDeleteOrder = async (order: { fullId?: string; id: string }) => {
    await api.deleteBotOrder(name, order.fullId || order.id)
    await refetchOrders()
  }

  const [activeTab, setActiveTab] = useState<'watchlist' | 'positions' | 'performance'>('watchlist')
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortColumn, setSortColumn] = useState<string | null>('ticker')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [historicalData, setHistoricalData] = useState<{ [ticker: string]: any[] }>({})
  const [isToggling, setIsToggling] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [runMessage, setRunMessage] = useState<string | null>(null)

  const watchlist = watchlistData?.watchlist || []
  const config = bot?.config || {}
  const strategyName = config.strategy || name
  const isActive = config.state === 'active'

  // Default to the first watchlist ticker once data loads
  useEffect(() => {
    if (!selectedTicker && watchlist.length > 0) {
      setSelectedTicker(watchlist[0].ticker)
    }
  }, [watchlist, selectedTicker])

  const handleToggleState = async () => {
    setIsToggling(true)
    try {
      if (isActive) {
        await api.deactivateBot(name)
      } else {
        await api.activateBot(name)
      }
      refetch()
    } catch (err) {
      console.error('Failed to toggle bot state:', err)
    } finally {
      setIsToggling(false)
    }
  }

  const handleRun = async () => {
    setIsRunning(true)
    setRunMessage(null)
    try {
      const result = await api.runBot(name, { step: 'pre_market' })
      setRunMessage(`Run completed: ${result.output?.agents_executed?.length ?? 0} agents executed`)
      refetch()
    } catch (err: any) {
      setRunMessage(err.response?.data?.detail || 'Run failed')
    } finally {
      setIsRunning(false)
    }
  }

  if (isLoading) {
    return <div className="text-slate-400">Loading bot...</div>
  }

  if (!bot) {
    return <div className="text-slate-400">Bot "{name}" not found</div>
  }

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-shrink-0">
        <div>
          <Link to="/bots" className="text-purple-400 hover:text-purple-300 text-sm">
            ← Back to bots
          </Link>
          <div className="flex items-center gap-3 mt-2">
            <h1 className="text-3xl font-bold text-white">{name}</h1>
            <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
              isActive ? 'bg-green-900/30 text-green-300' : 'bg-yellow-900/30 text-yellow-300'
            }`}>
              {isActive ? '● Active' : '○ Inactive'}
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">Strategy: {strategyName}</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleToggleState}
            disabled={isToggling}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition disabled:opacity-50 ${
              isActive
                ? 'bg-yellow-900/20 text-yellow-400 hover:bg-yellow-900/40'
                : 'bg-green-900/20 text-green-400 hover:bg-green-900/40'
            }`}
          >
            {isActive ? 'Pause' : 'Activate'}
          </button>
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium text-sm transition disabled:opacity-50"
          >
            {isRunning ? 'Running...' : '▶ Run pre-market'}
          </button>
        </div>
      </div>

      {runMessage && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-sm text-slate-300 flex-shrink-0">
          {runMessage}
        </div>
      )}

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

      {/* Bottom row (~30%) - Orders widget */}
      <div className="flex-[3] min-h-0">
        <OrdersWidget orders={ordersData?.orders || []} isLoading={isOrdersLoading} onDeleteOrder={handleDeleteOrder} />
      </div>
    </div>
  )
}
