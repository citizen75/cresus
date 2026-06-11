import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

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
  const [showCountryDropdown, setShowCountryDropdown] = useState(false)
  const [sortColumn, setSortColumn] = useState<string>('symbol')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')

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
    if (selectedCountries.length === 0 || !selectedAssetType) {
      return
    }

    try {
      setLoading(true)
      const countriesParam = selectedCountries.join(',')
      const response = await fetch(
        `http://192.168.0.130:6501/api/v1/data/filter?countries=${countriesParam}&asset_type=${selectedAssetType}`
      )
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

  const filteredTickers = tickers
    .filter(ticker =>
      searchQuery === '' ||
      ticker.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticker.name?.toLowerCase().includes(searchQuery.toLowerCase())
    )
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

  const tableColumns = getTableColumns(selectedAssetType)

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
                  className={`w-full text-left px-3 py-2 rounded transition ${
                    selectedUniverse === universe.id
                      ? 'bg-purple-600/30 text-purple-300 border border-purple-500'
                      : 'text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{universe.name}</div>
                      <div className="text-xs text-slate-500">{universe.count || 0} tickers</div>
                    </div>
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
                className="px-2 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white rounded text-xs flex items-center gap-1 transition whitespace-nowrap"
              >
                <span>
                  {selectedCountries.length === 0
                    ? '🌍 Countries'
                    : `🌍 ${selectedCountries.length}`}
                </span>
                <span className={`text-xs transition ${showCountryDropdown ? 'rotate-180' : ''}`}>▼</span>
              </button>

              {/* Dropdown Menu */}
              {showCountryDropdown && (
                <div className="absolute top-full mt-1 left-0 bg-slate-800 border border-slate-700 rounded shadow-lg z-50 max-h-48 overflow-y-auto">
                  {COUNTRIES.map(country => (
                    <button
                      key={country.code}
                      onClick={() => toggleCountry(country.code)}
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
              className="px-2 py-1.5 bg-slate-800 border border-slate-700 text-white rounded text-xs focus:outline-none focus:border-purple-500 whitespace-nowrap"
            >
              {ASSET_TYPES.map(type => (
                <option key={type.id} value={type.id}>
                  {type.icon} {type.label}
                </option>
              ))}
            </select>

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
          <div className="flex-1 overflow-y-auto overflow-x-hidden scrollbar">
            {loading ? (
              <div className="flex items-center justify-center h-full text-slate-400">
                Loading tickers...
              </div>
            ) : filteredTickers.length === 0 ? (
              <div className="flex items-center justify-center h-full text-slate-400">
                No tickers found
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-800 border-b border-slate-700">
                  <tr>
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
                    <tr key={`${ticker.symbol}-${idx}`} className="hover:bg-slate-800/50 transition">
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
            )}
          </div>

          {/* Footer */}
          {filteredTickers.length > 0 && (
            <div className="px-4 py-3 border-t border-slate-800 text-xs text-slate-500">
              Showing {filteredTickers.length} of {tickers.length} tickers
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
