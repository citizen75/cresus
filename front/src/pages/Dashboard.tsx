import { usePortfolios } from '@/hooks/usePortfolio'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const { data, isLoading } = usePortfolios()

  if (isLoading) {
    return <div className="text-slate-400">Loading...</div>
  }

  const portfolios = data?.portfolios || []

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold text-white mb-2">Home</h1>
        <p className="text-slate-400">Welcome to your portfolio dashboard</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-6">
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="text-slate-400 text-sm mb-2">Total portfolios</div>
          <div className="text-3xl font-bold text-white">{portfolios.length}</div>
        </div>
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="text-slate-400 text-sm mb-2">Total positions</div>
          <div className="text-3xl font-bold text-white">
            {portfolios.reduce((sum, p) => sum + p.num_positions, 0)}
          </div>
        </div>
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="text-slate-400 text-sm mb-2">Total trades</div>
          <div className="text-3xl font-bold text-white">
            {portfolios.reduce((sum, p) => sum + p.num_trades, 0)}
          </div>
        </div>
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="text-slate-400 text-sm mb-2">Avg return</div>
          <div className="text-3xl font-bold text-green-400">+12.5%</div>
        </div>
      </div>

      {/* Portfolio Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">Your Portfolios</h2>
          <Link to="/portfolios" className="text-purple-400 hover:text-purple-300 text-sm font-medium">
            View all →
          </Link>
        </div>

        {portfolios.length === 0 ? (
          <div className="bg-slate-900 rounded-lg p-12 border border-slate-800 text-center">
            <p className="text-slate-400 mb-4">No portfolios yet</p>
            <Link
              to="/portfolios"
              className="inline-flex px-6 py-3 bg-gradient-to-r from-purple-600 to-violet-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-violet-700 transition"
            >
              Create Portfolio
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {portfolios.map((portfolio) => (
              <Link
                key={portfolio.name}
                to={`/portfolios/${portfolio.name}`}
                className="group bg-gradient-to-br from-slate-900 to-slate-900/50 rounded-lg p-6 border border-slate-800 hover:border-purple-600 transition cursor-pointer"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-violet-600 rounded-lg flex items-center justify-center">
                    <span className="text-xl">💼</span>
                  </div>
                  <span className="inline-flex px-2 py-1 rounded bg-purple-900/30 text-purple-300 text-xs font-medium capitalize">
                    {portfolio.type}
                  </span>
                </div>

                <h3 className="text-white font-bold text-lg mb-1 group-hover:text-purple-400 transition">
                  {portfolio.name}
                </h3>
                <p className="text-slate-400 text-sm mb-4">{portfolio.description}</p>

                <div className="space-y-3 pt-4 border-t border-slate-700">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400 text-sm">Currency</span>
                    <span className="text-white font-medium">{portfolio.currency}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400 text-sm">Positions</span>
                    <span className="text-white font-medium">{portfolio.num_positions}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400 text-sm">Trades</span>
                    <span className="text-white font-medium">{portfolio.num_trades}</span>
                  </div>
                  <div className="flex justify-between items-center pt-2 border-t border-slate-700">
                    <span className="text-slate-400 text-sm">Total gain</span>
                    <span className="text-green-400 font-medium">+€0</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
