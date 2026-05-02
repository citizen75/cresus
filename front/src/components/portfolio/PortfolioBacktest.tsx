import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface PortfolioBacktestProps {
  name: string
}

const backtestPerformanceData = [
  { date: '2018', returnBk: -8.2, returnBench: -4.4 },
  { date: '2019', returnBk: 31.2, returnBench: 31.5 },
  { date: '2020', returnBk: 38.7, returnBench: 16.8 },
  { date: '2021', returnBk: 24.1, returnBench: 28.7 },
  { date: '2022', returnBk: -12.6, returnBench: -18.1 },
  { date: '2023', returnBk: 35.4, returnBench: 25.2 },
  { date: '2024', returnBk: 12.8, returnBench: 9.7 },
]

const returnBreakdownData = [
  { month: 'Jan', value: 2.1 },
  { month: 'Feb', value: -1.3 },
  { month: 'Mar', value: 3.4 },
  { month: 'Apr', value: 2.8 },
  { month: 'May', value: 1.9 },
]

const topContributors = [
  { stock: 'NVIDIA', contribution: '+18.61%', impact: 'Strong semiconductor demand' },
  { stock: 'Microsoft', contribution: '+12.35%', impact: 'Azure cloud growth' },
  { stock: 'TSMC', contribution: '+10.23%', impact: 'AI chip manufacturing' },
  { stock: 'Palantir', contribution: '+8.91%', impact: 'Government contracts' },
  { stock: 'Snowflake', contribution: '+6.44%', impact: 'Cloud data platforms' },
]

export default function PortfolioBacktest({ name }: PortfolioBacktestProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Backtest analysis</h2>
          <p className="text-slate-400 text-sm mt-1">Historical performance from Jan 2018 - May 2024</p>
        </div>
        <button className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition">
          Create backtest
        </button>
      </div>

      {/* Backtest Summary Cards */}
      <div className="grid grid-cols-6 gap-4">
        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Total return</p>
          <p className="text-white font-bold text-xl">+156.35%</p>
          <p className="text-slate-400 text-xs">vs. SPY +88.2%</p>
        </div>
        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">CAGR</p>
          <p className="text-white font-bold text-xl">19.7%</p>
          <p className="text-slate-400 text-xs">vs. SPY 10.2%</p>
        </div>
        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Max drawdown</p>
          <p className="text-red-400 font-bold text-xl">-18.6%</p>
          <p className="text-slate-400 text-xs">vs. SPY -24.7%</p>
        </div>
        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Sharpe ratio</p>
          <p className="text-white font-bold text-xl">1.58</p>
          <p className="text-slate-400 text-xs">vs. SPY 0.84</p>
        </div>
        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Win rate</p>
          <p className="text-white font-bold text-xl">64.8%</p>
          <p className="text-slate-400 text-xs">242/373 months</p>
        </div>
        <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
          <p className="text-slate-400 text-xs uppercase mb-2">Avg holding period</p>
          <p className="text-white font-bold text-xl">6.5</p>
          <p className="text-slate-400 text-xs">Months</p>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Return Breakdown */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold text-lg mb-6">Return breakdown</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={returnBreakdownData} margin={{ top: 20, right: 30, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="month" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }} />
                <Bar dataKey="value" fill="#10b981" name="Monthly Return" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 pt-4 border-t border-slate-700 grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-slate-400">Stock selection</p>
              <p className="text-green-400 font-bold">+12.4%</p>
            </div>
            <div>
              <p className="text-slate-400">Timing effect</p>
              <p className="text-green-400 font-bold">+3.2%</p>
            </div>
          </div>
        </div>

        {/* Performance Comparison */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold text-lg mb-6">Annual returns</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={backtestPerformanceData} margin={{ top: 20, right: 30, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }} />
                <Legend />
                <Line type="monotone" dataKey="returnBk" stroke="#a78bfa" strokeWidth={2} name="Growth Portfolio (Backtest)" dot={{ fill: '#a78bfa' }} />
                <Line type="monotone" dataKey="returnBench" stroke="#475569" strokeWidth={2} name="SPY (Benchmark)" dot={{ fill: '#475569' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Performance Table */}
      <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
        <h3 className="text-white font-bold text-lg mb-6">Performance by year</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-800/50 border-b border-slate-800">
              <tr>
                <th className="px-6 py-3 text-left text-slate-400 font-medium">Year</th>
                <th className="px-6 py-3 text-left text-slate-400 font-medium">Portfolio</th>
                <th className="px-6 py-3 text-left text-slate-400 font-medium">SPY</th>
                <th className="px-6 py-3 text-left text-slate-400 font-medium">Outperformance</th>
                <th className="px-6 py-3 text-left text-slate-400 font-medium">Volatility</th>
                <th className="px-6 py-3 text-left text-slate-400 font-medium">Sharpe</th>
              </tr>
            </thead>
            <tbody>
              {backtestPerformanceData.map((row) => {
                const outperformance = row.returnBk - row.returnBench
                return (
                  <tr key={row.date} className="border-t border-slate-800 hover:bg-slate-800/30 transition">
                    <td className="px-6 py-4 text-white font-medium">{row.date}</td>
                    <td className={`px-6 py-4 font-medium ${row.returnBk >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {row.returnBk > 0 ? '+' : ''}{row.returnBk.toFixed(1)}%
                    </td>
                    <td className={`px-6 py-4 font-medium ${row.returnBench >= 0 ? 'text-slate-400' : 'text-red-400'}`}>
                      {row.returnBench > 0 ? '+' : ''}{row.returnBench.toFixed(1)}%
                    </td>
                    <td className={`px-6 py-4 font-medium ${outperformance >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {outperformance > 0 ? '+' : ''}{outperformance.toFixed(1)}%
                    </td>
                    <td className="px-6 py-4 text-slate-400">{(Math.random() * 15 + 10).toFixed(1)}%</td>
                    <td className="px-6 py-4 text-white">{(Math.random() * 1.5 + 0.5).toFixed(2)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top Contributors */}
      <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
        <h3 className="text-white font-bold text-lg mb-6">Top contributors (backtest)</h3>
        <div className="space-y-4">
          {topContributors.map((contributor, index) => (
            <div key={contributor.stock} className="flex items-start justify-between p-4 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1">
                  <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-violet-600 rounded flex items-center justify-center text-xs font-bold text-white">
                    {index + 1}
                  </div>
                  <p className="text-white font-bold">{contributor.stock}</p>
                </div>
                <p className="text-slate-400 text-sm ml-11">{contributor.impact}</p>
              </div>
              <div className="text-right">
                <p className="text-green-400 font-bold text-lg">{contributor.contribution}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
