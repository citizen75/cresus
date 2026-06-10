import { useState } from 'react'

interface AlertMatch {
  ticker: string
  company_name?: string
  [key: string]: any
}

interface AlertResultsTableProps {
  matches: AlertMatch[]
  searchQuery?: string
  onSearchChange?: (query: string) => void
  sortColumn?: string | null
  onSortChange?: (column: string) => void
  sortDirection?: 'asc' | 'desc'
}

export default function AlertResultsTable({
  matches,
  searchQuery = '',
  onSearchChange,
  sortColumn = 'ticker',
  onSortChange,
  sortDirection = 'asc',
}: AlertResultsTableProps) {
  const [internalSearch, setInternalSearch] = useState('')
  const search = searchQuery !== undefined ? searchQuery : internalSearch

  // Get sortable columns from first match
  const allColumns = matches.length > 0 ? Object.keys(matches[0]) : []
  const displayColumns = ['ticker', 'company_name', ...allColumns.filter(c => !['ticker', 'company_name'].includes(c))].filter((col, idx, arr) => arr.indexOf(col) === idx)

  // Filter matches
  const filteredMatches = matches.filter(match => {
    if (!search) return true
    const query = search.toLowerCase()
    return Object.values(match).some(val =>
      String(val).toLowerCase().includes(query)
    )
  })

  // Sort matches
  const sortedMatches = [...filteredMatches].sort((a, b) => {
    if (!sortColumn) return 0

    const aVal = a[sortColumn]
    const bVal = b[sortColumn]

    if (aVal === null || aVal === undefined) return 1
    if (bVal === null || bVal === undefined) return -1

    let comparison = 0
    if (typeof aVal === 'string') {
      comparison = aVal.localeCompare(bVal)
    } else {
      comparison = Number(aVal) - Number(bVal)
    }

    return sortDirection === 'asc' ? comparison : -comparison
  })

  const formatValue = (val: any) => {
    if (val === null || val === undefined) return '—'
    if (typeof val === 'number') return val.toFixed(2)
    return String(val)
  }

  const handleHeaderClick = (column: string) => {
    onSortChange?.(column === sortColumn ? column : column)
  }

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      {onSearchChange && (
        <div className="relative">
          <input
            type="text"
            placeholder="Search matches..."
            value={search}
            onChange={(e) => {
              setInternalSearch(e.target.value)
              onSearchChange(e.target.value)
            }}
            className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white rounded-lg focus:outline-none focus:border-purple-500 text-sm"
          />
          <span className="absolute right-4 top-2.5 text-slate-500 text-sm">
            {filteredMatches.length} of {matches.length}
          </span>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto border border-slate-700 rounded-lg">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-700 bg-slate-950">
              {displayColumns.map((col) => (
                <th
                  key={col}
                  onClick={() => handleHeaderClick(col)}
                  className={`px-4 py-3 text-left text-xs font-semibold text-slate-400 ${
                    ['ticker', 'company_name'].includes(col)
                      ? 'sticky bg-slate-950 z-10'
                      : ''
                  } ${col === 'ticker' ? 'left-0 w-20' : col === 'company_name' ? 'left-20' : ''} ${
                    onSortChange ? 'cursor-pointer hover:text-slate-300' : ''
                  }`}
                  style={
                    col === 'ticker'
                      ? { left: 0 }
                      : col === 'company_name'
                        ? { left: '80px' }
                        : undefined
                  }
                >
                  <div className="flex items-center gap-2">
                    {col.replace(/_/g, ' ')}
                    {sortColumn === col && (
                      <span className="text-purple-400">
                        {sortDirection === 'asc' ? '↑' : '↓'}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {sortedMatches.map((match, idx) => (
              <tr key={`${match.ticker}-${idx}`} className="hover:bg-slate-800/50 transition">
                {displayColumns.map((col) => (
                  <td
                    key={`${match.ticker}-${col}`}
                    className={`px-4 py-3 text-sm text-slate-300 ${
                      ['ticker', 'company_name'].includes(col)
                        ? 'sticky font-medium text-white bg-slate-900 z-10'
                        : ''
                    } ${col === 'ticker' ? 'left-0 w-20' : col === 'company_name' ? 'left-20' : ''}`}
                    style={
                      col === 'ticker'
                        ? { left: 0 }
                        : col === 'company_name'
                          ? { left: '80px' }
                          : undefined
                    }
                  >
                    {col === 'ticker' ? (
                      <span className="font-bold text-purple-400">{match[col]}</span>
                    ) : (
                      formatValue(match[col])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>

        {sortedMatches.length === 0 && (
          <div className="p-6 text-center text-slate-500">
            No matches found
          </div>
        )}
      </div>
    </div>
  )
}
