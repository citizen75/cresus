import { usePortfolioDetails, usePortfolioMetrics, usePortfolioHistory, usePortfolioAllocation, useTopHoldings } from '@/hooks/usePortfolio'
import PortfolioChart from '@/components/PortfolioChart'
import { PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'
import { useState } from 'react'

interface PortfolioOverviewProps {
  name: string
}

export default function PortfolioOverview({ name }: PortfolioOverviewProps) {
  const { data: details, isLoading: detailsLoading } = usePortfolioDetails(name)
  const { data: metrics, isLoading: metricsLoading } = usePortfolioMetrics(name)
  const { data: history, isLoading: historyLoading } = usePortfolioHistory(name)
  const { data: allocation, isLoading: allocationLoading } = usePortfolioAllocation(name)
  const { data: holdings, isLoading: holdingsLoading } = useTopHoldings(name)

  const [timeRange, setTimeRange] = useState('1M')

  if (detailsLoading || metricsLoading || historyLoading) {
    return <div className="text-slate-400">Loading portfolio...</div>
  }

  const totalValue = details?.total_value || 0
  const dailyChange = 12540.32 // Mock data
  const dailyChangePercent = 1.87

  const chartColors = ['#a78bfa', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6']
  const allocationData = allocation?.positions?.map((pos: any) => ({
    name: pos.ticker,
    value: pos.weight,
  })) || []

  const performanceData = history?.history?.slice(-30) || [
    { date: '2026-01-01', value: 100000 },
    { date: '2026-05-01', value: 100000 },
  ]

  return (
    <div className="space-y-6">
      {/* Total Value Section */}
      <div className="bg-gradient-to-br from-slate-900 to-slate-950 rounded-lg p-6 border border-slate-800">
        <div className="flex items-end justify-between mb-6">
          <div>
            <p className="text-slate-400 text-sm mb-2">Total value</p>
            <p className="text-5xl font-bold text-white">€{totalValue.toLocaleString('de-DE', { maximumFractionDigits: 2 })}</p>
            <p className="text-green-400 text-lg mt-2">+€{dailyChange.toLocaleString()} (+{dailyChangePercent}%) Today</p>
          </div>
          <div className="flex gap-2">
            {['1D', '1W', '1M', '3M', 'YTD', '1Y', 'All'].map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-2 rounded text-sm font-medium transition ${
                  timeRange === range
                    ? 'bg-purple-600 text-white'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>

        {/* Chart */}
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={performanceData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#a78bfa" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" stroke="#94a3b8" style={{ fontSize: '12px' }} />
              <YAxis stroke="#94a3b8" style={{ fontSize: '12px' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }}
                labelStyle={{ color: '#f1f5f9' }}
                formatter={(value) => ['€' + value.toLocaleString(), 'Value']}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#a78bfa"
                strokeWidth={2}
                dot={false}
                fillOpacity={1}
                fill="url(#colorValue)"
                name="Portfolio Value"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Three Column Layout */}
      <div className="grid grid-cols-3 gap-6">
        {/* Allocation */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold text-lg mb-6">Allocation</h3>
          <div className="flex items-center justify-center">
            <div className="w-48 h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={allocationData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {allocationData.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={chartColors[index % chartColors.length]} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="mt-6 space-y-3">
            {allocationData.map((item: any, index: number) => (
              <div key={item.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: chartColors[index % chartColors.length] }}></div>
                  <span className="text-slate-400 text-sm">{item.name}</span>
                </div>
                <span className="text-white font-medium text-sm">{item.value.toFixed(1)}%</span>
              </div>
            ))}
          </div>
          <div className="mt-6 pt-6 border-t border-slate-700">
            <div className="text-center">
              <p className="text-slate-400 text-sm">Total value</p>
              <p className="text-white font-bold">€{totalValue.toLocaleString('de-DE', { maximumFractionDigits: 0 })}</p>
              <p className="text-slate-400 text-xs">{details?.num_positions || 0} positions</p>
            </div>
          </div>
        </div>

        {/* Performance */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold text-lg mb-6">Performance</h3>
          <div className="space-y-4">
            <div>
              <p className="text-slate-400 text-sm mb-2">YTD return</p>
              <p className="text-green-400 text-2xl font-bold">+28.74%</p>
              <p className="text-slate-400 text-xs mt-1">vs. SPY +11.02%</p>
            </div>
            <div className="pt-4 border-t border-slate-700 space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-slate-400 text-sm">Since inception (Feb 2024)</span>
                <span className="text-green-400 font-medium text-sm">+34.21%</span>
              </div>
            </div>
          </div>
          <button className="w-full mt-6 px-4 py-2 text-purple-400 hover:text-purple-300 text-sm font-medium transition">
            View performance →
          </button>
        </div>

        {/* Risk Overview */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold text-lg mb-6">Risk overview</h3>
          <div className="space-y-4">
            <div className="bg-slate-800/50 rounded p-4">
              <p className="text-slate-400 text-xs uppercase mb-2">Risk score</p>
              <div className="flex items-end gap-2">
                <p className="text-orange-400 text-3xl font-bold">6.2</p>
                <p className="text-slate-400 text-sm mb-1">/10</p>
              </div>
              <p className="text-slate-400 text-xs mt-2">Moderate</p>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-slate-400 text-sm">Volatility (1Y)</span>
                <span className="text-white font-medium">18.7%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400 text-sm">Max drawdown</span>
                <span className="text-red-400 font-medium">-12.3%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400 text-sm">Sharpe ratio</span>
                <span className="text-white font-medium">{metrics?.sharpe_ratio || 1.42}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Top Holdings */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden">
        <div className="p-6 border-b border-slate-800">
          <h3 className="text-white font-bold text-lg">Top holdings</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-800/50 border-b border-slate-800">
              <tr>
                <th className="px-6 py-4 text-left text-slate-400 font-medium">Name</th>
                <th className="px-6 py-4 text-left text-slate-400 font-medium">Weight</th>
                <th className="px-6 py-4 text-left text-slate-400 font-medium">Value</th>
                <th className="px-6 py-4 text-left text-slate-400 font-medium">Today</th>
                <th className="px-6 py-4 text-left text-slate-400 font-medium">YTD</th>
              </tr>
            </thead>
            <tbody>
              {!holdings?.holdings || holdings.holdings.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                    No holdings found
                  </td>
                </tr>
              ) : (
                holdings.holdings.map((holding: any) => (
                  <tr key={holding.ticker} className="border-t border-slate-800 hover:bg-slate-800/30 transition">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 bg-slate-700 rounded flex items-center justify-center text-xs font-bold text-white">
                          {holding.ticker.charAt(0)}
                        </div>
                        <div>
                          <p className="text-white font-medium">{holding.ticker}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-white font-medium">{holding.weight.toFixed(1)}%</td>
                    <td className="px-6 py-4 text-white">€{holding.value.toLocaleString('de-DE', { maximumFractionDigits: 2 })}</td>
                    <td className={`px-6 py-4 font-medium ${holding.today_change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {holding.today_change > 0 ? '+' : ''}{holding.today_change.toFixed(2)}%
                    </td>
                    <td className={`px-6 py-4 font-medium ${holding.ytd_change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {holding.ytd_change > 0 ? '+' : ''}{holding.ytd_change.toFixed(2)}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-900">
          <button className="text-purple-400 hover:text-purple-300 text-sm font-medium transition">
            View all holdings →
          </button>
        </div>
      </div>
    </div>
  )
}
