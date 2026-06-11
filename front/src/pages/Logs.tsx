import { useState, useEffect } from 'react'

interface LogEntry {
  timestamp: string
  level: string
  message: string
  component?: string
}

export default function Logs() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<string>('all')
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    loadLogs()
  }, [])

  const loadLogs = async () => {
    setLoading(true)
    try {
      // Fetch logs from API (placeholder - adjust endpoint as needed)
      // const response = await fetch('http://192.168.0.130:6501/api/v1/logs')
      // const data = await response.json()
      // setLogs(data.logs || [])

      // For now, show placeholder message
      setLogs([])
    } catch (err) {
      console.error('Failed to load logs:', err)
    } finally {
      setLoading(false)
    }
  }

  const filteredLogs = logs.filter(log => {
    const levelMatch = filter === 'all' || log.level === filter
    const searchMatch =
      log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.component?.toLowerCase().includes(searchTerm.toLowerCase())
    return levelMatch && searchMatch
  })

  const logLevels = ['all', 'INFO', 'WARNING', 'ERROR', 'DEBUG']

  return (
    <div className="flex-1 overflow-hidden flex flex-col">
      {/* Controls */}
      <div className="px-6 py-4 border-b border-slate-800 space-y-3">
        <div className="flex gap-4 items-center">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search logs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
            />
          </div>
          <button
            onClick={loadLogs}
            disabled={loading}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-700 text-white rounded font-medium transition text-sm"
          >
            {loading ? '⏳ Loading...' : '🔄 Refresh'}
          </button>
        </div>

        <div className="flex gap-2">
          {logLevels.map(level => (
            <button
              key={level}
              onClick={() => setFilter(level)}
              className={`px-3 py-1 rounded text-xs font-medium transition ${
                filter === level
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      {/* Logs List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full text-slate-400">
            Loading logs...
          </div>
        ) : logs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-400">
            <div className="text-center">
              <p className="text-sm mb-2">📋 Logs View</p>
              <p className="text-xs text-slate-500">
                Log streaming endpoint not yet configured
              </p>
              <p className="text-xs text-slate-500 mt-2">
                Implement: GET /api/v1/logs with optional filters
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-0">
            {filteredLogs.map((log, idx) => (
              <div
                key={idx}
                className={`px-6 py-3 border-b border-slate-800 text-xs font-mono ${
                  log.level === 'ERROR'
                    ? 'bg-red-950/20 text-red-300'
                    : log.level === 'WARNING'
                    ? 'bg-yellow-950/20 text-yellow-300'
                    : 'text-slate-400'
                }`}
              >
                <div className="flex gap-4">
                  <span className="text-slate-500">{log.timestamp}</span>
                  <span className="font-semibold w-12">{log.level}</span>
                  {log.component && <span className="text-slate-500">{log.component}</span>}
                  <span className="flex-1">{log.message}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
