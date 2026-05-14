import { useState, useEffect } from 'react'
import { getApiBaseUrl, api } from '@/services/api'

interface StrategyBuilderProps {
  name: string
}

interface Strategy {
  name: string
  universe: string
  description: string
  engine: string
  indicators: string[]
  buy_conditions: string
  sell_conditions: string
  watchlist?: {
    enabled: boolean
    parameters: Record<string, any>
  }
  signals?: {
    enabled: boolean
    weights: Record<string, number>
    parameters: Record<string, any>
  }
  entry?: {
    enabled: boolean
    parameters: Record<string, any>
  }
  exit?: {
    enabled: boolean
    parameters: Record<string, any>
  }
  backtest?: {
    initial_capital: number
  }
}

export default function StrategyBuilder({ name }: StrategyBuilderProps) {
  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingWatchlist, setEditingWatchlist] = useState(false)
  const [editingEntry, setEditingEntry] = useState(false)
  const [editingExit, setEditingExit] = useState(false)
  const [editingSignals, setEditingSignals] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  
  // Form state
  const [entryForm, setEntryForm] = useState<any>(null)
  const [exitForm, setExitForm] = useState<any>(null)
  const [watchlistForm, setWatchlistForm] = useState<any>(null)
  const [signalsForm, setSignalsForm] = useState<any>(null)
  const [editingBasic, setEditingBasic] = useState(false)
  const [basicForm, setBasicForm] = useState<any>(null)
  const [universes, setUniverses] = useState<string[]>([])
  const [loadingUniverses, setLoadingUniverses] = useState(false)

  useEffect(() => {
    const fetchStrategy = async () => {
      try {
        const baseUrl = getApiBaseUrl()

        // First, fetch portfolio details to get the strategy name
        const portfolioResponse = await fetch(`${baseUrl}/api/v1/portfolios/${name}`)
        if (!portfolioResponse.ok) {
          throw new Error(`Failed to fetch portfolio: ${portfolioResponse.statusText}`)
        }
        const portfolioData = await portfolioResponse.json()
        const strategyName = portfolioData.strategy || name

        // Then fetch the strategy using the strategy name
        const strategyResponse = await fetch(`${baseUrl}/api/v1/strategies/${strategyName}`)
        if (!strategyResponse.ok) {
          throw new Error(`Failed to fetch strategy: ${strategyResponse.statusText}`)
        }
        const strategyData = await strategyResponse.json()
        setStrategy(strategyData.strategy)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchStrategy()
  }, [name])

  const handleEditBasic = async () => {
    if (!strategy) return
    setBasicForm({
      universe: strategy.universe,
      description: strategy.description,
    })
    setEditingBasic(true)

    // Fetch universes list
    setLoadingUniverses(true)
    try {
      const data = await api.listUniverses()
      setUniverses(data.universes || [])
    } catch (err) {
      console.error('Failed to load universes:', err)
    } finally {
      setLoadingUniverses(false)
    }
  }

  const handleSaveBasic = async () => {
    if (!basicForm) return

    const updates: any = {}
    if (basicForm.universe !== strategy?.universe) {
      updates.universe = basicForm.universe
    }
    if (basicForm.description !== strategy?.description) {
      updates.description = basicForm.description
    }

    if (Object.keys(updates).length === 0) {
      setEditingBasic(false)
      return
    }

    await saveStrategy(updates)
    setEditingBasic(false)
  }

  const saveStrategy = async (updates: any) => {
    if (!strategy) return

    setIsSaving(true)

    try {
      const baseUrl = getApiBaseUrl()
      const response = await fetch(`${baseUrl}/api/v1/strategies/${name}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      })

      if (!response.ok) {
        throw new Error(`Failed to update strategy: ${response.statusText}`)
      }
      
      const data = await response.json()
      setStrategy(data.strategy)
      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      console.error('Save error:', message)
      return false
    } finally {
      setIsSaving(false)
    }
  }

  const handleSaveEntry = async () => {
    if (!entryForm) return
    const success = await saveStrategy({ entry: entryForm })
    if (success) {
      setEditingEntry(false)
      setEntryForm(null)
    }
  }

  const handleSaveExit = async () => {
    if (!exitForm) return
    const success = await saveStrategy({ exit: exitForm })
    if (success) {
      setEditingExit(false)
      setExitForm(null)
    }
  }

  const handleSaveWatchlist = async () => {
    if (!watchlistForm) return
    const success = await saveStrategy({ watchlist: watchlistForm })
    if (success) {
      setEditingWatchlist(false)
      setWatchlistForm(null)
    }
  }

  const handleSaveSignals = async () => {
    if (!signalsForm) return
    const success = await saveStrategy({ signals: signalsForm })
    if (success) {
      setEditingSignals(false)
      setSignalsForm(null)
    }
  }

  if (loading) {
    return <div className="text-slate-400 py-12 text-center">Loading strategy...</div>
  }

  if (error) {
    return <div className="text-red-400 py-12 text-center">Error: {error}</div>
  }

  if (!strategy) {
    return <div className="text-slate-400 py-12 text-center">Strategy not found</div>
  }

  return (
    <div className="space-y-6">
      {/* Header with Save Button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Strategy definition</h2>
          <p className="text-slate-400 text-sm mt-1">{strategy.description}</p>
        </div>
        <button className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition">
          Save strategy
        </button>
      </div>

      {/* Strategy Status */}
      <div className="flex items-center gap-2 text-sm">
        <span className="w-2 h-2 bg-green-400 rounded-full"></span>
        <span className="text-green-400">Strategy active</span>
      </div>

      {/* Strategy Info Cards */}
      <div className="grid grid-cols-4 gap-6">
        {/* Left Sidebar: Universe & Indicators */}
        <div className="space-y-6">
          {/* Universe */}
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
            <h3 className="text-white font-bold mb-2 text-sm">Universe</h3>
            {editingBasic ? (
              <div className="space-y-2">
                <div>
                  <p className="text-slate-400 text-xs uppercase mb-1">Universe</p>
                  {loadingUniverses ? (
                    <div className="w-full bg-slate-800 border border-slate-700 text-slate-400 rounded px-2 py-1 text-xs">
                      Loading...
                    </div>
                  ) : (
                    <select
                      value={basicForm?.universe || ''}
                      onChange={(e) => setBasicForm({ ...basicForm, universe: e.target.value })}
                      className="w-full bg-slate-800 border border-slate-700 text-white rounded px-2 py-1 text-xs focus:border-purple-500 focus:outline-none"
                    >
                      <option value="">Select a universe</option>
                      {universes.map((u) => (
                        <option key={u} value={u}>
                          {u}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
                <div>
                  <p className="text-slate-400 text-xs uppercase mb-1">Description</p>
                  <textarea
                    value={basicForm?.description || ''}
                    onChange={(e) => setBasicForm({ ...basicForm, description: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 text-white rounded px-2 py-1 text-xs focus:border-purple-500 focus:outline-none h-16 resize-none"
                  />
                </div>
                <div className="flex gap-2 pt-2">
                  <button
                    onClick={handleSaveBasic}
                    disabled={isSaving}
                    className="flex-1 px-2 py-1 bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium rounded transition disabled:opacity-50"
                  >
                    {isSaving ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    onClick={() => setEditingBasic(false)}
                    className="flex-1 px-2 py-1 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded transition"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  <div className="bg-slate-800/50 rounded p-2">
                    <p className="text-slate-400 text-xs uppercase mb-0.5">Universe</p>
                    <p className="text-white font-medium text-xs capitalize">{strategy.universe.replace(/_/g, ' ')}</p>
                  </div>
                  <div className="bg-slate-800/50 rounded p-2">
                    <p className="text-slate-400 text-xs uppercase mb-0.5">Engine</p>
                    <p className="text-white font-medium text-xs">{strategy.engine}</p>
                  </div>
                </div>
                <button
                  onClick={handleEditBasic}
                  className="w-full mt-2 px-2 py-1 text-purple-400 hover:text-purple-300 text-xs font-medium transition"
                >
                  Edit
                </button>
              </>
            )}
          </div>

          {/* Indicators */}
          <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-white font-bold text-sm">Indicators</h3>
              <button className="text-purple-400 hover:text-purple-300 text-xs font-medium transition">
                Manage
              </button>
            </div>
            <div className="space-y-2">
              {strategy.indicators?.map((indicator) => (
                <div key={indicator} className="flex items-center gap-2 p-2 bg-blue-900/20 rounded border border-blue-800/50">
                  <span className="w-1.5 h-1.5 bg-blue-400 rounded-full"></span>
                  <span className="text-blue-400 text-xs font-medium">{indicator}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Watchlist Config */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-bold">Watchlist</h3>
            <button
              onClick={() => {
                if (editingWatchlist) {
                  handleSaveWatchlist()
                } else {
                  setWatchlistForm({
                    enabled: strategy.watchlist?.enabled || false,
                    parameters: JSON.parse(JSON.stringify(strategy.watchlist?.parameters || {}))
                  })
                  setEditingWatchlist(true)
                }
              }}
              disabled={isSaving}
              className="text-purple-400 hover:text-purple-300 text-sm font-medium disabled:opacity-50"
            >
              {editingWatchlist ? (isSaving ? 'Saving...' : 'Done') : 'Edit'}
            </button>
          </div>

          {editingWatchlist ? (
            // Edit Form
            <div className="space-y-3">
              <div>
                <label className="text-slate-400 text-xs uppercase block mb-1">Volume Min</label>
                <input
                  type="number"
                  defaultValue={strategy.watchlist?.parameters?.volume?.min_volume || 500000}
                  onChange={(e) => {
                    setWatchlistForm({
                      ...watchlistForm,
                      parameters: {
                        ...watchlistForm?.parameters,
                        volume: {
                          ...watchlistForm?.parameters?.volume,
                          min_volume: parseInt(e.target.value)
                        }
                      }
                    })
                  }}
                  className="w-full bg-slate-800 border border-slate-700 text-white px-2 py-1 rounded text-xs"
                />
              </div>
              <div>
                <label className="text-slate-400 text-xs uppercase block mb-1">Ranking</label>
                <input
                  type="text"
                  defaultValue={strategy.watchlist?.parameters?.ranking?.metric || 'score'}
                  onChange={(e) => {
                    setWatchlistForm({
                      ...watchlistForm,
                      parameters: {
                        ...watchlistForm?.parameters,
                        ranking: {
                          ...watchlistForm?.parameters?.ranking,
                          metric: e.target.value
                        }
                      }
                    })
                  }}
                  className="w-full bg-slate-800 border border-slate-700 text-white px-2 py-1 rounded text-xs"
                />
              </div>
              <div>
                <label className="text-slate-400 text-xs uppercase block mb-1">Trend</label>
                <textarea
                  defaultValue={strategy.watchlist?.parameters?.trend?.formula || ''}
                  onChange={(e) => {
                    setWatchlistForm({
                      ...watchlistForm,
                      parameters: {
                        ...watchlistForm?.parameters,
                        trend: {
                          formula: e.target.value,
                          description: watchlistForm?.parameters?.trend?.description || ''
                        }
                      }
                    })
                  }}
                  className="w-full bg-slate-800 border border-slate-700 text-white px-2 py-1 rounded text-xs font-mono h-12"
                />
              </div>
              <div>
                <label className="text-slate-400 text-xs uppercase block mb-1">Volatility</label>
                <textarea
                  defaultValue={strategy.watchlist?.parameters?.volatility?.formula || ''}
                  onChange={(e) => {
                    setWatchlistForm({
                      ...watchlistForm,
                      parameters: {
                        ...watchlistForm?.parameters,
                        volatility: {
                          formula: e.target.value,
                          description: watchlistForm?.parameters?.volatility?.description || ''
                        }
                      }
                    })
                  }}
                  className="w-full bg-slate-800 border border-slate-700 text-white px-2 py-1 rounded text-xs font-mono h-12"
                />
              </div>
            </div>
          ) : (
            // Display View
            <div className="space-y-2 text-xs">
              {strategy.watchlist?.parameters?.volume && (
                <div className="bg-slate-800/50 rounded p-2">
                  <p className="text-slate-400 uppercase mb-1">Volume Min</p>
                  <p className="text-white font-medium">{strategy.watchlist.parameters.volume.min_volume?.toLocaleString()}</p>
                </div>
              )}
              {strategy.watchlist?.parameters?.ranking && (
                <div className="bg-slate-800/50 rounded p-2">
                  <p className="text-slate-400 uppercase mb-1">Ranking</p>
                  <p className="text-white font-medium">{strategy.watchlist.parameters.ranking.metric}</p>
                </div>
              )}
              {strategy.watchlist?.parameters?.trend && (
                <div className="bg-slate-800/50 rounded p-2">
                  <p className="text-slate-400 uppercase mb-1 text-xs">Trend</p>
                  <p className="text-slate-300 text-xs font-mono break-all line-clamp-2">{strategy.watchlist.parameters.trend.formula}</p>
                </div>
              )}
              {strategy.watchlist?.parameters?.volatility && (
                <div className="bg-slate-800/50 rounded p-2">
                  <p className="text-slate-400 uppercase mb-1 text-xs">Volatility</p>
                  <p className="text-slate-300 text-xs font-mono break-all line-clamp-2">{strategy.watchlist.parameters.volatility.formula}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Entry Conditions */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-bold">Entry</h3>
            <button
              onClick={() => {
                if (editingEntry) {
                  handleSaveEntry()
                } else {
                  setEntryForm({
                    enabled: strategy.entry?.enabled || false,
                    parameters: JSON.parse(JSON.stringify(strategy.entry?.parameters || {}))
                  })
                  setEditingEntry(true)
                }
              }}
              disabled={isSaving}
              className="text-purple-400 hover:text-purple-300 text-sm font-medium disabled:opacity-50"
            >
              {editingEntry ? (isSaving ? 'Saving...' : 'Done') : 'Edit'}
            </button>
          </div>

          {editingEntry ? (
            // Edit Form
            <div className="space-y-4">
              {strategy.entry?.parameters && Object.entries(strategy.entry.parameters).map(([key, value]: [string, any]) => (
                <div key={key}>
                  <label className="text-slate-400 text-xs uppercase block mb-1 capitalize">{key.replace(/_/g, ' ')}</label>
                  {typeof value === 'object' && value.formula !== undefined ? (
                    <>
                      <textarea
                        defaultValue={value.formula || ''}
                        onChange={(e) => {
                          setEntryForm({
                            ...entryForm,
                            parameters: {
                              ...entryForm?.parameters,
                              [key]: {
                                ...value,
                                formula: e.target.value
                              }
                            }
                          })
                        }}
                        className="w-full bg-slate-800 border border-slate-700 text-white px-2 py-1 rounded text-xs font-mono h-12"
                      />
                      {value.type && (
                        <div className="mt-1 text-xs text-slate-500">Type: {value.type}</div>
                      )}
                    </>
                  ) : (
                    <input
                      type="text"
                      defaultValue={value || ''}
                      onChange={(e) => {
                        setEntryForm({
                          ...entryForm,
                          parameters: {
                            ...entryForm?.parameters,
                            [key]: e.target.value
                          }
                        })
                      }}
                      className="w-full bg-slate-800 border border-slate-700 text-white px-2 py-1 rounded text-xs"
                    />
                  )}
                  {typeof value === 'object' && value.description && (
                    <p className="text-slate-500 text-xs mt-1">{value.description}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            // Display View
            strategy.entry?.enabled ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 p-2 bg-green-900/20 rounded border border-green-800/50">
                  <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                  <span className="text-green-400 text-xs font-medium">Enabled</span>
                </div>
                {strategy.entry.parameters && Object.entries(strategy.entry.parameters).map(([key, value]: [string, any]) => (
                  <div key={key}>
                    <p className="text-slate-400 text-xs uppercase mb-1 capitalize">{key.replace(/_/g, ' ')}</p>
                    <div className="text-slate-300 text-xs bg-slate-800/30 p-2 rounded font-mono break-all">
                      {typeof value === 'object' ? value.formula : value}
                    </div>
                    {typeof value === 'object' && value.description && (
                      <p className="text-slate-500 text-xs mt-1">{value.description}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-slate-400 text-sm">Not configured</div>
            )
          )}
        </div>

        {/* Exit Conditions */}
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-bold">Exit</h3>
            <button
              onClick={() => {
                if (editingExit) {
                  handleSaveExit()
                } else {
                  setExitForm({
                    enabled: strategy.exit?.enabled || false,
                    parameters: JSON.parse(JSON.stringify(strategy.exit?.parameters || {}))
                  })
                  setEditingExit(true)
                }
              }}
              disabled={isSaving}
              className="text-purple-400 hover:text-purple-300 text-sm font-medium disabled:opacity-50"
            >
              {editingExit ? (isSaving ? 'Saving...' : 'Done') : 'Edit'}
            </button>
          </div>

          {editingExit ? (
            // Edit Form
            <div className="space-y-4">
              {strategy.exit?.parameters && Object.entries(strategy.exit.parameters).map(([key, value]: [string, any]) => (
                <div key={key}>
                  <label className="text-slate-400 text-xs uppercase block mb-1 capitalize">{key.replace(/_/g, ' ')}</label>
                  {typeof value === 'object' && value.formula !== undefined ? (
                    <>
                      <textarea
                        defaultValue={value.formula || ''}
                        onChange={(e) => {
                          setExitForm({
                            ...exitForm,
                            parameters: {
                              ...exitForm?.parameters,
                              [key]: {
                                ...value,
                                formula: e.target.value
                              }
                            }
                          })
                        }}
                        className="w-full bg-slate-800 border border-slate-700 text-white px-2 py-1 rounded text-xs font-mono h-12"
                      />
                      {value.type && (
                        <div className="mt-1 text-xs text-slate-500">Type: {value.type}</div>
                      )}
                    </>
                  ) : (
                    <input
                      type="text"
                      defaultValue={value || ''}
                      onChange={(e) => {
                        setExitForm({
                          ...exitForm,
                          parameters: {
                            ...exitForm?.parameters,
                            [key]: e.target.value
                          }
                        })
                      }}
                      className="w-full bg-slate-800 border border-slate-700 text-white px-2 py-1 rounded text-xs"
                    />
                  )}
                  {typeof value === 'object' && value.description && (
                    <p className="text-slate-500 text-xs mt-1">{value.description}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            // Display View
            strategy.exit?.enabled ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 p-2 bg-red-900/20 rounded border border-red-800/50">
                  <span className="w-2 h-2 bg-red-400 rounded-full"></span>
                  <span className="text-red-400 font-medium">Exit Rules</span>
                </div>
                {strategy.exit.parameters && Object.entries(strategy.exit.parameters).map(([key, value]: [string, any]) => (
                  <div key={key}>
                    <p className="text-slate-400 text-xs uppercase mb-1 capitalize">{key.replace(/_/g, ' ')}</p>
                    <div className="text-slate-300 text-xs bg-slate-800/30 p-2 rounded font-mono break-all">
                      {typeof value === 'object' ? value.formula : value}
                    </div>
                    {typeof value === 'object' && value.description && (
                      <p className="text-slate-500 text-xs mt-1">{value.description}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-slate-400 text-sm">Not configured</div>
            )
          )}
        </div>
      </div>

      {/* Signals Configuration */}
      {strategy.signals?.enabled && (
        <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-white font-bold text-lg">Signal Weights</h3>
            <button
              onClick={() => {
                if (editingSignals) {
                  handleSaveSignals()
                } else {
                  setSignalsForm({
                    enabled: strategy.signals?.enabled || false,
                    weights: JSON.parse(JSON.stringify(strategy.signals?.weights || {})),
                    parameters: JSON.parse(JSON.stringify(strategy.signals?.parameters || {}))
                  })
                  setEditingSignals(true)
                }
              }}
              disabled={isSaving}
              className="text-purple-400 hover:text-purple-300 text-sm font-medium disabled:opacity-50"
            >
              {editingSignals ? (isSaving ? 'Saving...' : 'Done') : 'Edit'}
            </button>
          </div>

          {editingSignals ? (
            // Edit Form
            <div className="space-y-4">
              {Object.entries(strategy.signals.weights).map(([key, value]) => (
                <div key={key}>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-slate-400 text-xs uppercase capitalize">{key.replace(/_/g, ' ')}</label>
                    <span className="text-white font-medium text-sm">
                      {signalsForm?.weights?.[key] ? (signalsForm.weights[key] * 100).toFixed(1) : (value * 100).toFixed(1)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="1"
                    defaultValue={(value * 100).toString()}
                    onChange={(e) => {
                      setSignalsForm({
                        ...signalsForm,
                        weights: {
                          ...signalsForm?.weights,
                          [key]: parseInt(e.target.value) / 100
                        }
                      })
                    }}
                    className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                  />
                </div>
              ))}
              <div className="mt-4 p-3 bg-slate-800/50 rounded">
                <p className="text-slate-400 text-xs">
                  Total: <span className="text-slate-200 font-medium">
                    {(Object.values((signalsForm?.weights || strategy.signals.weights) as Record<string, number>).reduce((a: number, b: number) => a + b, 0) * 100).toFixed(1)}%
                  </span>
                </p>
              </div>
            </div>
          ) : (
            // Display View
            <div className="space-y-4">
              {Object.entries(strategy.signals.weights).map(([key, value]) => (
                <div key={key} className="bg-slate-800/50 rounded p-4 border border-slate-700/50">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-white font-semibold capitalize">{key.replace(/_/g, ' ')}</p>
                    <p className="text-purple-400 font-bold text-lg">{(value * 100).toFixed(0)}%</p>
                  </div>
                  {strategy.signals.parameters?.[key]?.description && (
                    <p className="text-slate-400 text-xs mb-2">{strategy.signals.parameters[key].description}</p>
                  )}
                  {strategy.signals.parameters?.[key]?.formula && (
                    <div className="bg-slate-900/50 rounded p-2 font-mono text-xs text-slate-300 break-all">
                      {strategy.signals.parameters[key].formula}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
