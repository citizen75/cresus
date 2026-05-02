import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface DataPoint {
  date: string
  value: number
}

interface PortfolioChartProps {
  data: DataPoint[]
  title: string
}

export default function PortfolioChart({ data, title }: PortfolioChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-96 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-center">
        <p className="text-slate-400">No data available</p>
      </div>
    )
  }

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-lg p-6">
      <h3 className="text-white font-bold text-lg mb-6">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#a78bfa" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="date"
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
            tick={{ fill: '#94a3b8' }}
          />
          <YAxis
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
            tick={{ fill: '#94a3b8' }}
            label={{ value: '€', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #475569',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#f1f5f9' }}
            formatter={(value) => ['€' + value.toLocaleString(), 'Value']}
          />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
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
  )
}
