import { useState } from 'react'
import TradingChart from '@/components/TradingChart'

export default function ChartPage() {
  const [selectedTicker, setSelectedTicker] = useState('CAC')
  const [timeframe, setTimeframe] = useState('1D')

  const portfolioHoldings = [
    { symbol: 'ATC', price: 37.30, change: 1.60, changePercent: 4.48 },
    { symbol: 'EMI', price: 14.74, change: 0.33, changePercent: 2.29 },
    { symbol: 'RXL', price: 37.34, change: 0.86, changePercent: 2.36 },
    { symbol: 'ETL', price: 2.936, change: 0.029, changePercent: 1.00 },
    { symbol: 'SU', price: 263.40, change: 3.10, changePercent: 1.17 },
    { symbol: 'BB', price: 57.5, change: 0.3, changePercent: 0.52 },
    { symbol: 'RNO', price: 28.10, change: 0.60, changePercent: 2.18 },
    { symbol: 'AM', price: 84.95, change: 0.50, changePercent: 0.59 },
    { symbol: 'ENG', price: 27.40, change: 0.24, changePercent: 0.88 },
    { symbol: 'QD', price: 11.44, change: -0.02, changePercent: -0.17 },
  ]


  return (
    <div className="flex flex-col h-full bg-slate-950">
      {/* Header */}
      <div className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <div className="text-white font-bold text-lg">{selectedTicker}</div>
            <div className="text-xs text-slate-400">Multi Units France Sicav - Amundi CAC 40 UCITS ETF</div>
          </div>
          <div className="text-right">
            <div className="text-white font-bold text-xl">80.20 EUR</div>
            <div className="text-sm text-green-400">+0.20 +0.25%</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1 bg-slate-800 hover:bg-slate-700 rounded text-slate-300 text-sm">
            Add to watchlist
          </button>
          <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded text-white text-sm font-medium">
            Trade
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar - Holdings */}
        <div className="w-80 bg-slate-900 border-r border-slate-800 flex flex-col overflow-hidden">
          {/* Holdings header */}
          <div className="px-4 py-4 border-b border-slate-800 flex-shrink-0">
            <div className="text-sm font-bold text-white mb-2">Holdings</div>
            <div className="grid grid-cols-4 gap-2 text-xs text-slate-400">
              <div>Symbol</div>
              <div className="text-right">Price</div>
              <div className="text-right">Change</div>
              <div className="text-right">%</div>
            </div>
          </div>

          {/* Holdings list */}
          <div className="flex-1 overflow-y-auto">
            {portfolioHoldings.map((holding) => (
              <div
                key={holding.symbol}
                onClick={() => setSelectedTicker(holding.symbol)}
                className={`px-4 py-3 border-b border-slate-800 cursor-pointer hover:bg-slate-800/50 transition ${
                  selectedTicker === holding.symbol ? 'bg-purple-600/20' : ''
                }`}
              >
                <div className="grid grid-cols-4 gap-2 items-center">
                  <div className="font-medium text-white text-sm">{holding.symbol}</div>
                  <div className="text-right text-white text-sm">{holding.price.toFixed(2)}</div>
                  <div className={`text-right text-xs ${holding.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {holding.change >= 0 ? '+' : ''}{holding.change.toFixed(2)}
                  </div>
                  <div className={`text-right text-xs ${holding.changePercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {holding.changePercent >= 0 ? '+' : ''}{holding.changePercent.toFixed(2)}%
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Key stats */}
          <div className="px-4 py-4 border-t border-slate-800 text-xs space-y-2 flex-shrink-0">
            <div className="flex justify-between">
              <span className="text-slate-400">Volume</span>
              <span className="text-white">20.99K</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Avg Vol (30D)</span>
              <span className="text-white">38.93K</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Market Cap</span>
              <span className="text-white">$3.18B</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Yield</span>
              <span className="text-white">2.90%</span>
            </div>
          </div>
        </div>

        {/* Center - Chart */}
        <div className="flex-1 bg-slate-950 overflow-hidden">
          <TradingChart timeframe={timeframe} title={selectedTicker} />
        </div>

        {/* Right sidebar - Controls */}
        <div className="w-48 bg-slate-900 border-l border-slate-800 p-4 overflow-y-auto space-y-4">
          {/* Timeframe selector */}
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase mb-2">Timeframe</div>
            <div className="grid grid-cols-3 gap-1">
              {['1D', '1W', '1M', '3M', '6M', '1Y'].map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`py-1 px-2 text-xs rounded transition ${
                    timeframe === tf
                      ? 'bg-purple-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* Indicators */}
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase mb-2">Indicators</div>
            <div className="space-y-2">
              {['MA 20', 'MA 50', 'MA 200', 'RSI 14', 'MACD'].map((indicator) => (
                <label key={indicator} className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" className="rounded border-slate-600" defaultChecked={indicator === 'MA 20'} />
                  <span className="text-sm text-slate-300">{indicator}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Chart Type */}
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase mb-2">Chart Type</div>
            <div className="space-y-1">
              {['Candlestick', 'Line', 'Bars'].map((type) => (
                <button
                  key={type}
                  className={`w-full text-left px-3 py-2 text-sm rounded transition ${
                    type === 'Candlestick'
                      ? 'bg-purple-600 text-white'
                      : 'text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
