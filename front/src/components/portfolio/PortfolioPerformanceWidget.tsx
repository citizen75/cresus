import { usePortfolioMetrics, usePortfolioHistory, usePortfolioDetails, useCurrentPrices } from '@/hooks/usePortfolio'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { formatCurrency } from '@/utils/currency'

interface PortfolioPerformanceWidgetProps {
  portfolioName: string
}

export default function PortfolioPerformanceWidget({ portfolioName }: PortfolioPerformanceWidgetProps) {
  const { data: details, isLoading: isDetailsLoading } = usePortfolioDetails(portfolioName)
  const { data: metrics, isLoading: isMetricsLoading } = usePortfolioMetrics(portfolioName)
  const { data: history, isLoading: isHistoryLoading } = usePortfolioHistory(portfolioName)
  const { data: currentPrices, isLoading: isCurrentPricesLoading } = useCurrentPrices(portfolioName)

  const isLoading = isDetailsLoading || isMetricsLoading || isHistoryLoading || isCurrentPricesLoading
  const currency = details?.currency || 'USD'
  const initialCapital = details?.initial_capital || 0
  const cash = currentPrices?.cash ?? 0
  const positionsValue = currentPrices?.total_value ?? 0

  const historyArray = history?.history || []
  const pnlData = historyArray.map((entry: any) => ({
    date: entry.date,
    value: (entry.value || 0) - initialCapital,
  }))

  const latestPnl = pnlData.length > 0 ? pnlData[pnlData.length - 1].value : 0
  const latestPnlPct = initialCapital > 0 ? (latestPnl / initialCapital) * 100 : 0

  const metricChips = [
    { label: 'Total Gain', value: `${(metrics?.total_gain_pct ?? 0).toFixed(2)}%` },
    { label: 'Sharpe', value: (metrics?.sharpe_ratio ?? 0).toFixed(2) },
    { label: 'Sortino', value: (metrics?.sortino_ratio ?? 0).toFixed(2) },
    { label: 'Calmar', value: (metrics?.calmar_ratio ?? 0).toFixed(2) },
    { label: 'Max DD', value: `${(metrics?.max_drawdown_pct ?? 0).toFixed(1)}%`, negative: true },
    { label: 'Profit Factor', value: (metrics?.profit_factor ?? 0).toFixed(2) },
    { label: 'Expectancy', value: `${(metrics?.expectancy_pct ?? 0).toFixed(1)}%` },
    { label: 'SQN', value: (metrics?.sqn ?? 0).toFixed(2) },
    { label: 'Kelly', value: `${(metrics?.kelly_criterion_pct ?? 0).toFixed(1)}%` },
    { label: 'Trades', value: metrics?.num_trades ?? 0 },
    { label: 'Buy/Sell', value: `${metrics?.buy_trades ?? 0}/${metrics?.sell_trades ?? 0}` },
    { label: 'Fees', value: formatCurrency(metrics?.total_fees ?? 0, currency) },
  ]

  if (isLoading) {
    return <div className="text-center py-8 text-slate-400 text-sm">Loading performance...</div>
  }

  return (
    <div className="h-full flex flex-col gap-2 p-3 overflow-y-auto">
      {/* Header: Total P&L, Cash, Positions inline */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <p className="text-slate-400 text-xs">Total P&L</p>
          <div className="flex items-baseline gap-2">
            <p className={`text-xl font-bold ${latestPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {latestPnl >= 0 ? '+' : ''}{formatCurrency(latestPnl, currency)}
            </p>
            <p className={`text-xs ${latestPnlPct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              ({latestPnlPct >= 0 ? '+' : ''}{latestPnlPct.toFixed(2)}%)
            </p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-slate-400 text-xs">Cash</p>
          <p className="text-white font-semibold text-sm">{formatCurrency(cash, currency)}</p>
        </div>
        <div className="text-right">
          <p className="text-slate-400 text-xs">Positions</p>
          <p className="text-white font-semibold text-sm">{formatCurrency(positionsValue, currency)}</p>
        </div>
      </div>

      {/* Compact metric chips */}
      <div className="grid grid-cols-4 gap-1.5 flex-shrink-0">
        {metricChips.map((chip) => (
          <div key={chip.label} className="bg-slate-800/50 rounded px-2 py-1.5 border border-slate-800">
            <p className="text-slate-500 text-[10px] uppercase leading-tight">{chip.label}</p>
            <p className={`font-semibold text-sm leading-tight ${chip.negative ? 'text-red-400' : 'text-white'}`}>{chip.value}</p>
          </div>
        ))}
      </div>

      {/* Condensed historical P&L chart */}
      <div className="flex-1 min-h-[90px]">
        {pnlData.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500 text-xs">No history available</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <LineChart data={pnlData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 10 }} tickLine={false} minTickGap={40} />
              <YAxis stroke="#64748b" tick={{ fontSize: 10 }} tickLine={false} width={48} domain={['dataMin', 'dataMax']} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '6px', fontSize: '12px' }}
                labelStyle={{ color: '#f1f5f9' }}
                formatter={(value) => [formatCurrency(Number(value), currency), 'P&L']}
              />
              <Line type="monotone" dataKey="value" stroke="#a78bfa" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
