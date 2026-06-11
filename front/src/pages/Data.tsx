import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import CardChart from '@/components/CardChart'

interface Universe {
  id: string
  name: string
  count?: number
}

interface Ticker {
  symbol: string
  name?: string
  sector?: string
  industry?: string
  market_cap?: string
  price?: string
  change?: string
  revenue?: string
  isin?: string
  currency?: string
}

const COUNTRIES = [
  { code: 'FR', label: 'France', flag: '🇫🇷' },
  { code: 'DE', label: 'Germany', flag: '🇩🇪' },
  { code: 'NL', label: 'Netherlands', flag: '🇳🇱' },
  { code: 'EU', label: 'Europe', flag: '🇪🇺' },
  { code: 'US', label: 'USA', flag: '🇺🇸' },
]

const ASSET_TYPES = [
  { id: 'stocks', label: 'Stocks', icon: '📈' },
  { id: 'etfs', label: 'ETFs', icon: '💱' },
  { id: 'funds', label: 'Funds', icon: '🏦' },
  { id: 'indices', label: 'Indices', icon: '📊' },
]

export default function Data() {
  const navigate = useNavigate()
  const [universes, setUniverses] = useState<Universe[]>([])
  const [selectedUniverse, setSelectedUniverse] = useState<string | null>(null)
  const [tickers, setTickers] = useState<Ticker[]>([])
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCountries, setSelectedCountries] = useState<string[]>(['FR'])
  const [selectedAssetType, setSelectedAssetType] = useState<string>('stocks')
  const [selectedExchanges, setSelectedExchanges] = useState<string[]>([])
  const [selectedCurrencies, setSelectedCurrencies] = useState<string[]>([])
  const [showCountryDropdown, setShowCountryDropdown] = useState(false)
  const [showExchangeDropdown, setShowExchangeDropdown] = useState(false)
  const [showCurrencyDropdown, setShowCurrencyDropdown] = useState(false)
  const [availableExchanges, setAvailableExchanges] = useState<string[]>([])
  const [availableCurrencies, setAvailableCurrencies] = useState<string[]>([])
  const [sortColumn, setSortColumn] = useState<string>('symbol')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set())
  const [draggedRows, setDraggedRows] = useState<string[]>([])
  const [dropTarget, setDropTarget] = useState<string | null>(null)
  const [selectedTickerDetail, setSelectedTickerDetail] = useState<Ticker | null>(null)
  const [tickerHistory, setTickerHistory] = useState<Array<{date: string, close: number}>>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  // Load universes on mount
  useEffect(() => {
    loadUniverses()
  }, [])

  // Load tickers when filters change
  useEffect(() => {
    loadFilteredTickers()
  }, [selectedCountries, selectedAssetType])

  // Load tickers for selected universe
  useEffect(() => {
    if (selectedUniverse) {
      loadUniverseTickers(selectedUniverse)
    }
  }, [selectedUniverse])

  const loadUniverses = async () => {
    try {
      setLoading(true)
      const response = await fetch(`http://192.168.0.130:6501/api/v1/data/universes/list`)
      if (response.ok) {
        const data = await response.json()
        setUniverses(data.universes || [])
      }
    } catch (err) {
      console.error('Failed to load universes:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadUniverseTickers = async (universe: string) => {
    try {
      setLoading(true)
      const response = await fetch(`http://192.168.0.130:6501/api/v1/data/universe/${universe}`)
      if (response.ok) {
        const data = await response.json()
        setTickers(data.tickers || [])
        setSearchQuery('')
      }
    } catch (err) {
      console.error('Failed to load tickers:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadFilteredTickers = async () => {
    // Don't call if no filters selected
    if (selectedCountries.length === 0 && !selectedAssetType) {
      return
    }

    try {
      setLoading(true)
      let url = 'http://192.168.0.130:6501/api/v1/data/filter?'

      // Add country filter if selected
      if (selectedCountries.length > 0) {
        const countriesParam = selectedCountries.join(',')
        url += `countries=${countriesParam}&`
      }

      // Add asset type filter
      if (selectedAssetType) {
        url += `asset_type=${selectedAssetType}`
      }

      // Remove trailing & if present
      url = url.replace(/&$/, '')

      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setTickers(data.tickers || [])
        setSelectedUniverse(null)
        setSearchQuery('')
      }
    } catch (err) {
      console.error('Failed to load filtered tickers:', err)
    } finally {
      setLoading(false)
    }
  }

  const toggleCountry = (code: string) => {
    setSelectedCountries(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    )
  }

  const toggleExchange = (exchange: string) => {
    setSelectedExchanges(prev =>
      prev.includes(exchange) ? prev.filter(e => e !== exchange) : [...prev, exchange]
    )
  }

  const toggleCurrency = (currency: string) => {
    setSelectedCurrencies(prev =>
      prev.includes(currency) ? prev.filter(c => c !== currency) : [...prev, currency]
    )
  }

  // Collect unique exchanges and currencies from tickers
  const updateAvailableFilters = () => {
    const exchanges = [...new Set(
      tickers
        .map(t => t.exchange)
        .filter((e): e is string => e !== undefined && e !== null && e !== '-')
    )].sort()
    setAvailableExchanges(exchanges)

    const currencies = [...new Set(
      tickers
        .map(t => t.currency)
        .filter((c): c is string => c !== undefined && c !== null && c !== '-')
    )].sort()
    setAvailableCurrencies(currencies)
  }

  // Update available filters when tickers change
  useEffect(() => {
    updateAvailableFilters()
  }, [tickers])

  // Handle ESC key to close dialog
  useEffect(() => {
    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && selectedTickerDetail) {
        closeTickerDetail()
      }
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [selectedTickerDetail])

  const handleSort = (columnKey: string) => {
    if (sortColumn === columnKey) {
      // Toggle direction if same column
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      // New column, default to ascending
      setSortColumn(columnKey)
      setSortDirection('asc')
    }
  }

  const toggleRowSelection = (symbol: string) => {
    setSelectedRows(prev => {
      const newSet = new Set(prev)
      if (newSet.has(symbol)) {
        newSet.delete(symbol)
      } else {
        newSet.add(symbol)
      }
      return newSet
    })
  }

  const selectAllRows = () => {
    if (selectedRows.size === filteredTickers.length) {
      setSelectedRows(new Set())
    } else {
      setSelectedRows(new Set(filteredTickers.map(t => t.symbol)))
    }
  }

  const handleRowDragStart = (symbol: string) => {
    const selected = selectedRows.has(symbol) ? Array.from(selectedRows) : [symbol]
    setDraggedRows(selected)
  }

  const handleUniverseDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'copy'
  }

  const handleUniverseDrop = async (universeId: string) => {
    if (draggedRows.length === 0) return

    try {
      // Load universe to check for existing tickers
      const universeResponse = await fetch(
        `http://192.168.0.130:6501/api/v1/data/universe/${universeId}`
      )
      const universeData = await universeResponse.json()
      const existingSymbols = new Set(
        (universeData.tickers || []).map((t: any) => t.symbol || t)
      )

      // Filter out duplicates
      const newTickers = draggedRows.filter(
        (ticker) => !existingSymbols.has(ticker)
      )
      const duplicateCount = draggedRows.length - newTickers.length

      if (newTickers.length === 0) {
        alert('All selected tickers are already in this universe')
        setDraggedRows([])
        setDropTarget(null)
        return
      }

      // Add only new tickers
      const response = await fetch(
        `http://192.168.0.130:6501/api/v1/data/universe/${universeId}/tickers`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tickers: newTickers }),
        }
      )

      if (response.ok) {
        const result = await response.json()
        if (duplicateCount > 0) {
          alert(
            `✅ Added ${result.added || newTickers.length} tickers\n⚠️ Skipped ${duplicateCount} duplicates`
          )
        } else {
          alert(`✅ Added ${result.added || newTickers.length} tickers`)
        }
        // Reload the universe
        await loadUniverses()
        setDraggedRows([])
        setDropTarget(null)
      }
    } catch (err) {
      console.error('Failed to add tickers to universe:', err)
      alert('Failed to add tickers to universe')
    }
  }

  const removeFromUniverse = async () => {
    if (!selectedUniverse || selectedRows.size === 0) return

    if (!confirm(`Remove ${selectedRows.size} ticker(s) from ${selectedUniverse}?`)) {
      return
    }

    try {
      const tickersToRemove = Array.from(selectedRows)
      const response = await fetch(
        `http://192.168.0.130:6501/api/v1/data/universe/${selectedUniverse}/tickers`,
        {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tickers: tickersToRemove }),
        }
      )

      if (response.ok) {
        const result = await response.json()
        alert(`✅ Removed ${result.removed || selectedRows.size} ticker(s)`)
        // Reload universes and clear selection
        await loadUniverses()
        setSelectedRows(new Set())
      } else {
        alert('Failed to remove tickers from universe')
      }
    } catch (err) {
      console.error('Failed to remove tickers from universe:', err)
      alert('Failed to remove tickers from universe')
    }
  }

  const openTickerDetail = async (ticker: Ticker) => {
    // Merge fundamental data from API
    const mergedTicker = { ...ticker }
    setSelectedTickerDetail(mergedTicker)
    setHistoryLoading(true)

    try {
      // Fetch 1 year of historical data and fundamentals
      const response = await fetch(
        `http://192.168.0.130:6501/api/v1/data/history/${ticker.symbol}?days=365`
      )
      if (response.ok) {
        const data = await response.json()
        setTickerHistory(data.history || [])

        // Merge fundamental data into ticker detail
        if (data.fundamentals) {
          const fundamentals = data.fundamentals
          const updatedTicker = {
            ...mergedTicker,
            market_cap: fundamentals.market_cap,
            pe_ratio: fundamentals.pe_ratio,
            eps: fundamentals.eps,
            dividend_yield: fundamentals.dividend_yield,
            high_52w: fundamentals["52_week_high"],
            low_52w: fundamentals["52_week_low"],
            avg_volume: fundamentals.avg_volume,
            beta: fundamentals.beta,
            description: fundamentals.description,
          }
          setSelectedTickerDetail(updatedTicker)
        }
      }
    } catch (err) {
      console.error('Failed to load ticker history:', err)
    } finally {
      setHistoryLoading(false)
    }
  }

  const closeTickerDetail = () => {
    setSelectedTickerDetail(null)
    setTickerHistory([])
  }

  const filteredTickers = tickers
    .filter(ticker => {
      // Search filter
      if (searchQuery !== '') {
        const query = searchQuery.toLowerCase()
        if (!((ticker.symbol && ticker.symbol.toLowerCase().includes(query)) ||
              (ticker.name && ticker.name.toLowerCase().includes(query)))) {
          return false
        }
      }
      // Exchange filter
      if (selectedExchanges.length > 0) {
        if (!ticker.exchange || !selectedExchanges.includes(ticker.exchange)) {
          return false
        }
      }
      // Currency filter
      if (selectedCurrencies.length > 0) {
        if (!ticker.currency || !selectedCurrencies.includes(ticker.currency)) {
          return false
        }
      }
      return true
    })
    .sort((a, b) => {
      const aVal = a[sortColumn as keyof Ticker]
      const bVal = b[sortColumn as keyof Ticker]

      // Handle undefined/null values
      if (aVal === undefined || aVal === null) return 1
      if (bVal === undefined || bVal === null) return -1

      // Convert to string for comparison
      const aStr = String(aVal).toLowerCase()
      const bStr = String(bVal).toLowerCase()

      // Try numeric comparison first
      const aNum = parseFloat(aStr)
      const bNum = parseFloat(bStr)
      if (!isNaN(aNum) && !isNaN(bNum)) {
        return sortDirection === 'asc' ? aNum - bNum : bNum - aNum
      }

      // Fallback to string comparison
      const comparison = aStr.localeCompare(bStr)
      return sortDirection === 'asc' ? comparison : -comparison
    })

  // Define columns per asset type
  // Detect asset type from actual data when viewing universe
  const detectAssetTypeFromData = (): string => {
    if (tickers.length === 0) return selectedAssetType

    // Check if tickers look like ETFs (usually have .PA suffix and no sector/industry)
    const likelyETFs = tickers.every(
      t => t.symbol?.includes('.') && (!t.sector || t.sector === '-') && (!t.industry || t.industry === '-')
    )

    if (likelyETFs) return 'etfs'
    return selectedAssetType
  }

  const getTableColumns = (assetType: string) => {
    switch (assetType) {
      case 'stocks':
        return [
          { key: 'symbol', label: 'Symbol' },
          { key: 'name', label: 'Name' },
          { key: 'country', label: 'Country' },
          { key: 'sector', label: 'Sector' },
          { key: 'industry', label: 'Industry' },
          { key: 'exchange', label: 'Exchange' },
          { key: 'price', label: 'Price', align: 'right' },
        ]
      case 'etfs':
        return [
          { key: 'symbol', label: 'Symbol' },
          { key: 'name', label: 'Name' },
          { key: 'country', label: 'Country' },
          { key: 'currency', label: 'Currency' },
          { key: 'exchange', label: 'Exchange' },
          { key: 'price', label: 'Price', align: 'right' },
        ]
      case 'funds':
        return [
          { key: 'symbol', label: 'Symbol' },
          { key: 'name', label: 'Name' },
          { key: 'country', label: 'Country' },
          { key: 'currency', label: 'Currency' },
          { key: 'price', label: 'Price', align: 'right' },
        ]
      case 'indices':
        return [
          { key: 'symbol', label: 'Symbol' },
          { key: 'name', label: 'Name' },
          { key: 'country', label: 'Country' },
          { key: 'exchange', label: 'Exchange' },
          { key: 'currency', label: 'Currency' },
          { key: 'price', label: 'Price', align: 'right' },
        ]
      default:
        return []
    }
  }

  // Use detected asset type when viewing universe, otherwise use selected filter
  const displayAssetType = selectedUniverse ? detectAssetTypeFromData() : selectedAssetType
  const tableColumns = getTableColumns(displayAssetType)

  return (
    <div className="flex-1 bg-slate-950 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Financial Database</h1>
          <p className="text-sm text-slate-400 mt-1">Browse universes and filtered tickers</p>
        </div>
        <button
          onClick={() => navigate('/data/universes')}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition"
        >
          📦 Manage Universes
        </button>
      </div>

      {/* Main content */}
      <div className="flex-1 flex gap-4 p-6 overflow-hidden">
        {/* Left Panel - Universes List */}
        <div className="w-80 flex flex-col border border-slate-800 rounded-lg bg-slate-900">
          <div className="px-4 py-3 border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Universes ({universes.length})
          </div>
          <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
            {loading && universes.length === 0 ? (
              <div className="text-center text-slate-500 py-8">Loading universes...</div>
            ) : universes.length === 0 ? (
              <div className="text-center text-slate-500 py-8">No universes available</div>
            ) : (
              universes.map(universe => (
                <button
                  key={universe.id}
                  onClick={() => setSelectedUniverse(universe.id)}
                  onDragOver={(e) => {
                    if (draggedRows.length > 0) {
                      handleUniverseDragOver(e)
                      setDropTarget(universe.id)
                    }
                  }}
                  onDragLeave={() => setDropTarget(null)}
                  onDrop={(e) => {
                    e.preventDefault()
                    handleUniverseDrop(universe.id)
                  }}
                  className={`w-full text-left px-3 py-2 rounded transition ${
                    selectedUniverse === universe.id
                      ? 'bg-purple-600/30 text-purple-300 border border-purple-500'
                      : dropTarget === universe.id
                      ? 'bg-green-600/30 text-green-300 border border-green-500'
                      : 'text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{universe.name}</div>
                      <div className="text-xs text-slate-500">{universe.count || 0} tickers</div>
                    </div>
                    {draggedRows.length > 0 && (
                      <div className="text-xs bg-green-600 px-2 py-1 rounded">
                        +{draggedRows.length}
                      </div>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right Panel */}
        <div className="flex-1 flex flex-col border border-slate-800 rounded-lg bg-slate-900 min-h-0">
          {/* Filters Header - All Inline */}
          <div className="px-3 py-2 border-b border-slate-800 flex gap-2 items-center justify-between">
            <div className="flex gap-2 items-center flex-1">
            {/* Country Filter */}
            <div className="relative">
              <button
                onClick={() => setShowCountryDropdown(!showCountryDropdown)}
                className="px-3 py-1.5 bg-blue-900/30 hover:bg-blue-800/40 border border-blue-700/50 text-blue-300 rounded text-xs font-medium flex items-center gap-2 transition whitespace-nowrap"
                title="Filter by country"
              >
                <span>🌍</span>
                <span>Country</span>
                {selectedCountries.length > 0 && <span className="bg-blue-600 text-white px-1.5 rounded text-xs">{selectedCountries.length}</span>}
                <span className={`text-xs transition ${showCountryDropdown ? 'rotate-180' : ''}`}>▼</span>
              </button>

              {/* Dropdown Menu */}
              {showCountryDropdown && (
                <div className="absolute top-full mt-1 left-0 bg-slate-800 border border-slate-700 rounded shadow-lg z-50 max-h-48 overflow-y-auto">
                  {COUNTRIES.map(country => (
                    <button
                      key={country.code}
                      onClick={() => {
                        toggleCountry(country.code)
                        setShowCountryDropdown(false)
                      }}
                      className={`w-full text-left px-2 py-1.5 text-xs transition flex items-center gap-1 ${
                        selectedCountries.includes(country.code)
                          ? 'bg-purple-600/30 text-purple-300'
                          : 'text-slate-300 hover:bg-slate-700'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedCountries.includes(country.code)}
                        onChange={() => {}}
                        className="w-3 h-3"
                      />
                      <span>{country.flag}</span>
                      <span className="text-xs">{country.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Asset Type Filter */}
            <select
              value={selectedAssetType}
              onChange={(e) => setSelectedAssetType(e.target.value)}
              className="px-3 py-1.5 bg-green-900/30 hover:bg-green-800/40 border border-green-700/50 text-green-300 rounded text-xs font-medium focus:outline-none focus:border-green-600 whitespace-nowrap"
              title="Filter by asset type"
            >
              {ASSET_TYPES.map(type => (
                <option key={type.id} value={type.id}>
                  {type.icon} {type.label}
                </option>
              ))}
            </select>

            {/* Exchange Filter */}
            <div className="relative">
                <button
                  onClick={() => setShowExchangeDropdown(!showExchangeDropdown)}
                  className="px-3 py-1.5 bg-amber-900/30 hover:bg-amber-800/40 border border-amber-700/50 text-amber-300 rounded text-xs font-medium flex items-center gap-2 transition whitespace-nowrap"
                  title="Filter by exchange"
                >
                  <span>🏢</span>
                  <span>Exchange</span>
                  {selectedExchanges.length > 0 && <span className="bg-amber-600 text-white px-1.5 rounded text-xs">{selectedExchanges.length}</span>}
                  <span className={`text-xs transition ${showExchangeDropdown ? 'rotate-180' : ''}`}>▼</span>
                </button>

                {/* Dropdown Menu */}
                {showExchangeDropdown && (
                  <div className="absolute top-full mt-1 left-0 bg-slate-800 border border-slate-700 rounded shadow-lg z-50 max-h-48 overflow-y-auto min-w-48">
                    {availableExchanges.length === 0 ? (
                      <div className="px-2 py-2 text-xs text-slate-400">
                        Load tickers to see exchanges
                      </div>
                    ) : (
                      availableExchanges.map(exchange => (
                        <button
                          key={exchange}
                          onClick={() => {
                            toggleExchange(exchange)
                            setShowExchangeDropdown(false)
                          }}
                          className={`w-full text-left px-2 py-1.5 text-xs transition flex items-center gap-1 ${
                            selectedExchanges.includes(exchange)
                              ? 'bg-purple-600/30 text-purple-300'
                              : 'text-slate-300 hover:bg-slate-700'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selectedExchanges.includes(exchange)}
                            onChange={() => {}}
                            className="w-3 h-3"
                          />
                          <span className="text-xs">{exchange}</span>
                        </button>
                      ))
                    )}
                  </div>
                )}
            </div>

            {/* Currency Filter */}
            <div className="relative">
                <button
                  onClick={() => setShowCurrencyDropdown(!showCurrencyDropdown)}
                  className="px-3 py-1.5 bg-orange-900/30 hover:bg-orange-800/40 border border-orange-700/50 text-orange-300 rounded text-xs font-medium flex items-center gap-2 transition whitespace-nowrap"
                  title="Filter by currency"
                >
                  <span>💱</span>
                  <span>Currency</span>
                  {selectedCurrencies.length > 0 && <span className="bg-orange-600 text-white px-1.5 rounded text-xs">{selectedCurrencies.length}</span>}
                  <span className={`text-xs transition ${showCurrencyDropdown ? 'rotate-180' : ''}`}>▼</span>
                </button>

                {/* Dropdown Menu */}
                {showCurrencyDropdown && (
                  <div className="absolute top-full mt-1 left-0 bg-slate-800 border border-slate-700 rounded shadow-lg z-50 max-h-48 overflow-y-auto min-w-48">
                    {availableCurrencies.length === 0 ? (
                      <div className="px-2 py-2 text-xs text-slate-400">
                        Load tickers to see currencies
                      </div>
                    ) : (
                      availableCurrencies.map(currency => (
                        <button
                          key={currency}
                          onClick={() => {
                            toggleCurrency(currency)
                            setShowCurrencyDropdown(false)
                          }}
                          className={`w-full text-left px-2 py-1.5 text-xs transition flex items-center gap-1 ${
                            selectedCurrencies.includes(currency)
                              ? 'bg-purple-600/30 text-purple-300'
                              : 'text-slate-300 hover:bg-slate-700'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selectedCurrencies.includes(currency)}
                            onChange={() => {}}
                            className="w-3 h-3"
                          />
                          <span className="text-xs">{currency}</span>
                        </button>
                      ))
                    )}
                  </div>
                )}
            </div>

            {/* Search Bar */}
            <input
              type="text"
              placeholder="🔍 Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1 px-2 py-1.5 bg-slate-800 border border-slate-700 text-white rounded text-xs focus:outline-none focus:border-purple-500"
            />
            </div>

            {/* Count Display */}
            <div className="text-xs text-slate-400 whitespace-nowrap pl-2 border-l border-slate-700">
              {filteredTickers.length} / {tickers.length}
            </div>
          </div>

          {/* Table */}
          <div className="flex-1 overflow-hidden flex flex-col">
            {loading ? (
              <div className="flex items-center justify-center h-full text-slate-400">
                Loading tickers...
              </div>
            ) : filteredTickers.length === 0 ? (
              <div className="flex items-center justify-center h-full text-slate-400">
                No tickers found
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto overflow-x-hidden scrollbar">
                <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-800 border-b border-slate-700">
                  <tr>
                    <th className="px-4 py-3 text-slate-300 font-semibold text-left w-10">
                      <input
                        type="checkbox"
                        checked={selectedRows.size > 0 && selectedRows.size === filteredTickers.length}
                        onChange={selectAllRows}
                        className="w-4 h-4 cursor-pointer"
                      />
                    </th>
                    {tableColumns.map(col => (
                      <th
                        key={col.key}
                        onClick={() => handleSort(col.key)}
                        className={`px-4 py-3 text-slate-300 font-semibold cursor-pointer hover:bg-slate-700/50 transition ${
                          col.align === 'right' ? 'text-right' : 'text-left'
                        } ${sortColumn === col.key ? 'bg-slate-700 text-purple-300' : ''}`}
                      >
                        <div className="flex items-center gap-1">
                          <span>{col.label}</span>
                          {sortColumn === col.key && (
                            <span className="text-xs">
                              {sortDirection === 'asc' ? '↑' : '↓'}
                            </span>
                          )}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {filteredTickers.map((ticker, idx) => (
                    <tr
                      key={`${ticker.symbol}-${idx}`}
                      draggable={selectedRows.has(ticker.symbol) || selectedRows.size === 0}
                      onDragStart={() => handleRowDragStart(ticker.symbol)}
                      onClick={() => {
                        // Only open dialog if no rows selected (not in drag-drop mode)
                        if (selectedRows.size === 0) {
                          openTickerDetail(ticker)
                        }
                      }}
                      className={`transition ${
                        selectedRows.has(ticker.symbol)
                          ? 'bg-purple-600/30 text-purple-200'
                          : selectedRows.size === 0
                          ? 'hover:bg-slate-800/50 cursor-pointer'
                          : 'hover:bg-slate-800/50'
                      } ${selectedRows.size > 0 ? 'cursor-move' : ''}`}
                    >
                      <td className="px-4 py-3 w-10" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selectedRows.has(ticker.symbol)}
                          onChange={() => toggleRowSelection(ticker.symbol)}
                          className="w-4 h-4 cursor-pointer"
                        />
                      </td>
                      {tableColumns.map(col => (
                        <td
                          key={col.key}
                          className={`px-4 py-3 text-slate-400 ${
                            col.key === 'symbol' ? 'font-medium text-purple-300' : ''
                          } ${col.align === 'right' ? 'text-right' : ''}`}
                        >
                          {ticker[col.key as keyof Ticker] || '-'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Footer */}
          {filteredTickers.length > 0 && (
            <div className="px-4 py-3 border-t border-slate-800 flex items-center justify-between">
              <div className="text-xs text-slate-500">
                Showing {filteredTickers.length} of {tickers.length} tickers
                {selectedRows.size > 0 && (
                  <span className="ml-4 text-purple-400">
                    ({selectedRows.size} selected)
                  </span>
                )}
              </div>
              {selectedRows.size > 0 && selectedUniverse && (
                <button
                  onClick={removeFromUniverse}
                  className="px-3 py-1 bg-red-600/20 text-red-300 rounded text-xs hover:bg-red-600/30 transition font-medium"
                >
                  🗑️ Remove {selectedRows.size} from {selectedUniverse}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Ticker Detail Modal */}
      {selectedTickerDetail && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">{selectedTickerDetail.symbol}</h2>
                <p className="text-sm text-slate-400">{selectedTickerDetail.name}</p>
              </div>
              <button
                onClick={closeTickerDetail}
                className="text-slate-400 hover:text-white text-2xl transition"
              >
                ✕
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden flex">
              {/* Left: Fundamental Data */}
              <div className="w-96 border-r border-slate-800 overflow-y-auto p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Fundamentals</h3>
                <div className="grid grid-cols-2 gap-4">
                  {/* Price - Full Width */}
                  {selectedTickerDetail.price && (
                    <div className="col-span-2 pb-3 border-b border-slate-700">
                      <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Price</p>
                      <p className="text-2xl font-bold text-green-400">${selectedTickerDetail.price}</p>
                    </div>
                  )}

                  {/* 2-Column Grid Items */}
                  {selectedTickerDetail.exchange && (
                    <div>
                      <p className="text-xs text-slate-400">Exchange</p>
                      <p className="text-sm font-medium text-slate-300">{selectedTickerDetail.exchange}</p>
                    </div>
                  )}
                  {selectedTickerDetail.country && (
                    <div>
                      <p className="text-xs text-slate-400">Country</p>
                      <p className="text-sm font-medium text-slate-300">{selectedTickerDetail.country}</p>
                    </div>
                  )}
                  {selectedTickerDetail.currency && (
                    <div>
                      <p className="text-xs text-slate-400">Currency</p>
                      <p className="text-sm font-medium text-slate-300">{selectedTickerDetail.currency}</p>
                    </div>
                  )}
                  {selectedTickerDetail.sector && (
                    <div>
                      <p className="text-xs text-slate-400">Sector</p>
                      <p className="text-sm font-medium text-blue-300">{selectedTickerDetail.sector}</p>
                    </div>
                  )}
                  {selectedTickerDetail.industry && (
                    <div>
                      <p className="text-xs text-slate-400">Industry</p>
                      <p className="text-sm font-medium text-blue-300">{selectedTickerDetail.industry}</p>
                    </div>
                  )}
                  {selectedTickerDetail.market_cap && (
                    <div>
                      <p className="text-xs text-slate-400">Market Cap</p>
                      <p className="text-sm font-medium text-slate-300">
                        {typeof selectedTickerDetail.market_cap === 'number'
                          ? `$${(selectedTickerDetail.market_cap / 1e9).toFixed(2)}B`
                          : selectedTickerDetail.market_cap}
                      </p>
                    </div>
                  )}
                  {selectedTickerDetail.pe_ratio && (
                    <div>
                      <p className="text-xs text-slate-400">P/E Ratio</p>
                      <p className="text-sm font-medium text-slate-300">{selectedTickerDetail.pe_ratio.toFixed(2)}</p>
                    </div>
                  )}
                  {selectedTickerDetail.eps && (
                    <div>
                      <p className="text-xs text-slate-400">EPS (TTM)</p>
                      <p className="text-sm font-medium text-slate-300">${selectedTickerDetail.eps.toFixed(2)}</p>
                    </div>
                  )}
                  {selectedTickerDetail.dividend_yield && (
                    <div>
                      <p className="text-xs text-slate-400">Dividend Yield</p>
                      <p className="text-sm font-medium text-green-400">{(selectedTickerDetail.dividend_yield * 100).toFixed(2)}%</p>
                    </div>
                  )}
                  {selectedTickerDetail.high_52w && (
                    <div>
                      <p className="text-xs text-slate-400">52W High</p>
                      <p className="text-sm font-medium text-slate-300">${selectedTickerDetail.high_52w.toFixed(2)}</p>
                    </div>
                  )}
                  {selectedTickerDetail.low_52w && (
                    <div>
                      <p className="text-xs text-slate-400">52W Low</p>
                      <p className="text-sm font-medium text-slate-300">${selectedTickerDetail.low_52w.toFixed(2)}</p>
                    </div>
                  )}
                  {selectedTickerDetail.beta && (
                    <div>
                      <p className="text-xs text-slate-400">Beta</p>
                      <p className="text-sm font-medium text-slate-300">{selectedTickerDetail.beta.toFixed(2)}</p>
                    </div>
                  )}
                  {selectedTickerDetail.recommendation && (
                    <div>
                      <p className="text-xs text-slate-400">Analyst Rating</p>
                      <p className="text-sm font-medium text-yellow-400">{selectedTickerDetail.recommendation}</p>
                    </div>
                  )}
                  {selectedTickerDetail.target_price && (
                    <div>
                      <p className="text-xs text-slate-400">Target Price</p>
                      <p className="text-sm font-medium text-slate-300">${selectedTickerDetail.target_price}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Right: Price History Chart */}
              <div className="flex-1 p-6 overflow-y-auto">
                <h3 className="text-lg font-semibold text-white mb-4">1-Year Price History</h3>
                {historyLoading ? (
                  <div className="flex items-center justify-center h-80 text-slate-400">
                    Loading chart data...
                  </div>
                ) : tickerHistory.length > 0 ? (
                  <CardChart data={tickerHistory} ticker={selectedTickerDetail.symbol} />
                ) : (
                  <div className="flex items-center justify-center h-80 text-slate-400">
                    No historical data available
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
