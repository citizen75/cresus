import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface ChartDataPoint {
  date: string
  close: number
  ema_20?: number
  ema_50?: number
}

interface CardChartProps {
  data: ChartDataPoint[]
  ticker: string
  showVariation?: boolean
}

export default function CardChart({ data, ticker, showVariation = true }: CardChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="p-4 h-48 bg-slate-800/20 flex items-center justify-center">
        <p className="text-slate-400 text-sm">No data available</p>
      </div>
    )
  }

  const firstPrice = data[0]?.close || 0
  const lastPrice = data[data.length - 1]?.close || 0
  const variation = firstPrice !== 0 ? ((lastPrice - firstPrice) / firstPrice) * 100 : 0
  const isPositive = variation >= 0

  return (
    <div className="relative p-4 bg-slate-800/20">
      {/* Variation Badge */}
      {showVariation && (
        <div className="absolute top-4 right-4 z-10">
          <div className={`px-3 py-1 rounded-lg backdrop-blur-sm flex items-center gap-1 ${
            isPositive
              ? 'bg-green-900/40 border border-green-700/50'
              : 'bg-red-900/40 border border-red-700/50'
          }`}>
            <span className={`text-xs font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
              {isPositive ? '↗' : '↘'}
            </span>
            <span className={`text-sm font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
              {isPositive ? '+' : ''}{variation.toFixed(2)}%
            </span>
          </div>
        </div>
      )}

      {/* Chart */}
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 5, right: 30, left: -20, bottom: 0 }}
          >
            <defs>
              <linearGradient id={`gradient-${ticker}`} x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor={isPositive ? '#22c55e' : '#ef4444'}
                  stopOpacity={0.3}
                />
                <stop
                  offset="95%"
                  stopColor={isPositive ? '#22c55e' : '#ef4444'}
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              hide={true}
            />
            <YAxis
              hide={true}
              domain={['dataMin', 'dataMax']}
              type="number"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '0.5rem',
              }}
              formatter={(value: any) => {
                if (typeof value === 'number') {
                  return `€${value.toFixed(2)}`
                }
                return value ? `€${parseFloat(value).toFixed(2)}` : '—'
              }}
              labelFormatter={(label: any) => label}
            />
            <Line
              type="monotone"
              dataKey="close"
              stroke={isPositive ? '#22c55e' : '#ef4444'}
              dot={false}
              strokeWidth={2.5}
              isAnimationActive={false}
              fill={`url(#gradient-${ticker})`}
            />
            {data.some(d => d.ema_20 !== undefined) && (
              <Line
                type="monotone"
                dataKey="ema_20"
                stroke="#3b82f6"
                dot={false}
                strokeWidth={1.5}
                isAnimationActive={false}
                opacity={0.7}
              />
            )}
            {data.some(d => d.ema_50 !== undefined) && (
              <Line
                type="monotone"
                dataKey="ema_50"
                stroke="#f59e0b"
                dot={false}
                strokeWidth={1.5}
                isAnimationActive={false}
                opacity={0.7}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
