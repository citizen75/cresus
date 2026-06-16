import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { api } from '@/services/api'

interface TickerSearchDialogProps {
  isOpen: boolean
  onClose: () => void
  onSelectTicker: (ticker: string, company?: string) => void
  portfolioName?: string
}

interface TickerData {
  ticker?: string
  symbol?: string
  company_name?: string
  name?: string
  asset_type?: string
  type?: string
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
  console.log('[TickerSearchDialog] Rendering with isOpen:', isOpen)
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
      console.log('[TickerSearchDialog] Loading tickers...')
      if (!api.getAllTickers) {
        console.error('[TickerSearchDialog] getAllTickers method not found on API')
        setIsLoading(false)
        return
      }

      const response = await api.getAllTickers()
      console.log('[TickerSearchDialog] Response:', response)

      if (response) {
        // Handle both array and object responses
        const tickersList = Array.isArray(response) ? response : response.tickers || []
        console.log('[TickerSearchDialog] Setting tickers:', tickersList.length)
        setTickers(tickersList)

        // Extract unique exchanges and currencies (handle both field name formats)
        const exchanges = Array.from(new Set(tickersList.map((t: TickerData) => t.exchange || '').filter(Boolean))) as string[]
        const currencies = Array.from(new Set(tickersList.map((t: TickerData) => t.currency || '').filter(Boolean))) as string[]

        console.log('[TickerSearchDialog] Exchanges:', exchanges)
        console.log('[TickerSearchDialog] Currencies:', currencies)
        setAvailableExchanges(exchanges)
        setAvailableCurrencies(currencies)
      }
    } catch (err) {
      console.error('[TickerSearchDialog] Error loading tickers:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const filteredTickers = tickers.filter((ticker) => {
    // Handle different field names from API
    const tickerSymbol = ticker.ticker || ticker.symbol || ''
    const companyName = ticker.company_name || ticker.name || ''
    const assetType = ticker.asset_type || ticker.type || ''
    const exchange = ticker.exchange || ''
    const currency = ticker.currency || ''

    const query = searchQuery.toLowerCase()
    const matchesSearch =
      tickerSymbol.toLowerCase().includes(query) ||
      (companyName && companyName.toLowerCase().includes(query))

    const matchesAssetType =
      assetTypeFilter === 'All' || assetType === assetTypeFilter

    const matchesExchange =
      exchangeFilter === 'All' || exchange === exchangeFilter

    const matchesCurrency =
      currencyFilter === 'All' || currency === currencyFilter

    return matchesSearch && matchesAssetType && matchesExchange && matchesCurrency
  })

  if (!isOpen) {
    console.log('[TickerSearchDialog] Not open, returning null')
    return null
  }

  console.log('[TickerSearchDialog] Dialog is OPEN - rendering content')

  const dialogContent = (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ backgroundColor: 'transparent' }}>
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" style={{ zIndex: 1 }} />

      {/* Dialog */}
      <div className="relative bg-slate-900 border-4 border-yellow-500 rounded-lg w-[90vw] max-w-4xl max-h-[85vh] flex flex-col shadow-2xl" style={{ zIndex: 2 }}>
        {/* DEBUG INDICATOR */}
        <div style={{ position: 'absolute', top: '10px', left: '10px', background: 'yellow', color: 'black', padding: '5px 10px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold', zIndex: 10 }}>
          DIALOG VISIBLE
        </div>
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
              onChange={(e) => {
                console.log('[TickerSearchDialog] Search query changed:', e.target.value)
                setSearchQuery(e.target.value)
              }}
              placeholder="e.g., AAPL or Apple"
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
            />
            <div className="text-xs text-slate-500 mt-1">
              Search: "{searchQuery}" | Total tickers: {tickers.length} | Filtered: {filteredTickers.length}
            </div>
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
            <div className="p-12 text-center text-slate-400">
              <div>Loading tickers...</div>
              <div className="text-sm mt-2">Please wait, this may take a moment</div>
            </div>
          ) : tickers.length === 0 && !isLoading ? (
            <div className="p-12 text-center text-slate-400">
              <div>No tickers could be loaded</div>
              <div className="text-sm mt-2">Try entering a ticker manually or check your connection</div>
            </div>
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
                {filteredTickers.slice(0, 100).map((ticker) => {
                  const tickerSymbol = ticker.ticker || ticker.symbol || ''
                  const companyName = ticker.company_name || ticker.name || ''

                  return (
                    <tr
                      key={tickerSymbol}
                      className={`border-b border-slate-700 hover:bg-slate-800/50 transition ${
                        selectedRow?.ticker === tickerSymbol ? 'bg-slate-800' : ''
                      }`}
                      onClick={() => setSelectedRow(ticker)}
                    >
                      <td className="px-6 py-3 text-white font-mono font-medium">
                        {tickerSymbol}
                      </td>
                      <td className="px-6 py-3 text-slate-300">
                        {companyName || '—'}
                      </td>
                      <td className="px-6 py-3 text-slate-400 text-sm">
                        {ticker.asset_type || ticker.type || '—'}
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
                            onSelectTicker(tickerSymbol, companyName)
                          }}
                          className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-sm font-medium transition"
                        >
                          Buy
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
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

          {/* Manual Ticker Entry */}
          {tickers.length === 0 && (
            <div className="border-t border-slate-700 pt-4">
              <label className="block text-sm text-slate-400 mb-2">
                Or enter ticker manually
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="e.g., AAPL"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && (e.currentTarget.value.trim())) {
                      onSelectTicker(e.currentTarget.value.toUpperCase(), undefined)
                    }
                  }}
                  className="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                />
                <button
                  onClick={() => {
                    const ticker = (document.querySelector('[placeholder="e.g., AAPL"]') as HTMLInputElement)?.value.trim()
                    if (ticker) {
                      onSelectTicker(ticker.toUpperCase(), undefined)
                    }
                  }}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded font-medium transition"
                >
                  Buy
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )

  return createPortal(dialogContent, document.body)
}
