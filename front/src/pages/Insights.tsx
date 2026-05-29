import { usePortfolios, useCurrentPrices } from '@/hooks/usePortfolio'
import { useState, useCallback, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatCurrency } from '@/utils/currency'
import { api } from '@/services/api'

interface PortfolioPositions {
  portfolio: string
  currency: string
  positions: any[]
}

function PortfolioPositionsFetcher({ portfolio, onData }: { portfolio: any; onData: (data: PortfolioPositions) => void }) {
  const { data: priceData } = useCurrentPrices(portfolio.name)

  useEffect(() => {
    if (priceData?.positions) {
      onData({
        portfolio: portfolio.name,
        currency: portfolio.currency || 'USD',
        positions: priceData.positions,
      })
    }
  }, [priceData, portfolio.name, portfolio.currency, onData])

  return null
}

export default function Insights() {
  const navigate = useNavigate()
  const { data, isLoading: portfoliosLoading } = usePortfolios()
  const portfolios = data?.portfolios || []
  const [portfolioPositionsMap, setPortfolioPositionsMap] = useState<Record<string, PortfolioPositions>>({})

  const handlePortfolioData = useCallback((data: PortfolioPositions) => {
    setPortfolioPositionsMap((prev) => ({
      ...prev,
      [data.portfolio]: data,
    }))
  }, [])

  const [fundamentalData, setFundamentalData] = useState<Record<string, any>>({})

  // Fetch fundamental data for all unique tickers (in parallel with timeout)
  useEffect(() => {
    const uniqueTickers = new Set<string>()
    Object.values(portfolioPositionsMap).forEach((ppData: PortfolioPositions) => {
      ppData.positions.forEach((pos: any) => {
        uniqueTickers.add(pos.ticker)
      })
    })

    const fetchFundamentals = async () => {
      const newFundamentalData: Record<string, any> = {}
      const tickers = Array.from(uniqueTickers)

      // Fetch all tickers in parallel with timeout
      const promises = tickers.map(async (ticker) => {
        try {
          // Add 5 second timeout per ticker
          const controller = new AbortController()
          const timeoutId = setTimeout(() => controller.abort(), 5000)

          const data = await Promise.race([
            api.getFundamental(ticker),
            new Promise((_, reject) =>
              setTimeout(() => reject(new Error('Timeout')), 5000)
            )
          ])

          clearTimeout(timeoutId)
          const quotation = (data as any)?.data?.quotation || (data as any)?.quotation || data || {}
          return { ticker, quotation }
        } catch (error) {
          console.error(`Failed to fetch fundamental data for ${ticker}:`, error)
          return { ticker, quotation: {} }
        }
      })

      const results = await Promise.all(promises)
      results.forEach(({ ticker, quotation }) => {
        newFundamentalData[ticker] = quotation
      })

      setFundamentalData(newFundamentalData)
    }

    if (uniqueTickers.size > 0) {
      fetchFundamentals()
    }
  }, [portfolioPositionsMap])

  const [sortColumn, setSortColumn] = useState<string>('daily_change_pct')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [sectorFilter, setSectorFilter] = useState<string>('All sectors')
  const [performanceFilter, setPerformanceFilter] = useState<'all' | 'gainers' | 'losers'>('all')

  // Aggregate all holdings from all portfolios
  const allPositions = useMemo(() => {
    const positions: any[] = []
    Object.values(portfolioPositionsMap).forEach((ppData: PortfolioPositions) => {
      ppData.positions.forEach((holding: any) => {
        const fundamental = fundamentalData[holding.ticker] || {}
        positions.push({
          ticker: holding.ticker,
          company_name: holding.company_name || holding.ticker,
          sector: holding.sector || 'Unknown',
          asset_type: holding.asset_type || 'Stock',
          current_price: holding.current_price || 0,
          previous_close: fundamental.previous_close || holding.current_price || 0,
          quantity: holding.quantity || 0,
          portfolio: ppData.portfolio,
          currency: ppData.currency,
          avg_entry_price: holding.avg_entry_price || 0,
          position_value: holding.position_value || 0,
          position_gain: holding.position_gain || 0,
          position_gain_pct: holding.position_gain_pct || 0,
          volume: fundamental.volume || 0,
          market_cap: fundamental.market_cap || 0,
          pe_ratio: fundamental.pe_ratio || 0,
        })
      })
    })
    return positions
  }, [portfolioPositionsMap, fundamentalData])

  // Calculate daily changes for each position
  const positionsWithDailyChange = useMemo(() => {
    return allPositions.map((pos: any) => {
      const dailyChange = pos.current_price - pos.previous_close
      const dailyChangePct = pos.previous_close > 0 ? (dailyChange / pos.previous_close) * 100 : 0
      return {
        ...pos,
        daily_change: dailyChange,
        daily_change_pct: dailyChangePct,
      }
    })
  }, [allPositions])

  // Apply filters
  const filteredPositions = useMemo(() => {
    let filtered = positionsWithDailyChange

    // Search filter
    if (searchQuery) {
      filtered = filtered.filter((pos: any) =>
        pos.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
        pos.company_name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    // Sector filter
    if (sectorFilter !== 'All sectors') {
      filtered = filtered.filter((pos: any) => pos.sector === sectorFilter)
    }

    // Performance filter
    if (performanceFilter === 'gainers') {
      filtered = filtered.filter((pos: any) => pos.daily_change_pct > 0)
    } else if (performanceFilter === 'losers') {
      filtered = filtered.filter((pos: any) => pos.daily_change_pct < 0)
    }

    return filtered
  }, [positionsWithDailyChange, searchQuery, sectorFilter, performanceFilter])

  // Sort positions
  const sortedPositions = useMemo(() => {
    const sorted = [...filteredPositions]
    sorted.sort((a: any, b: any) => {
      let aVal, bVal

      switch (sortColumn) {
        case 'ticker':
          aVal = a.ticker.toLowerCase()
          bVal = b.ticker.toLowerCase()
          break
        case 'company':
          aVal = a.company_name.toLowerCase()
          bVal = b.company_name.toLowerCase()
          break
        case 'sector':
          aVal = a.sector.toLowerCase()
          bVal = b.sector.toLowerCase()
          break
        case 'current_price':
          aVal = a.current_price
          bVal = b.current_price
          break
        case 'daily_change':
          aVal = a.daily_change
          bVal = b.daily_change
          break
        case 'daily_change_pct':
          aVal = a.daily_change_pct
          bVal = b.daily_change_pct
          break
        case 'quantity':
          aVal = a.quantity
          bVal = b.quantity
          break
        case 'position_value':
          aVal = a.position_value
          bVal = b.position_value
          break
        case 'position_gain_pct':
          aVal = a.position_gain_pct
          bVal = b.position_gain_pct
          break
        default:
          return 0
      }

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDirection === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }

      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : aVal < bVal ? -1 : 0
      } else {
        return bVal > aVal ? 1 : bVal < aVal ? -1 : 0
      }
    })

    return sorted
  }, [filteredPositions, sortColumn, sortDirection])

  const handleColumnSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('desc')
    }
  }

  const getSortIndicator = (column: string) => {
    if (sortColumn !== column) return ''
    return sortDirection === 'asc' ? ' ↑' : ' ↓'
  }

  // Get unique sectors for filter
  const sectors = useMemo(() => {
    const sectorSet = new Set(allPositions.map((p: any) => p.sector))
    return Array.from(sectorSet).sort()
  }, [allPositions])

  // Calculate summary stats
  const summaryStats = useMemo(() => {
    const gainers = positionsWithDailyChange.filter((p: any) => p.daily_change_pct > 0)
    const losers = positionsWithDailyChange.filter((p: any) => p.daily_change_pct < 0)
    const totalDailyChange = positionsWithDailyChange.reduce((sum: number, p: any) => sum + p.daily_change, 0)
    const avgDailyChangePct = positionsWithDailyChange.length > 0
      ? positionsWithDailyChange.reduce((sum: number, p: any) => sum + p.daily_change_pct, 0) / positionsWithDailyChange.length
      : 0

    return {
      totalPositions: allPositions.length,
      gainers: gainers.length,
      losers: losers.length,
      totalDailyChange,
      avgDailyChangePct,
    }
  }, [positionsWithDailyChange, allPositions])

  const uniqueTickerCount = useMemo(() => {
    const tickers = new Set<string>()
    allPositions.forEach((pos: any) => tickers.add(pos.ticker))
    return tickers.size
  }, [allPositions])

  const fundamentalDataLoaded = uniqueTickerCount > 0 && Object.keys(fundamentalData).length >= uniqueTickerCount

  const isLoading = portfoliosLoading || Object.keys(portfolioPositionsMap).length === 0

  return (
    <>
      {/* Fetch positions for each portfolio */}
      {portfolios.map((portfolio: any) => (
        <PortfolioPositionsFetcher
          key={portfolio.name}
          portfolio={portfolio}
          onData={handlePortfolioData}
        />
      ))}

      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">Insights</h1>
          <p className="text-slate-400">Daily market movement across all positions</p>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-5 gap-4">
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
            <p className="text-slate-400 text-xs uppercase mb-2">Total Positions</p>
            <p className="text-white font-bold text-2xl">{summaryStats.totalPositions}</p>
          </div>

          <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
            <p className="text-slate-400 text-xs uppercase mb-2">Gainers</p>
            <p className="text-green-400 font-bold text-2xl">{summaryStats.gainers}</p>
            <p className="text-green-400 text-sm mt-1">
              {summaryStats.totalPositions > 0
                ? ((summaryStats.gainers / summaryStats.totalPositions) * 100).toFixed(1)
                : 0}%
            </p>
          </div>

          <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
            <p className="text-slate-400 text-xs uppercase mb-2">Losers</p>
            <p className="text-red-400 font-bold text-2xl">{summaryStats.losers}</p>
            <p className="text-red-400 text-sm mt-1">
              {summaryStats.totalPositions > 0
                ? ((summaryStats.losers / summaryStats.totalPositions) * 100).toFixed(1)
                : 0}%
            </p>
          </div>

          <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
            <p className="text-slate-400 text-xs uppercase mb-2">Total Daily Change</p>
            <p className={`font-bold text-2xl ${summaryStats.totalDailyChange >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {summaryStats.totalDailyChange >= 0 ? '+' : ''}{summaryStats.totalDailyChange.toFixed(2)}
            </p>
          </div>

          <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
            <p className="text-slate-400 text-xs uppercase mb-2">Avg Daily Change %</p>
            <p className={`font-bold text-2xl ${summaryStats.avgDailyChangePct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {summaryStats.avgDailyChangePct >= 0 ? '+' : ''}{summaryStats.avgDailyChangePct.toFixed(2)}%
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-3 items-center justify-between">
          <div className="flex gap-3 flex-1">
            {/* Search */}
            <div className="flex-1 relative max-w-md">
              <input
                type="text"
                placeholder="Search ticker or company..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg focus:outline-none focus:border-purple-600"
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500">🔍</span>
            </div>

            {/* Performance Filter */}
            <select
              value={performanceFilter}
              onChange={(e) => setPerformanceFilter(e.target.value as any)}
              className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition"
            >
              <option value="all">All Positions</option>
              <option value="gainers">Gainers Only</option>
              <option value="losers">Losers Only</option>
            </select>

            {/* Sector Filter */}
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:border-slate-600 transition"
            >
              <option>All sectors</option>
              {sectors.map((sector: string) => (
                <option key={sector} value={sector}>
                  {sector}
                </option>
              ))}
            </select>
          </div>

          <div className="text-sm text-slate-400">
            Showing {sortedPositions.length} of {allPositions.length} positions
          </div>
        </div>

        {/* Table */}
        <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden flex flex-col">
          {isLoading ? (
            <div className="p-12 text-center text-slate-400">
              Loading positions across portfolios...
            </div>
          ) : !fundamentalDataLoaded && allPositions.length > 0 ? (
            <div className="p-12 text-center text-slate-400">
              Fetching daily price data... ({Object.keys(fundamentalData).length}/{uniqueTickerCount} tickers loaded)
            </div>
          ) : allPositions.length === 0 ? (
            <div className="p-12 text-center text-slate-400">
              No positions across portfolios yet
            </div>
          ) : (
            <>
              <div className="overflow-x-auto overflow-y-auto max-h-[800px]">
                <table className="w-full text-sm">
                  <thead className="bg-slate-800/50 border-b border-slate-800 sticky top-0">
                    <tr>
                      <th
                        className="px-4 py-3 text-left text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                        onClick={() => handleColumnSort('ticker')}
                      >
                        Ticker{getSortIndicator('ticker')}
                      </th>
                      <th
                        className="px-4 py-3 text-left text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                        onClick={() => handleColumnSort('company')}
                      >
                        Company{getSortIndicator('company')}
                      </th>
                      <th
                        className="px-4 py-3 text-left text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                        onClick={() => handleColumnSort('sector')}
                      >
                        Sector{getSortIndicator('sector')}
                      </th>
                      <th
                        className="px-4 py-3 text-left text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                        onClick={() => handleColumnSort('current_price')}
                      >
                        Price{getSortIndicator('current_price')}
                      </th>
                      <th
                        className="px-4 py-3 text-left text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                        onClick={() => handleColumnSort('daily_change')}
                      >
                        Daily Change{getSortIndicator('daily_change')}
                      </th>
                      <th
                        className="px-4 py-3 text-left text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                        onClick={() => handleColumnSort('daily_change_pct')}
                      >
                        Daily %{getSortIndicator('daily_change_pct')}
                      </th>
                      <th
                        className="px-4 py-3 text-left text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                        onClick={() => handleColumnSort('quantity')}
                      >
                        Quantity{getSortIndicator('quantity')}
                      </th>
                      <th
                        className="px-4 py-3 text-left text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                        onClick={() => handleColumnSort('position_value')}
                      >
                        Position Value{getSortIndicator('position_value')}
                      </th>
                      <th
                        className="px-4 py-3 text-left text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                        onClick={() => handleColumnSort('position_gain_pct')}
                      >
                        Position Gain %{getSortIndicator('position_gain_pct')}
                      </th>
                      <th className="px-4 py-3 text-left text-slate-400 font-medium">Portfolio</th>
                      <th className="px-4 py-3 text-left text-slate-400 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedPositions.map((pos: any) => (
                      <tr
                        key={`${pos.ticker}-${pos.portfolio}`}
                        className="border-t border-slate-800 hover:bg-slate-800/30 transition cursor-pointer"
                        onClick={() => navigate(`/portfolios/${encodeURIComponent(pos.portfolio)}/holdings`)}
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 bg-gradient-to-br from-purple-500 to-violet-600 rounded flex items-center justify-center text-xs font-bold text-white">
                              {pos.ticker.charAt(0)}
                            </div>
                            <span className="text-white font-medium">{pos.ticker}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-slate-300 text-sm font-medium">{pos.company_name}</td>
                        <td className="px-4 py-3 text-slate-300 text-sm">
                          <span className="inline-block px-2 py-1 rounded bg-slate-800/50 text-xs">
                            {pos.sector}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-white font-medium">
                          {formatCurrency(pos.current_price, pos.currency)}
                        </td>
                        <td className={`px-4 py-3 font-medium ${pos.daily_change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {pos.daily_change >= 0 ? '+' : ''}{formatCurrency(Math.abs(pos.daily_change), pos.currency)}
                        </td>
                        <td className={`px-4 py-3 font-medium ${pos.daily_change_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {pos.daily_change_pct >= 0 ? '+' : ''}{pos.daily_change_pct.toFixed(2)}%
                        </td>
                        <td className="px-4 py-3 text-white">{pos.quantity}</td>
                        <td className="px-4 py-3 text-white font-medium">
                          {formatCurrency(pos.position_value, pos.currency)}
                        </td>
                        <td className={`px-4 py-3 font-medium ${pos.position_gain_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {pos.position_gain_pct >= 0 ? '+' : ''}{pos.position_gain_pct.toFixed(2)}%
                        </td>
                        <td className="px-4 py-3 text-slate-300 text-sm">{pos.portfolio}</td>
                        <td className="px-4 py-3">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              navigate(`/portfolios/${encodeURIComponent(pos.portfolio)}/holdings`)
                            }}
                            className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded transition"
                          >
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  )
}
