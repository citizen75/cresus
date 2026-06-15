import { useState, useEffect } from 'react'
import { api } from '@/services/api'

interface TickerSearchDialogProps {
  isOpen: boolean
  onClose: () => void
  onSelectTicker: (ticker: string, company?: string) => void
  portfolioName?: string
}

interface TickerData {
  ticker: string
  company_name?: string
  asset_type?: string
  exchange?: string
  currency?: string
  sector?: string
  industry?: string
}

export default function TickerSearchDialog({
  isOpen,
  onClose,
  onSelectTicker,
  portfolioName,
}: TickerSearchDialogProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [assetTypeFilter, setAssetTypeFilter] = useState('All')
  const [exchangeFilter, setExchangeFilter] = useState('All')
  const [currencyFilter, setCurrencyFilter] = useState('All')
  const [tickers, setTickers] = useState<TickerData[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [availableExchanges, setAvailableExchanges] = useState<string[]>([])
  const [availableCurrencies, setAvailableCurrencies] = useState<string[]>([])
  const [selectedRow, setSelectedRow] = useState<TickerData | null>(null)

  // Load available tickers on mount
  useEffect(() => {
    if (isOpen) {
      loadTickers()
    }
  }, [isOpen])

  const loadTickers = async () => {
    setIsLoading(true)
    try {
      const response = await api.getAllTickers?.()
      if (response) {
        // Handle both array and object responses
        const tickersList = Array.isArray(response) ? response : response.tickers || []
        setTickers(tickersList)

        // Extract unique exchanges and currencies
        const exchanges = Array.from(new Set(tickersList.map((t: TickerData) => t.exchange).filter(Boolean))) as string[]
        const currencies = Array.from(new Set(tickersList.map((t: TickerData) => t.currency).filter(Boolean))) as string[]

        setAvailableExchanges(exchanges)
        setAvailableCurrencies(currencies)
      }
    } catch (err) {
      console.error('Failed to load tickers:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const filteredTickers = tickers.filter((ticker) => {
    const query = searchQuery.toLowerCase()
    const matchesSearch =
      ticker.ticker.toLowerCase().includes(query) ||
      (ticker.company_name && ticker.company_name.toLowerCase().includes(query))

    const matchesAssetType =
      assetTypeFilter === 'All' || ticker.asset_type === assetTypeFilter

    const matchesExchange =
      exchangeFilter === 'All' || ticker.exchange === exchangeFilter

    const matchesCurrency =
      currencyFilter === 'All' || ticker.currency === currencyFilter

    return matchesSearch && matchesAssetType && matchesExchange && matchesCurrency
  })

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-900 border border-slate-800 rounded-lg w-[90vw] max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800">
          <h2 className="text-xl font-bold text-white">Search Ticker</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition text-2xl"
          >
            ✕
          </button>
        </div>

        {/* Search & Filters */}
        <div className="p-6 space-y-4 border-b border-slate-800">
          {/* Search Input */}
          <div>
            <label className="block text-sm text-slate-400 mb-2">
              Search ticker or company name
            </label>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="e.g., AAPL or Apple"
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
            />
          </div>

          {/* Filters */}
          <div className="grid grid-cols-3 gap-4">
            {/* Asset Type Filter */}
            <div>
              <label className="block text-sm text-slate-400 mb-2">
                Asset Type
              </label>
              <select
                value={assetTypeFilter}
                onChange={(e) => setAssetTypeFilter(e.target.value)}
                className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded text-white focus:outline-none focus:border-purple-500"
              >
                <option>All</option>
                <option>Stock</option>
                <option>ETF</option>
                <option>Crypto</option>
                <option>Bond</option>
              </select>
            </div>

            {/* Exchange Filter */}
            <div>
              <label className="block text-sm text-slate-400 mb-2">
                Exchange
              </label>
              <select
                value={exchangeFilter}
                onChange={(e) => setExchangeFilter(e.target.value)}
                className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded text-white focus:outline-none focus:border-purple-500"
              >
                <option>All</option>
                {availableExchanges.map((ex) => (
                  <option key={ex} value={ex}>
                    {ex}
                  </option>
                ))}
              </select>
            </div>

            {/* Currency Filter */}
            <div>
              <label className="block text-sm text-slate-400 mb-2">
                Currency
              </label>
              <select
                value={currencyFilter}
                onChange={(e) => setCurrencyFilter(e.target.value)}
                className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded text-white focus:outline-none focus:border-purple-500"
              >
                <option>All</option>
                {availableCurrencies.map((cur) => (
                  <option key={cur} value={cur}>
                    {cur}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Results Table */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="p-12 text-center text-slate-400">Loading tickers...</div>
          ) : filteredTickers.length === 0 ? (
            <div className="p-12 text-center text-slate-400">
              {searchQuery ? 'No tickers found matching your search' : 'No tickers available'}
            </div>
          ) : (
            <table className="w-full">
              <thead className="sticky top-0 bg-slate-800/50 border-b border-slate-700">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-slate-300">
                    Ticker
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-slate-300">
                    Company
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-slate-300">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-slate-300">
                    Exchange
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-slate-300">
                    Currency
                  </th>
                  <th className="px-6 py-3 text-right text-sm font-semibold text-slate-300">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredTickers.slice(0, 100).map((ticker) => (
                  <tr
                    key={ticker.ticker}
                    className={`border-b border-slate-700 hover:bg-slate-800/50 transition ${
                      selectedRow?.ticker === ticker.ticker ? 'bg-slate-800' : ''
                    }`}
                    onClick={() => setSelectedRow(ticker)}
                  >
                    <td className="px-6 py-3 text-white font-mono font-medium">
                      {ticker.ticker}
                    </td>
                    <td className="px-6 py-3 text-slate-300">
                      {ticker.company_name || '—'}
                    </td>
                    <td className="px-6 py-3 text-slate-400 text-sm">
                      {ticker.asset_type || '—'}
                    </td>
                    <td className="px-6 py-3 text-slate-400 text-sm">
                      {ticker.exchange || '—'}
                    </td>
                    <td className="px-6 py-3 text-slate-400 text-sm">
                      {ticker.currency || '—'}
                    </td>
                    <td className="px-6 py-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onSelectTicker(ticker.ticker, ticker.company_name)
                        }}
                        className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-sm font-medium transition"
                      >
                        Buy
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-800 flex items-center justify-between">
          <div className="text-sm text-slate-400">
            Showing {filteredTickers.length} results
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
