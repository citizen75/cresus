import { useState } from 'react'

interface ResultTableProps {
  data: any[]
  searchQuery?: string
  onSearchChange?: (query: string) => void
  sortColumn?: string | null
  onSortChange?: (column: string) => void
  sortDirection?: 'asc' | 'desc'
  onRowClick?: (row: any) => void
  selectedRow?: any | null
}

export default function ResultTable({
  data,
  searchQuery = '',
  onSearchChange,
  sortColumn = null,
  onSortChange,
  sortDirection = 'asc',
  onRowClick,
  selectedRow = null,
}: ResultTableProps) {
  const [internalSearch, setInternalSearch] = useState('')
  const search = searchQuery !== undefined ? searchQuery : internalSearch

  // Filter and sort results
  const filteredAndSorted = (() => {
    let filtered = data.filter((row) => {
      if (!search.trim()) return true
      const query = search.toLowerCase()
      return Object.values(row).some((val) =>
        String(val).toLowerCase().includes(query)
      )
    })

    if (sortColumn) {
      filtered.sort((a, b) => {
        const aVal = a[sortColumn]
        const bVal = b[sortColumn]
        const isNumeric = typeof aVal === 'number' && typeof bVal === 'number'

        if (isNumeric) {
          return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
        } else {
          const aStr = String(aVal || '').toLowerCase()
          const bStr = String(bVal || '').toLowerCase()
          return sortDirection === 'asc'
            ? aStr.localeCompare(bStr)
            : bStr.localeCompare(aStr)
        }
      })
    }

    return filtered
  })()

  const handleColumnSort = (column: string) => {
    if (!onSortChange) return
    if (sortColumn === column) {
      // Already sorted by this column - toggle direction would happen in parent
      onSortChange(column)
    } else {
      onSortChange(column)
    }
  }

  const formatValue = (value: any, key: string) => {
    let displayValue = String(value || '')
    const numValue = typeof value === 'number' ? value : parseFloat(String(value || 0))

    if (!isNaN(numValue)) {
      // Format volume with 0 decimal places
      if (key.toLowerCase().includes('volume') || key.toLowerCase().includes('vol')) {
        displayValue = numValue.toFixed(0)
      } else {
        // Format other numbers with 3 decimal places
        displayValue = numValue.toFixed(3)
      }
    }

    return displayValue
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-12 text-slate-400">
        No data to display
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Search Bar */}
      {onSearchChange && (
        <div className="relative">
          <input
            type="text"
            placeholder="Search results..."
            value={search}
            onChange={(e) => {
              setInternalSearch(e.target.value)
              onSearchChange(e.target.value)
            }}
            className="w-full px-4 py-2 bg-slate-800 border border-slate-700 text-white rounded-lg focus:outline-none focus:border-purple-500 text-sm"
          />
          <span className="absolute right-4 top-2.5 text-slate-500 text-sm">
            {filteredAndSorted.length} of {data.length}
          </span>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto border border-slate-700 rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-slate-800/50 border-b border-slate-800">
            <tr>
              {data.length > 0 &&
                Object.keys(data[0]).map((key) => (
                  <th
                    key={key}
                    onClick={() => handleColumnSort(key)}
                    className="px-6 py-3 text-left text-slate-300 font-medium cursor-pointer hover:bg-slate-700/50 transition"
                  >
                    <div className="flex items-center gap-2">
                      {key}
                      {sortColumn === key && (
                        <span className="text-xs text-slate-400">
                          {sortDirection === 'asc' ? '↑' : '↓'}
                        </span>
                      )}
                    </div>
                  </th>
                ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {filteredAndSorted.map((row, idx) => (
              <tr
                key={idx}
                className={`hover:bg-slate-800/50 transition ${
                  onRowClick ? 'cursor-pointer' : ''
                } ${
                  selectedRow &&
                  JSON.stringify(selectedRow) === JSON.stringify(row)
                    ? 'bg-slate-800/50 border-l-2 border-l-purple-600'
                    : ''
                }`}
                onClick={() => onRowClick?.(row)}
              >
                {Object.entries(row).map(([key, value], colIdx) => (
                  <td key={colIdx} className="px-6 py-3 text-slate-300">
                    {formatValue(value, key)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
