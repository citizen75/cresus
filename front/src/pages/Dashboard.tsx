import { usePortfolios } from '@/hooks/usePortfolio'
import { Link } from 'react-router-dom'
import { useMemo } from 'react'

export default function Dashboard() {
  const { data, isLoading } = usePortfolios()
  const portfolios = data?.portfolios || []

  // Calculate total net worth and daily change across all portfolios
  const totalNetWorth = useMemo(() =>
    portfolios.reduce((sum: number, p: any) => sum + (p.total_portfolio_value || 0), 0)
  , [portfolios])

  const totalInvested = useMemo(() =>
    portfolios.reduce((sum: number, p: any) => sum + (p.initial_capital || 0), 0)
  , [portfolios])

  const totalGain = totalNetWorth - totalInvested
  const totalGainPercent = totalInvested > 0 ? (totalGain / totalInvested * 100) : 0

  // Mock daily performance data - in production would come from API
  const dailyPerformance = useMemo(() => {
    const dayChange = totalNetWorth * 0.02
    return {
      value: dayChange,
      percent: (dayChange / totalNetWorth) * 100,
      direction: Math.random() > 0.5 ? 'up' : 'down'
    }
  }, [totalNetWorth])

  // Aggregate all holdings from all portfolios to find top gainers/losers
  const allHoldings = useMemo(() => {
    const holdings: any[] = []
    portfolios.forEach((portfolio: any) => {
      if (portfolio.holdings && Array.isArray(portfolio.holdings)) {
        portfolio.holdings.forEach((holding: any) => {
          holdings.push({
            ticker: holding.ticker,
            portfolio: portfolio.name,
            currentPrice: holding.current_price || 0,
            quantity: holding.quantity || 0,
            avgCost: holding.avg_cost || 0,
            unrealizedGain: holding.unrealized_gain || 0,
            unrealizedGainPercent: holding.unrealized_gain_pct || 0,
            totalValue: (holding.current_price || 0) * (holding.quantity || 0)
          })
        })
      }
    })
    return holdings
  }, [portfolios])

  // Group holdings by ticker and calculate aggregate metrics
  const aggregatedHoldings = useMemo(() => {
    const map = new Map<string, any>()
    allHoldings.forEach((holding) => {
      const key = holding.ticker
      if (!map.has(key)) {
        map.set(key, {
          ticker: holding.ticker,
          totalValue: 0,
          totalGain: 0,
          quantity: 0,
          portfolios: []
        })
      }
      const existing = map.get(key)
      existing.totalValue += holding.totalValue
      existing.totalGain += holding.unrealizedGain
      existing.quantity += holding.quantity
      if (!existing.portfolios.includes(holding.portfolio)) {
        existing.portfolios.push(holding.portfolio)
      }
    })

    return Array.from(map.values())
      .map((h) => ({
        ...h,
        gainPercent: h.totalValue > 0 ? (h.totalGain / h.totalValue) * 100 : 0
      }))
      .sort((a, b) => b.gainPercent - a.gainPercent)
  }, [allHoldings])

  const topGainers = aggregatedHoldings.slice(0, 5)
  const topLosers = aggregatedHoldings.slice(-5).reverse()

  if (isLoading) {
    return <div className="text-slate-400">Loading...</div>
  }

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
          <div className="text-slate-400 text-sm mb-2">Total net worth</div>
          <div className="text-3xl font-bold text-white">${totalNetWorth.toFixed(0)}</div>
          <div className={`text-sm mt-2 ${totalGain >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {totalGain >= 0 ? '+' : ''}{totalGain.toFixed(0)} ({totalGainPercent.toFixed(2)}%)
          </div>
        </div>
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="text-slate-400 text-sm mb-2">Today's change</div>
          <div className={`text-3xl font-bold ${dailyPerformance.direction === 'up' ? 'text-green-400' : 'text-red-400'}`}>
            {dailyPerformance.direction === 'up' ? '+' : '-'}${Math.abs(dailyPerformance.value).toFixed(0)}
          </div>
          <div className={`text-sm mt-2 ${dailyPerformance.direction === 'up' ? 'text-green-400' : 'text-red-400'}`}>
            {dailyPerformance.direction === 'up' ? '+' : ''}{dailyPerformance.percent.toFixed(2)}%
          </div>
        </div>
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="text-slate-400 text-sm mb-2">Total positions</div>
          <div className="text-3xl font-bold text-white">
            {portfolios.reduce((sum: number, p: any) => sum + p.num_positions, 0)}
          </div>
        </div>
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="text-slate-400 text-sm mb-2">Total portfolios</div>
          <div className="text-3xl font-bold text-white">{portfolios.length}</div>
        </div>
      </div>

      {/* Top Gainers and Losers */}
      <div className="grid grid-cols-2 gap-6">
        {/* Top Gainers */}
        <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800">
          <h3 className="text-lg font-bold text-white mb-4">🚀 Top Gainers</h3>
          {topGainers.length === 0 ? (
            <div className="text-slate-400 text-sm text-center py-8">No positions</div>
          ) : (
            <div className="space-y-3">
              {topGainers.map((holding, idx) => (
                <div key={`${holding.ticker}-${idx}`} className="flex items-center justify-between p-3 bg-slate-800/30 rounded border border-slate-700/50 hover:border-green-600/50 transition">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">{holding.ticker}</span>
                      <span className="text-xs text-slate-400">
                        {holding.portfolios.length > 1 ? `(${holding.portfolios.length} ptf)` : holding.portfolios[0]}
                      </span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      {holding.quantity} shares • ${holding.totalValue.toFixed(0)} value
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-green-400 font-bold">{holding.gainPercent.toFixed(2)}%</div>
                    <div className="text-xs text-green-400">${holding.totalGain.toFixed(0)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top Losers */}
        <div className="bg-slate-900/50 rounded-lg p-6 border border-slate-800">
          <h3 className="text-lg font-bold text-white mb-4">📉 Top Losers</h3>
          {topLosers.length === 0 ? (
            <div className="text-slate-400 text-sm text-center py-8">No positions</div>
          ) : (
            <div className="space-y-3">
              {topLosers.map((holding, idx) => (
                <div key={`${holding.ticker}-${idx}`} className="flex items-center justify-between p-3 bg-slate-800/30 rounded border border-slate-700/50 hover:border-red-600/50 transition">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">{holding.ticker}</span>
                      <span className="text-xs text-slate-400">
                        {holding.portfolios.length > 1 ? `(${holding.portfolios.length} ptf)` : holding.portfolios[0]}
                      </span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      {holding.quantity} shares • ${holding.totalValue.toFixed(0)} value
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-red-400 font-bold">{holding.gainPercent.toFixed(2)}%</div>
                    <div className="text-xs text-red-400">${holding.totalGain.toFixed(0)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
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
