import { useState, useEffect } from 'react'
import { getApiBaseUrl } from '@/services/api'
import DynamicSection from './DynamicSection'
import YAML from 'js-yaml'

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
  watchlist?: Record<string, any>
  signals?: Record<string, any>
  entry?: Record<string, any>
  exit?: Record<string, any>
  backtest?: Record<string, any>
  [key: string]: any
}

export default function StrategyBuilder({ name }: StrategyBuilderProps) {
  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isRawMode, setIsRawMode] = useState(false)
  const [rawFormat, setRawFormat] = useState<'json' | 'yaml'>('yaml')
  const [rawContent, setRawContent] = useState('')
  const [parseError, setParseError] = useState<string | null>(null)
  const [isSavingRaw, setIsSavingRaw] = useState(false)

  useEffect(() => {
    const fetchStrategy = async () => {
      try {
        const baseUrl = getApiBaseUrl()
        const strategyResponse = await fetch(`${baseUrl}/api/v1/strategies/${name}`)
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

  const saveStrategy = async (updates: any) => {
    if (!strategy) return false

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
    }
  }

  const handleRawOpen = () => {
    if (!strategy) return
    try {
      setRawContent(YAML.dump(strategy, { lineWidth: -1 }))
      setRawFormat('yaml')
    } catch {
      setRawContent(JSON.stringify(strategy, null, 2))
      setRawFormat('json')
    }
    setParseError(null)
    setIsRawMode(true)
  }

  const parseRawContent = (): Record<string, any> | null => {
    try {
      let parsed: any
      if (rawFormat === 'yaml') {
        parsed = YAML.load(rawContent)
      } else {
        parsed = JSON.parse(rawContent)
      }
      setParseError(null)
      return parsed
    } catch (err) {
      setParseError(err instanceof Error ? err.message : `Invalid ${rawFormat.toUpperCase()}`)
      return null
    }
  }

  const handleRawSave = async () => {
    const parsed = parseRawContent()
    if (!parsed) return

    setIsSavingRaw(true)
    try {
      const success = await saveStrategy(parsed)
      if (success) {
        setIsRawMode(false)
        setRawContent('')
      }
    } finally {
      setIsSavingRaw(false)
    }
  }

  const handleSaveSection = async (section: string, data: Record<string, any>) => {
    return saveStrategy({ [section]: data })
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

  const configSections = ['watchlist', 'signals', 'entry', 'exit', 'backtest']

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Strategy definition</h2>
          <p className="text-slate-400 text-sm mt-1">{strategy.description}</p>
        </div>
        <button
          onClick={handleRawOpen}
          className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition text-sm"
        >
          YAML/JSON
        </button>
      </div>

      {/* Strategy Status */}
      <div className="flex items-center gap-2 text-sm">
        <span className="w-2 h-2 bg-green-400 rounded-full"></span>
        <span className="text-green-400">Strategy active</span>
      </div>

      {/* Basic Info */}
      <DynamicSection
        title="Basic Info"
        data={{
          name: strategy.name,
          universe: strategy.universe,
          engine: strategy.engine,
          description: strategy.description,
          indicators: strategy.indicators || [],
          buy_conditions: strategy.buy_conditions,
          sell_conditions: strategy.sell_conditions,
        }}
        onSave={(data) =>
          handleSaveSection('basic', data).then((success) => {
            if (!success) throw new Error('Failed to save')
          })
        }
        preferYaml={true}
      />

      {/* Dynamic Config Sections */}
      {configSections.map((section) => {
        const data = strategy[section as keyof Strategy]
        if (!data) return null

        return (
          <DynamicSection
            key={section}
            title={section.charAt(0).toUpperCase() + section.slice(1)}
            data={data as Record<string, any>}
            onSave={(updatedData) =>
              handleSaveSection(section, updatedData).then((success) => {
                if (!success) throw new Error('Failed to save')
              })
            }
          />
        )
      })}

      {/* Raw Editor Modal */}
      {isRawMode && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 rounded-lg border border-slate-800 p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-white">Edit Strategy Configuration</h2>
              <button
                onClick={() => {
                  setIsRawMode(false)
                  setRawContent('')
                  setParseError(null)
                }}
                className="text-slate-400 hover:text-slate-300 text-2xl"
              >
                ✕
              </button>
            </div>

            <div className="flex gap-2 mb-4">
              <select
                value={rawFormat}
                onChange={(e) => {
                  const newFormat = e.target.value as 'json' | 'yaml'
                  setRawFormat(newFormat)
                  if (rawContent) {
                    try {
                      const parsed = rawFormat === 'yaml'
                        ? YAML.load(rawContent)
                        : JSON.parse(rawContent)

                      if (newFormat === 'yaml') {
                        setRawContent(YAML.dump(parsed as Record<string, any>, { lineWidth: -1 }))
                      } else {
                        setRawContent(JSON.stringify(parsed, null, 2))
                      }
                      setParseError(null)
                    } catch (err) {
                      setParseError(`Cannot convert: ${err instanceof Error ? err.message : 'Invalid format'}`)
                    }
                  }
                }}
                className="px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded font-medium"
              >
                <option value="json">JSON</option>
                <option value="yaml">YAML</option>
              </select>
              <div className="flex-1 text-slate-400 text-sm flex items-center">
                {rawFormat === 'yaml' ? '📋 YAML format' : '⚙️ JSON format'}
              </div>
            </div>

            <div className="space-y-3 mb-4">
              <textarea
                value={rawContent}
                onChange={(e) => {
                  setRawContent(e.target.value)
                  setParseError(null)
                }}
                className={`w-full bg-slate-800 border ${parseError ? 'border-red-600' : 'border-slate-700'} text-white rounded px-3 py-2 text-xs focus:border-purple-500 focus:outline-none font-mono h-96`}
                placeholder={`Paste ${rawFormat.toUpperCase()} here...`}
              />
              {parseError && (
                <div className="text-red-400 text-sm font-medium">
                  {parseError}
                </div>
              )}
            </div>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setIsRawMode(false)
                  setRawContent('')
                  setParseError(null)
                }}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded transition"
              >
                Cancel
              </button>
              <button
                onClick={handleRawSave}
                disabled={isSavingRaw || parseError !== null}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSavingRaw ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
