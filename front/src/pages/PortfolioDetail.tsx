import { useParams, Link, useLocation, useNavigate } from 'react-router-dom'
import PortfolioOverview from '@/components/portfolio/PortfolioOverview'
import StrategyBuilder from '@/components/portfolio/StrategyBuilder'
import AIWatchlist from '@/components/portfolio/AIWatchlist'
import OrdersView from '@/components/portfolio/OrdersView'
import PortfolioBacktest from '@/components/portfolio/PortfolioBacktest'
import PortfolioSettings from '@/components/portfolio/PortfolioSettings'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'strategy', label: 'Strategy' },
  { id: 'watchlist', label: 'AI Watchlist' },
  { id: 'orders', label: 'Orders' },
  { id: 'backtest', label: 'Backtest' },
  { id: 'holdings', label: 'Holdings' },
  { id: 'activity', label: 'Activity' },
  { id: 'settings', label: 'Settings' },
]

export default function PortfolioDetail() {
  const { name = 'main' } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  
  // Detect active tab from URL path
  const getActiveTab = () => {
    // Check URL for routed tabs
    if (location.pathname.includes('/strategy')) return 'strategy'
    if (location.pathname.includes('/watchlist')) return 'watchlist'
    if (location.pathname.includes('/backtest')) return 'backtest'
    if (location.pathname.includes('/orders')) return 'orders'
    if (location.pathname.includes('/holdings')) return 'holdings'
    if (location.pathname.includes('/transactions')) return 'activity'
    if (location.pathname.includes('/settings')) return 'settings'

    // Default to overview if no tab path segment found
    return 'overview'
  }
  
  const activeTab = getActiveTab()
  
  const handleTabChange = (tabId: string) => {
    // Route all tabs through URL
    if (tabId === 'overview') {
      navigate(`/portfolios/${encodeURIComponent(name)}`)
    } else if (tabId === 'strategy') {
      navigate(`/portfolios/${encodeURIComponent(name)}/strategy`)
    } else if (tabId === 'watchlist') {
      navigate(`/portfolios/${encodeURIComponent(name)}/watchlist`)
    } else if (tabId === 'backtest') {
      navigate(`/portfolios/${encodeURIComponent(name)}/backtest`)
    } else if (tabId === 'orders') {
      navigate(`/portfolios/${encodeURIComponent(name)}/orders`)
    } else if (tabId === 'holdings') {
      navigate(`/portfolios/${encodeURIComponent(name)}/holdings`)
    } else if (tabId === 'activity') {
      navigate(`/portfolios/${encodeURIComponent(name)}/transactions`)
    } else if (tabId === 'settings') {
      navigate(`/portfolios/${encodeURIComponent(name)}/settings`)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <Link to="/portfolios" className="text-purple-400 hover:text-purple-300 text-sm">
            ← Back to portfolios
          </Link>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition text-sm font-medium">
            Actions
          </button>
          <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition text-sm font-medium flex items-center gap-2">
            <span>✨</span> Ask Cresus
          </button>
        </div>
      </div>

      {/* Portfolio Header */}
      <div className="flex items-start justify-between border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-violet-600 rounded-lg flex items-center justify-center">
              <span className="text-lg">🚀</span>
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white capitalize">{name} Portfolio</h1>
              <p className="text-slate-400 text-sm">High growth companies and AI innovators.</p>
            </div>
          </div>
          <div className="mt-2 flex items-center gap-4">
            <span className="inline-block px-2 py-1 bg-purple-900/30 text-purple-300 text-xs font-medium rounded">Primary</span>
            <span className="text-slate-500 text-xs flex items-center gap-1">
              <span className="w-2 h-2 bg-green-400 rounded-full"></span>
              Updated just now
            </span>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-slate-800">
        <div className="flex gap-8 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
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

      {/* Tab Content */}
      <div>
        {activeTab === 'overview' && <PortfolioOverview name={name} />}
        {activeTab === 'strategy' && <StrategyBuilder name={name} />}
        {activeTab === 'watchlist' && <AIWatchlist name={name} />}
        {activeTab === 'orders' && <OrdersView name={name} />}
        {activeTab === 'backtest' && <PortfolioBacktest name={name} />}
        {activeTab === 'settings' && <PortfolioSettings name={name} />}
        {activeTab === 'activity' && <div className="text-slate-400 py-12 text-center">Activity tab - Coming soon</div>}
      </div>
    </div>
  )
}
