interface StrategyBuilderProps {
  name: string
}

export default function StrategyBuilder({ name }: StrategyBuilderProps) {
  return (
    <div className="space-y-6">
      {/* Header with Save Button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Strategy definition</h2>
          <p className="text-slate-400 text-sm mt-1">Define the rules Cresus will use to build and manage this portfolio.</p>
        </div>
        <button className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition">
          Save strategy
        </button>
      </div>

      {/* Strategy Status */}
      <div className="flex items-center gap-2 text-sm">
        <span className="w-2 h-2 bg-green-400 rounded-full"></span>
        <span className="text-green-400">Strategy active</span>
      </div>

      {/* 5 Column Layout */}
      <div className="grid grid-cols-5 gap-6">
        {/* Universe */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold mb-4">Universe</h3>
          <div className="space-y-3">
            <div className="bg-slate-800/50 rounded p-3">
              <p className="text-slate-400 text-xs uppercase mb-1">Universe</p>
              <p className="text-white font-medium text-sm">S&P 500 Equities</p>
            </div>
            <div className="bg-slate-800/50 rounded p-3">
              <p className="text-slate-400 text-xs uppercase mb-1">Includes</p>
              <p className="text-white font-medium text-sm">~500 stocks</p>
            </div>
          </div>
          <button className="w-full mt-4 px-4 py-2 text-purple-400 hover:text-purple-300 text-sm font-medium transition">
            Edit universe
          </button>
        </div>

        {/* Entry Conditions */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold mb-4">Entry conditions</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-2 p-2 bg-green-900/20 rounded border border-green-800/50">
              <span className="w-2 h-2 bg-green-400 rounded-full"></span>
              <span className="text-green-400 text-xs font-medium">AI Relevance Score ≥ 80</span>
            </div>
            <div className="flex items-center gap-2 p-2 bg-green-900/20 rounded border border-green-800/50">
              <span className="w-2 h-2 bg-green-400 rounded-full"></span>
              <span className="text-green-400 text-xs font-medium">Revenue Growth (TTM) ≥ 15%</span>
            </div>
            <div className="flex items-center gap-2 p-2 bg-green-900/20 rounded border border-green-800/50">
              <span className="w-2 h-2 bg-green-400 rounded-full"></span>
              <span className="text-green-400 text-xs font-medium">Gross Margin ≥ 40%</span>
            </div>
          </div>
          <button className="w-full mt-4 px-4 py-2 text-purple-400 hover:text-purple-300 text-sm font-medium transition">
            Edit conditions
          </button>
        </div>

        {/* Exit Conditions */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold mb-4">Exit conditions</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-2 p-2 bg-red-900/20 rounded border border-red-800/50">
              <span className="w-2 h-2 bg-red-400 rounded-full"></span>
              <span className="text-red-400 text-xs font-medium">AI Relevance Score ≤ 40</span>
            </div>
            <div className="flex items-center gap-2 p-2 bg-red-900/20 rounded border border-red-800/50">
              <span className="w-2 h-2 bg-red-400 rounded-full"></span>
              <span className="text-red-400 text-xs font-medium">Revenue Growth (TTM) {'<'} 5%</span>
            </div>
            <div className="flex items-center gap-2 p-2 bg-red-900/20 rounded border border-red-800/50">
              <span className="w-2 h-2 bg-red-400 rounded-full"></span>
              <span className="text-red-400 text-xs font-medium">Drawdown high {'>'} 25%</span>
            </div>
          </div>
          <button className="w-full mt-4 px-4 py-2 text-purple-400 hover:text-purple-300 text-sm font-medium transition">
            Edit conditions
          </button>
        </div>

        {/* Position Sizing */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold mb-4">Position sizing</h3>
          <div className="space-y-3">
            <div>
              <p className="text-slate-400 text-xs uppercase mb-1">Method</p>
              <p className="text-white font-medium text-sm">Risk parity</p>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase mb-1">Target volatility</p>
              <p className="text-white font-medium text-sm">15%</p>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase mb-1">Max position size</p>
              <p className="text-white font-medium text-sm">8%</p>
            </div>
          </div>
          <button className="w-full mt-4 px-4 py-2 text-purple-400 hover:text-purple-300 text-sm font-medium transition">
            Edit rules
          </button>
        </div>

        {/* Rebalance */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <h3 className="text-white font-bold mb-4">Rebalance</h3>
          <div className="space-y-3">
            <div>
              <p className="text-slate-400 text-xs uppercase mb-1">Frequency</p>
              <p className="text-white font-medium text-sm">Weekly</p>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase mb-1">Last rebalance</p>
              <p className="text-white font-medium text-sm">2 days ago</p>
            </div>
            <div>
              <p className="text-slate-400 text-xs uppercase mb-1">Drift threshold</p>
              <p className="text-white font-medium text-sm">5%</p>
            </div>
          </div>
          <button className="w-full mt-4 px-4 py-2 text-purple-400 hover:text-purple-300 text-sm font-medium transition">
            Edit rebalance
          </button>
        </div>
      </div>

      {/* Strategy Summary */}
      <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
        <h3 className="text-white font-bold text-lg mb-6">Strategy summary</h3>
        <div className="grid grid-cols-6 gap-6">
          <div className="bg-slate-800/50 rounded p-4">
            <p className="text-slate-400 text-xs uppercase mb-2">Universe</p>
            <p className="text-white font-bold text-lg">~500</p>
            <p className="text-slate-400 text-xs">Stocks</p>
          </div>
          <div className="bg-slate-800/50 rounded p-4">
            <p className="text-slate-400 text-xs uppercase mb-2">Avg holding period</p>
            <p className="text-white font-bold text-lg">6.2</p>
            <p className="text-slate-400 text-xs">Months</p>
          </div>
          <div className="bg-slate-800/50 rounded p-4">
            <p className="text-slate-400 text-xs uppercase mb-2">Expected turnover</p>
            <p className="text-white font-bold text-lg">63%</p>
            <p className="text-slate-400 text-xs">/year</p>
          </div>
          <div className="bg-slate-800/50 rounded p-4">
            <p className="text-slate-400 text-xs uppercase mb-2">Rebalance opportunity</p>
            <p className="text-white font-bold text-lg">0.2</p>
            <p className="text-slate-400 text-xs">Days</p>
          </div>
          <div className="bg-slate-800/50 rounded p-4">
            <p className="text-slate-400 text-xs uppercase mb-2">Est. annual fees</p>
            <p className="text-white font-bold text-lg">€2,341</p>
            <p className="text-slate-400 text-xs">Based on holdings</p>
          </div>
          <div className="bg-slate-800/50 rounded p-4">
            <p className="text-slate-400 text-xs uppercase mb-2">Strategy style</p>
            <p className="text-white font-bold text-lg">Growth</p>
            <p className="text-slate-400 text-xs">Factor-based</p>
          </div>
        </div>
      </div>
    </div>
  )
}
