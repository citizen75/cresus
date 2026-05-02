import { useParams, useSearchParams, Link } from 'react-router-dom'
import TransactionsView from '@/components/portfolio/TransactionsView'

const MAIN_TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'strategy', label: 'Strategy' },
  { id: 'watchlist', label: 'AI Watchlist' },
  { id: 'backtest', label: 'Backtest' },
  { id: 'holdings', label: 'Holdings' },
  { id: 'activity', label: 'Activity' },
]

export default function TransactionsPage() {
  const { name = 'main' } = useParams()
  const [searchParams] = useSearchParams()
  const filterTicker = searchParams.get('ticker') || undefined

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

      {/* Main Tab Navigation */}
      <div className="border-b border-slate-800">
        <div className="flex gap-8 overflow-x-auto">
          {MAIN_TABS.map((tab) => {
            let href = `/portfolios/${encodeURIComponent(name)}`
            if (tab.id === 'holdings') href += '/holdings'

            return (
              <Link
                key={tab.id}
                to={href}
                className={`px-1 py-4 font-medium text-sm transition border-b-2 whitespace-nowrap ${
                  tab.id === 'holdings'
                    ? 'border-purple-600 text-white'
                    : 'border-transparent text-slate-400 hover:text-slate-300'
                }`}
              >
                {tab.label}
              </Link>
            )
          })}
        </div>
      </div>

      {/* Sub Navigation */}
      <div className="flex items-center gap-4 border-b border-slate-800 pb-4">
        <Link
          to={`/portfolios/${encodeURIComponent(name)}/holdings`}
          className="text-slate-400 hover:text-slate-300 text-sm font-medium"
        >
          ← Holdings
        </Link>
        <h2 className="text-xl font-bold text-white">
          Transactions
          {filterTicker && <span className="text-slate-400 font-normal ml-2">({filterTicker})</span>}
        </h2>
      </div>

      {/* Transactions Content */}
      <TransactionsView name={name} filterTicker={filterTicker} />
    </div>
  )
}
