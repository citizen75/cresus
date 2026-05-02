import { usePortfolioMetrics, useCurrentPrices } from '@/hooks/usePortfolio'
import { useState } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'
import PositionModal from './PositionModal'

interface HoldingsViewProps {
  name: string
  onViewTransactions?: (ticker: string) => void
}

const chartColors = ['#a78bfa', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6']

export default function HoldingsView({ name, onViewTransactions }: HoldingsViewProps) {
  const { data: metrics } = usePortfolioMetrics(name)
  const { data: priceData, isLoading: isPricesLoading, error: pricesError } = useCurrentPrices(name)
  const [activeTab, setActiveTab] = useState('positions')
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null)
  const [positionModalMode, setPositionModalMode] = useState<'buy' | 'sell' | null>(null)
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const [selectedPositionData, setSelectedPositionData] = useState<any>(null)

  const positions = priceData?.positions || []
  const totalValue = priceData?.total_value || 0
  const itemsPerPage = 10
  const totalPages = Math.ceil(positions.length / itemsPerPage)
  const paginatedPositions = positions.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)

  // Calculate sector exposure from positions
  const sectorMap = new Map<string, number>()
  positions.forEach((pos: any) => {
    const sector = pos.sector || 'Unknown'
    sectorMap.set(sector, (sectorMap.get(sector) || 0) + pos.position_value)
  })

  const sectorData = Array.from(sectorMap.entries()).map(([name, value]) => ({
    name,
    value: totalValue > 0 ? (value / totalValue) * 100 : 0,
  }))

  // Calculate summary metrics
  const unrealizedPNL = positions.reduce((sum: number, pos: any) => sum + (pos.position_gain || 0), 0)
  const unrealizedPNLPercent = totalValue > 0 ? (unrealizedPNL / (totalValue - unrealizedPNL)) * 100 : 0
  const dayPNL = 0  // Would need historical data to calculate
  const dayPNLPercent = 0
  const cash = 0  // Would come from portfolio cash balance
  const cashPercent = 0
  const invested = totalValue
  const investedPercent = 100

  const tabs = ['Overview', 'Positions', 'Allocation', 'Performance', 'Risk', 'Transactions', 'Exposure', 'Income']

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Holdings</h2>
          <p className="text-slate-400 text-sm mt-1">
            {isPricesLoading ? 'Loading real-time prices...' : 'Manage your investment positions'}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => {
              setPositionModalMode('buy')
              setSelectedTicker(null)
            }}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition text-sm"
          >
            + Buy
          </button>
          {selectedPosition && (
            <button
              onClick={() => {
                setPositionModalMode('sell')
                setSelectedTicker(selectedPosition)
              }}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition text-sm"
            >
              📉 Sell
            </button>
          )}
          <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-medium transition text-sm">
            Rebalance
          </button>
        </div>
      </div>

      {/* Error Message */}
      {pricesError && (
        <div className="p-4 bg-red-900/30 border border-red-800 rounded text-red-400 text-sm">
          Failed to load real-time prices: {pricesError instanceof Error ? pricesError.message : 'Unknown error'}
        </div>
      )}

      {/* Portfolio Summary Cards */}
      <div className="grid grid-cols-5 gap-4">
        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Total Value</p>
          <p className="text-white font-bold text-2xl">€{totalValue.toLocaleString('de-DE', { maximumFractionDigits: 2 })}</p>
          <p className="text-green-400 text-sm mt-1">+€12,540.32 (+1.87%)</p>
        </div>

        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Day P&L</p>
          <p className="text-green-400 font-bold text-2xl">+€{dayPNL.toLocaleString('de-DE', { maximumFractionDigits: 2 })}</p>
          <p className="text-green-400 text-sm mt-1">(+{dayPNLPercent.toFixed(2)}%)</p>
        </div>

        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Unrealized P&L</p>
          <p className="text-green-400 font-bold text-2xl">+€{unrealizedPNL.toLocaleString('de-DE', { maximumFractionDigits: 2 })}</p>
          <p className="text-green-400 text-sm mt-1">(+{unrealizedPNLPercent.toFixed(2)}%)</p>
        </div>

        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Cash</p>
          <p className="text-white font-bold text-2xl">€{cash.toLocaleString('de-DE', { maximumFractionDigits: 2 })}</p>
          <p className="text-slate-400 text-sm mt-1">({cashPercent.toFixed(1)}%)</p>
        </div>

        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Invested</p>
          <p className="text-white font-bold text-2xl">€{invested.toLocaleString('de-DE', { maximumFractionDigits: 2 })}</p>
          <p className="text-slate-400 text-sm mt-1">({investedPercent.toFixed(1)}%)</p>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left: Holdings Table */}
        <div className="col-span-2">
          {/* Tab Navigation */}
          <div className="border-b border-slate-800 mb-6">
            <div className="flex gap-6 overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab.toLowerCase())}
                  className={`px-1 py-3 font-medium text-sm transition border-b-2 whitespace-nowrap ${
                    activeTab === tab.toLowerCase()
                      ? 'border-purple-600 text-white'
                      : 'border-transparent text-slate-400 hover:text-slate-300'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Filters and Search */}
          <div className="flex gap-3 mb-6">
            <div className="flex-1 relative">
              <input
                type="text"
                placeholder="Search by symbol or company..."
                className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600"
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500">🔍</span>
            </div>

            <select className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition">
              <option>All positions</option>
              <option>Long only</option>
              <option>Short only</option>
            </select>

            <select className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition">
              <option>All sectors</option>
              {Array.from(sectorMap.keys())
                .sort()
                .map((sector: string) => (
                  <option key={sector} value={sector}>
                    {sector}
                  </option>
                ))}
            </select>

            <select className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition">
              <option>All assets</option>
              {Array.from(new Set(positions.map((p: any) => p.asset_type || 'Stock')) as Set<string>)
                .sort()
                .map((type: string) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
            </select>

            <button className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 transition">
              ⚙️
            </button>
          </div>

          {/* Holdings Table */}
          <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
            {positions.length === 0 ? (
              <div className="p-12 text-center text-slate-400">
                {isPricesLoading ? (
                  <p>Loading positions...</p>
                ) : (
                  <p>No positions in this portfolio</p>
                )}
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-800/50 border-b border-slate-800">
                      <tr>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">Symbol</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">Company</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">Sector</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">Type</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">Weight</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">Shares</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">Avg. Cost</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">Price</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">Market Value</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">Unrealized P&L</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">P&L %</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedPositions.map((pos: any) => {
                    const weight = (pos.position_value / totalValue * 100)
                    return (
                      <tr
                        key={pos.ticker}
                        onClick={() => setSelectedPosition(pos.ticker)}
                        className={`border-t border-slate-800 hover:bg-slate-800/30 transition cursor-pointer ${
                          selectedPosition === pos.ticker ? 'bg-slate-800/50' : ''
                        }`}
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 bg-gradient-to-br from-purple-500 to-violet-600 rounded flex items-center justify-center text-xs font-bold text-white">
                              {pos.ticker.charAt(0)}
                            </div>
                            <span className="text-white font-medium">{pos.ticker}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-slate-300 text-sm font-medium">{pos.company_name || pos.ticker}</td>
                        <td className="px-4 py-3 text-slate-300 text-sm">
                          <span className="inline-block px-2 py-1 rounded bg-slate-800/50 text-xs">
                            {pos.sector || 'Unknown'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-300 text-sm">{pos.asset_type || 'Stock'}</td>
                        <td className="px-4 py-3 text-white font-medium">{weight.toFixed(2)}%</td>
                        <td className="px-4 py-3 text-white">{pos.quantity}</td>
                        <td className="px-4 py-3 text-white">€{pos.avg_entry_price.toLocaleString('de-DE', { maximumFractionDigits: 2 })}</td>
                        <td className="px-4 py-3 text-white">€{pos.current_price.toLocaleString('de-DE', { maximumFractionDigits: 2 })}</td>
                        <td className="px-4 py-3 text-white font-medium">€{pos.position_value.toLocaleString('de-DE', { maximumFractionDigits: 2 })}</td>
                        <td className={`px-4 py-3 font-medium ${pos.position_gain >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {pos.position_gain >= 0 ? '+' : ''}€{pos.position_gain.toLocaleString('de-DE', { maximumFractionDigits: 2 })}
                        </td>
                        <td className={`px-4 py-3 font-medium ${pos.position_gain_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {pos.position_gain_pct > 0 ? '+' : ''}{pos.position_gain_pct.toFixed(2)}%
                        </td>
                        <td className="px-4 py-3 text-green-400 font-medium">+0.45%</td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => onViewTransactions?.(pos.ticker)}
                            className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded transition"
                            title="View and edit transactions"
                          >
                            Transactions
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="px-6 py-4 border-t border-slate-800 bg-slate-900 flex items-center justify-between text-sm">
              <p className="text-slate-400">
                Showing {Math.min((currentPage - 1) * itemsPerPage + 1, positions.length)}-{Math.min(currentPage * itemsPerPage, positions.length)} of {positions.length} positions
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="px-2 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded hover:bg-slate-700 disabled:opacity-50 transition"
                >
                  ←
                </button>
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => i + 1).map((page) => (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={`px-2 py-1 rounded transition ${
                      page === currentPage
                        ? 'bg-purple-600 text-white'
                        : 'bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    {page}
                  </button>
                ))}
                <button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  className="px-2 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded hover:bg-slate-700 disabled:opacity-50 transition"
                >
                  →
                </button>
              </div>
            </div>
            </>
            )}
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="space-y-6">
          {/* Allocation Pie Chart */}
          <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-bold">Allocation</h3>
              <button className="text-purple-400 hover:text-purple-300 text-sm">View full →</button>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-40 h-40">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={positions.slice(0, 5).map((pos: any) => ({
                        name: pos.ticker,
                        value: pos.position_value,
                      }))}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={70}
                      paddingAngle={1}
                      dataKey="value"
                    >
                      {positions.map((_: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={chartColors[index % chartColors.length]} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="text-center mt-4">
                <p className="text-slate-400 text-xs mb-1">Total Value</p>
                <p className="text-white font-bold text-lg">€{totalValue.toLocaleString('de-DE', { maximumFractionDigits: 0 })}</p>
              </div>
            </div>
          </div>

          {/* Sector Exposure */}
          <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-bold">Sector Exposure</h3>
              <button className="text-purple-400 hover:text-purple-300 text-sm">View full →</button>
            </div>
            <div className="space-y-3">
              {sectorData.map((sector, index) => (
                <div key={sector.name}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-slate-400 text-sm">{sector.name}</span>
                    <span className="text-white font-medium text-sm">{sector.value.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2">
                    <div
                      className="h-2 rounded-full"
                      style={{
                        width: `${sector.value}%`,
                        backgroundColor: chartColors[index % chartColors.length],
                      }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Risk Snapshot */}
          <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-bold">Risk Snapshot</h3>
              <button className="text-purple-400 hover:text-purple-300 text-sm">View full →</button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-slate-400 text-xs uppercase mb-2">Portfolio Beta</p>
                <p className="text-white font-bold text-xl">1.08</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs uppercase mb-2">Sharpe Ratio</p>
                <p className="text-white font-bold text-xl">{metrics?.sharpe_ratio || 1.42}</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs uppercase mb-2">Max Drawdown</p>
                <p className="text-red-400 font-bold text-xl">-12.3%</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs uppercase mb-2">Volatility (1Y)</p>
                <p className="text-white font-bold text-xl">18.7%</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs uppercase mb-2">VaR (95%, 1D)</p>
                <p className="text-white font-bold text-xl">-2.31%</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs uppercase mb-2">Tracking Error</p>
                <p className="text-white font-bold text-xl">6.12%</p>
              </div>
            </div>
          </div>
        </div>
      </div>


      {/* Position Modal */}
      <PositionModal
        isOpen={positionModalMode !== null}
        mode={positionModalMode}
        ticker={selectedTicker || undefined}
        positionData={selectedPositionData}
        onClose={() => {
          setPositionModalMode(null)
          setSelectedTicker(null)
          setSelectedPositionData(null)
        }}
        onSuccess={() => {
          // Refetch portfolio details
          window.location.reload()
        }}
        portfolioName={name}
      />
    </div>
  )
}
