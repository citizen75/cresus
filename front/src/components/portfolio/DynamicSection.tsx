import { useState } from 'react'
import YAML from 'js-yaml'

interface DynamicSectionProps {
  title: string
  data: Record<string, any> | null
  onSave: (data: Record<string, any>) => Promise<void>
  preferYaml?: boolean
}

export default function DynamicSection({ title, data, onSave, preferYaml = false }: DynamicSectionProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [isRawMode, setIsRawMode] = useState(false)
  const [rawFormat, setRawFormat] = useState<'json' | 'yaml'>(preferYaml ? 'yaml' : 'json')
  const [formData, setFormData] = useState<Record<string, any> | null>(null)
  const [rawContent, setRawContent] = useState('')
  const [parseError, setParseError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const handleEdit = () => {
    if (!data) return
    setFormData(JSON.parse(JSON.stringify(data)))
    if (preferYaml) {
      try {
        setRawContent(YAML.dump(data, { lineWidth: -1 }))
        setRawFormat('yaml')
      } catch {
        setRawContent(JSON.stringify(data, null, 2))
        setRawFormat('json')
      }
    } else {
      setRawContent(JSON.stringify(data, null, 2))
      setRawFormat('json')
    }
    setParseError(null)
    setIsEditing(true)
    setIsRawMode(false)
  }

  const handleCancel = () => {
    setIsEditing(false)
    setIsRawMode(false)
    setFormData(null)
    setRawContent('')
    setParseError(null)
  }

  const handleSave = async () => {
    if (!formData) return
    setIsSaving(true)
    try {
      await onSave(formData)
      setIsEditing(false)
      setIsRawMode(false)
    } finally {
      setIsSaving(false)
    }
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

    setFormData(parsed)
    setIsSaving(true)
    try {
      await onSave(parsed)
      setIsEditing(false)
      setIsRawMode(false)
    } finally {
      setIsSaving(false)
    }
  }

  const renderField = (key: string, value: any, path: string = '') => {
    const fieldPath = path ? `${path}.${key}` : key
    const fieldValue = path ? getNestedValue(formData, path.split('.').concat(key)) : formData?.[key]

    if (value === null || value === undefined) {
      return (
        <div key={fieldPath} className="space-y-1">
          <label className="text-slate-400 text-xs uppercase block">{key}</label>
          <input
            type="text"
            value={fieldValue || ''}
            onChange={(e) => setNestedValue(fieldPath, e.target.value)}
            placeholder="null"
            className="w-full bg-slate-800 border border-slate-700 text-white rounded px-2 py-1 text-xs focus:border-purple-500 focus:outline-none"
          />
        </div>
      )
    }

    if (typeof value === 'boolean') {
      return (
        <div key={fieldPath} className="space-y-1">
          <label className="text-slate-400 text-xs uppercase block flex items-center gap-2">
            <input
              type="checkbox"
              checked={fieldValue || false}
              onChange={(e) => setNestedValue(fieldPath, e.target.checked)}
              className="w-4 h-4 rounded"
            />
            {key}
          </label>
        </div>
      )
    }

    if (typeof value === 'number') {
      return (
        <div key={fieldPath} className="space-y-1">
          <label className="text-slate-400 text-xs uppercase block">{key}</label>
          <input
            type="number"
            value={fieldValue || 0}
            onChange={(e) => setNestedValue(fieldPath, isNaN(parseFloat(e.target.value)) ? 0 : parseFloat(e.target.value))}
            className="w-full bg-slate-800 border border-slate-700 text-white rounded px-2 py-1 text-xs focus:border-purple-500 focus:outline-none"
          />
        </div>
      )
    }

    if (typeof value === 'string') {
      const isFormula = key.includes('formula') || key.includes('condition')
      return (
        <div key={fieldPath} className="space-y-1">
          <label className="text-slate-400 text-xs uppercase block">{key}</label>
          {isFormula ? (
            <textarea
              value={fieldValue || ''}
              onChange={(e) => setNestedValue(fieldPath, e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-white rounded px-2 py-1 text-xs focus:border-purple-500 focus:outline-none font-mono h-12"
            />
          ) : (
            <input
              type="text"
              value={fieldValue || ''}
              onChange={(e) => setNestedValue(fieldPath, e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-white rounded px-2 py-1 text-xs focus:border-purple-500 focus:outline-none"
            />
          )}
        </div>
      )
    }

    if (typeof value === 'object' && !Array.isArray(value)) {
      return (
        <div key={fieldPath} className="space-y-2 border border-slate-700 rounded p-3 bg-slate-800/30">
          <h5 className="text-slate-400 text-xs uppercase font-bold capitalize">{key}</h5>
          <div className="space-y-3 pl-2">
            {Object.entries(value).map(([subKey, subValue]) =>
              renderField(subKey, subValue, fieldPath)
            )}
          </div>
        </div>
      )
    }

    if (Array.isArray(value)) {
      return (
        <div key={fieldPath} className="space-y-1">
          <label className="text-slate-400 text-xs uppercase block">{key}</label>
          <textarea
            value={JSON.stringify(fieldValue || [], null, 2)}
            onChange={(e) => {
              try {
                setNestedValue(fieldPath, JSON.parse(e.target.value))
              } catch {
                // Keep raw text if not valid JSON
              }
            }}
            className="w-full bg-slate-800 border border-slate-700 text-white rounded px-2 py-1 text-xs focus:border-purple-500 focus:outline-none font-mono h-16"
          />
        </div>
      )
    }

    return null
  }

  const getNestedValue = (obj: any, path: string[]): any => {
    return path.reduce((acc, key) => acc?.[key], obj)
  }

  const setNestedValue = (path: string, value: any) => {
    const keys = path.split('.')
    const newForm = JSON.parse(JSON.stringify(formData))
    let current = newForm
    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) current[keys[i]] = {}
      current = current[keys[i]]
    }
    current[keys[keys.length - 1]] = value
    setFormData(newForm)
    if (rawFormat === 'yaml') {
      try {
        setRawContent(YAML.dump(newForm, { lineWidth: -1 }))
      } catch {
        setRawContent(JSON.stringify(newForm, null, 2))
      }
    } else {
      setRawContent(JSON.stringify(newForm, null, 2))
    }
  }

  return (
    <div className="bg-slate-900 rounded-lg p-6 border border-slate-800">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-bold">{title}</h3>
        <div className="flex items-center gap-2">
          {isEditing && (
            <>
              <button
                onClick={() => setIsRawMode(!isRawMode)}
                className="text-slate-400 hover:text-slate-300 text-xs font-medium transition"
              >
                {isRawMode ? '🎨 Form' : (rawFormat === 'yaml' ? 'YAML' : '{}JSON')}
              </button>
              {isRawMode && (
                <select
                  value={rawFormat}
                  onChange={(e) => {
                    const newFormat = e.target.value as 'json' | 'yaml'
                    setRawFormat(newFormat)
                    if (formData) {
                      if (newFormat === 'yaml') {
                        try {
                          setRawContent(YAML.dump(formData, { lineWidth: -1 }))
                        } catch {
                          setRawContent(JSON.stringify(formData, null, 2))
                        }
                      } else {
                        setRawContent(JSON.stringify(formData, null, 2))
                      }
                    }
                  }}
                  className="bg-slate-700 text-white border border-slate-600 rounded px-2 py-1 text-xs"
                >
                  <option value="json">JSON</option>
                  <option value="yaml">YAML</option>
                </select>
              )}
            </>
          )}
          <button
            onClick={() => {
              if (isEditing) {
                handleSave()
              } else {
                handleEdit()
              }
            }}
            disabled={isSaving}
            className="text-purple-400 hover:text-purple-300 text-sm font-medium disabled:opacity-50"
          >
            {isEditing ? (isSaving ? 'Saving...' : 'Done') : 'Edit'}
          </button>
        </div>
      </div>

      {isEditing ? (
        <div className="space-y-4">
          {isRawMode ? (
            <div className="space-y-2">
              <textarea
                value={rawContent}
                onChange={(e) => {
                  setRawContent(e.target.value)
                  setParseError(null)
                }}
                className={`w-full bg-slate-800 border ${parseError ? 'border-red-600' : 'border-slate-700'} text-white rounded px-3 py-2 text-xs focus:border-purple-500 focus:outline-none font-mono h-64`}
                placeholder={`Paste ${rawFormat.toUpperCase()} here...`}
              />
              {parseError && (
                <div className="text-red-400 text-xs">{parseError}</div>
              )}
              <div className="flex gap-2">
                <button
                  onClick={handleRawSave}
                  disabled={isSaving || parseError !== null}
                  className="flex-1 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium rounded transition disabled:opacity-50"
                >
                  {isSaving ? 'Saving...' : 'Save'}
                </button>
                <button
                  onClick={handleCancel}
                  className="flex-1 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="space-y-4">
                {formData && Object.entries(formData).map(([key, value]) =>
                  renderField(key, value)
                )}
              </div>
              <div className="flex gap-2 pt-4 border-t border-slate-700">
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="flex-1 px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium rounded transition disabled:opacity-50"
                >
                  {isSaving ? 'Saving...' : 'Save'}
                </button>
                <button
                  onClick={handleCancel}
                  className="flex-1 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium rounded transition"
                >
                  Cancel
                </button>
              </div>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-2 text-xs">
          {data && Object.keys(data).length > 0 ? (
            <div className="bg-slate-800/50 rounded p-3 font-mono text-slate-300 max-h-96 overflow-y-auto">
              <pre>{JSON.stringify(data, null, 2)}</pre>
            </div>
          ) : (
            <div className="text-slate-500 italic">No data configured</div>
          )}
        </div>
      )}
    </div>
  )
}
