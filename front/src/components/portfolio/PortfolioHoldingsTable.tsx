import { useState } from 'react'
import { formatCurrency } from '@/utils/currency'

interface PortfolioHoldingsTableProps {
  positions: any[]
  totalValue: number
  currency?: string
  fundamentalData?: Record<string, any>
  selectedPosition?: string | null
  onSelectPosition?: (ticker: string, position: any) => void
  showSearch?: boolean
  showActions?: boolean
  filterTickers?: string[] // Optional: filter positions to only these tickers
  externalSearchQuery?: string // Optional: search query from parent
  onSearchChange?: (query: string) => void // Callback when search changes
}

export function PortfolioHoldingsTable({
  positions,
  totalValue,
  currency = 'USD',
  fundamentalData = {},
  selectedPosition = null,
  onSelectPosition,
  showSearch = true,
  showActions = true,
  filterTickers,
  externalSearchQuery = '',
  onSearchChange,
}: PortfolioHoldingsTableProps) {
  const [internalSearchQuery, setInternalSearchQuery] = useState<string>('')
  const searchQuery = externalSearchQuery !== undefined ? externalSearchQuery : internalSearchQuery
  const [sortColumn, setSortColumn] = useState<string | null>('weight')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')

  // Filter positions
  const filteredPositions = positions.filter((pos) => {
    // Filter by ticker if filterTickers provided
    if (filterTickers && !filterTickers.includes(pos.ticker)) {
      return false
    }
    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      return (
        pos.ticker.toLowerCase().includes(query) ||
        (pos.company_name && pos.company_name.toLowerCase().includes(query))
      )
    }
    return true
  })

  // Sort positions
  const getSortedPositions = () => {
    return [...filteredPositions].sort((a: any, b: any) => {
      let aVal, bVal

      switch (sortColumn) {
        case 'symbol':
          aVal = a.ticker
          bVal = b.ticker
          break
        case 'company':
          aVal = a.company_name || a.ticker
          bVal = b.company_name || b.ticker
          break
        case 'sector':
          aVal = a.sector || 'Unknown'
          bVal = b.sector || 'Unknown'
          break
        case 'type':
          aVal = a.asset_type || 'Stock'
          bVal = b.asset_type || 'Stock'
          break
        case 'weight':
          aVal = (a.position_value / totalValue) * 100
          bVal = (b.position_value / totalValue) * 100
          break
        case 'shares':
          aVal = a.quantity
          bVal = b.quantity
          break
        case 'avg_cost':
          aVal = a.avg_entry_price
          bVal = b.avg_entry_price
          break
        case 'price':
          aVal = a.current_price
          bVal = b.current_price
          break
        case 'daily_change':
          const aFund = fundamentalData[a.ticker] || {}
          const bFund = fundamentalData[b.ticker] || {}
          const aPrevClose = aFund.previous_close || a.current_price
          const bPrevClose = bFund.previous_close || b.current_price
          aVal = a.current_price - aPrevClose
          bVal = b.current_price - bPrevClose
          break
        case 'market_value':
          aVal = a.position_value
          bVal = b.position_value
          break
        case 'unrealized_pnl':
          aVal = a.position_gain
          bVal = b.position_gain
          break
        case 'pnl_pct':
          aVal = a.position_gain_pct
          bVal = b.position_gain_pct
          break
        default:
          return 0
      }

      // String comparison
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDirection === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }

      // Numeric comparison
      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : aVal < bVal ? -1 : 0
      } else {
        return bVal > aVal ? 1 : bVal < aVal ? -1 : 0
      }
    })
  }

  const handleColumnSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('asc')
    }
  }

  const getSortIndicator = (column: string) => {
    if (sortColumn !== column) return ''
    return sortDirection === 'asc' ? ' ↑' : ' ↓'
  }

  const sortedPositions = getSortedPositions()

  return (
    <div className="space-y-4">
      {/* Search Bar - Only show if not using external search */}
      {showSearch && !externalSearchQuery && (
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Search by symbol or company..."
            value={internalSearchQuery}
            onChange={(e) => setInternalSearchQuery(e.target.value)}
            className="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-600"
          />
          {internalSearchQuery && (
            <button
              onClick={() => setInternalSearchQuery('')}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-sm transition"
            >
              Clear
            </button>
          )}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto overflow-y-auto max-h-[600px] rounded border border-slate-800">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-slate-800/50 border-b border-slate-700">
            <tr>
              <th
                className="px-4 py-3 text-left text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                onClick={() => handleColumnSort('symbol')}
              >
                Symbol{getSortIndicator('symbol')}
              </th>
              <th
                className="px-4 py-3 text-left text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                onClick={() => handleColumnSort('company')}
              >
                Company{getSortIndicator('company')}
              </th>
              <th
                className="px-4 py-3 text-left text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                onClick={() => handleColumnSort('weight')}
              >
                Weight{getSortIndicator('weight')}
              </th>
              <th
                className="px-4 py-3 text-right text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                onClick={() => handleColumnSort('shares')}
              >
                Shares{getSortIndicator('shares')}
              </th>
              <th
                className="px-4 py-3 text-right text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                onClick={() => handleColumnSort('avg_cost')}
              >
                Avg. Cost{getSortIndicator('avg_cost')}
              </th>
              <th
                className="px-4 py-3 text-right text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                onClick={() => handleColumnSort('price')}
              >
                Price{getSortIndicator('price')}
              </th>
              <th
                className="px-4 py-3 text-right text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                onClick={() => handleColumnSort('daily_change')}
              >
                Daily Change{getSortIndicator('daily_change')}
              </th>
              <th
                className="px-4 py-3 text-right text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                onClick={() => handleColumnSort('market_value')}
              >
                Market Value{getSortIndicator('market_value')}
              </th>
              <th
                className="px-4 py-3 text-right text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                onClick={() => handleColumnSort('unrealized_pnl')}
              >
                P&L{getSortIndicator('unrealized_pnl')}
              </th>
              <th
                className="px-4 py-3 text-right text-slate-400 font-medium cursor-pointer hover:text-slate-200 transition"
                onClick={() => handleColumnSort('pnl_pct')}
              >
                P&L %{getSortIndicator('pnl_pct')}
              </th>
              {showActions && <th className="px-4 py-3 text-center text-slate-400 font-medium">Actions</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {sortedPositions.length === 0 ? (
              <tr>
                <td colSpan={showActions ? 11 : 10} className="px-4 py-8 text-center text-slate-500">
                  No positions found
                </td>
              </tr>
            ) : (
              sortedPositions.map((pos: any) => {
                const weight = totalValue > 0 ? ((pos.position_value || 0) / totalValue) * 100 : 0
                const dailyChange = pos.position_gain || 0
                const dailyChangePct = pos.position_gain_pct || 0

                return (
                  <tr
                    key={pos.ticker}
                    onClick={() => onSelectPosition?.(pos.ticker, pos)}
                    className={`hover:bg-slate-800/50 transition ${
                      onSelectPosition ? 'cursor-pointer' : ''
                    } ${selectedPosition === pos.ticker ? 'bg-slate-800/30' : ''}`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-5 h-5 bg-gradient-to-br from-purple-500 to-violet-600 rounded flex items-center justify-center text-xs font-bold text-white">
                          {pos.ticker.charAt(0)}
                        </div>
                        <span className="text-white font-medium">{pos.ticker}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-300 truncate max-w-xs">{pos.company_name || '-'}</td>
                    <td className="px-4 py-3 text-white font-medium">{isNaN(weight) ? '0.0' : weight.toFixed(1)}%</td>
                    <td className="px-4 py-3 text-right text-slate-300">{pos.quantity !== null && pos.quantity !== undefined ? pos.quantity : '-'}</td>
                    <td className="px-4 py-3 text-right text-slate-300">{formatCurrency(pos.avg_entry_price || 0, currency)}</td>
                    <td className="px-4 py-3 text-right text-white font-medium">{formatCurrency(pos.current_price || 0, currency)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex flex-col items-end">
                        <span className={`font-medium text-sm ${dailyChange >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {dailyChange >= 0 ? '+' : ''}{formatCurrency(Math.abs(dailyChange || 0), currency)}
                        </span>
                        <span className={`text-xs ${(dailyChangePct || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {(dailyChangePct || 0) >= 0 ? '+' : ''}{(dailyChangePct || 0).toFixed(2)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-white font-medium">{formatCurrency(pos.position_value || 0, currency)}</td>
                    <td className={`px-4 py-3 text-right font-medium ${(pos.position_gain || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {(pos.position_gain || 0) >= 0 ? '+' : ''}{formatCurrency(Math.abs(pos.position_gain || 0), currency)}
                    </td>
                    <td className={`px-4 py-3 text-right font-medium ${(pos.position_gain_pct || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {(pos.position_gain_pct || 0) > 0 ? '+' : ''}{(pos.position_gain_pct || 0).toFixed(2)}%
                    </td>
                    {showActions && (
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            onSelectPosition?.(pos.ticker, pos)
                          }}
                          className="text-slate-400 hover:text-slate-200 transition"
                          title="View details"
                        >
                          📊
                        </button>
                      </td>
                    )}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Results count */}
      <div className="text-xs text-slate-500">
        Showing {sortedPositions.length} of {positions.length} positions
      </div>
    </div>
  )
}
