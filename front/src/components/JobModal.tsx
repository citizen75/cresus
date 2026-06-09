import { useState, useEffect } from 'react'

interface FormState {
  name: string
  schedule: string
  target: string
  type: 'http' | 'shell_exec' | 'flow' | 'agent'
  description: string
  params: string
  enabled: boolean
}

interface JobModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: FormState) => Promise<void>
  editingJob?: string | null
  initialData?: FormState
}

export function JobModal({ isOpen, onClose, onSubmit, editingJob, initialData }: JobModalProps) {
  const [formData, setFormData] = useState<FormState>({
    name: '',
    schedule: '',
    target: '',
    type: 'flow',
    description: '',
    params: '{}',
    enabled: false,
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (initialData) {
      setFormData(initialData)
    } else {
      setFormData({
        name: '',
        schedule: '',
        target: '',
        type: 'flow',
        description: '',
        params: '{}',
        enabled: false,
      })
    }
    setError(null)
  }, [initialData, isOpen])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.currentTarget
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? (e.currentTarget as HTMLInputElement).checked : value,
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      await onSubmit(formData)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save job')
    } finally {
      setSubmitting(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 rounded-lg border border-slate-800 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 sticky top-0 bg-slate-900">
          <h2 className="text-xl font-semibold text-white">
            {editingJob ? `Edit Job: ${editingJob}` : 'Create New Job'}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 text-2xl transition"
            title="Close"
          >
            ✕
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-4 bg-red-900/20 border border-red-700 text-red-400 rounded-lg text-sm">
              {error}
            </div>
          )}

          {/* Name & Type Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Name */}
            <div>
              <label className="block text-sm text-slate-300 mb-2 font-semibold">Job Name</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                disabled={!!editingJob}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500 disabled:opacity-50"
                placeholder="e.g., alert_sha_red"
                required
              />
            </div>

            {/* Type */}
            <div>
              <label className="block text-sm text-slate-300 mb-2 font-semibold">Job Type</label>
              <select
                name="type"
                value={formData.type}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
              >
                <option value="http">HTTP Request</option>
                <option value="shell_exec">Shell Command</option>
                <option value="flow">Flow</option>
                <option value="agent">Agent</option>
              </select>
            </div>
          </div>

          {/* Schedule & Target Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Schedule */}
            <div>
              <label className="block text-sm text-slate-300 mb-2 font-semibold">Schedule (Cron)</label>
              <input
                type="text"
                name="schedule"
                value={formData.schedule}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                placeholder="e.g., */30 9-18 * * 1-5"
                required
              />
              <p className="text-xs text-slate-500 mt-1">Use spaces (not underscores)</p>
            </div>

            {/* Target */}
            <div>
              <label className="block text-sm text-slate-300 mb-2 font-semibold">
                {formData.type === 'http' ? 'URL' : formData.type === 'shell_exec' ? 'Command' : 'Target'}
              </label>
              <input
                type="text"
                name="target"
                value={formData.target}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                placeholder={
                  formData.type === 'http'
                    ? 'http://localhost:8000/api/...'
                    : formData.type === 'shell_exec'
                      ? 'cresus data fetch all'
                      : 'premarket or strategy'
                }
                required
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm text-slate-300 mb-2 font-semibold">Description</label>
            <input
              type="text"
              name="description"
              value={formData.description}
              onChange={handleChange}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
              placeholder="Optional description of what this job does"
            />
          </div>

          {/* Parameters - Dynamic based on type */}
          <div className="bg-slate-800/50 border border-slate-700 rounded p-4">
            <label className="block text-sm text-slate-300 mb-3 font-semibold">
              {formData.type === 'http' ? 'HTTP Options' : formData.type === 'shell_exec' ? 'Shell Options' : 'Parameters'}
            </label>

            {formData.type === 'http' ? (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Method</label>
                  <select
                    value={(() => {
                      try {
                        const p = JSON.parse(formData.params)
                        return p.method || 'POST'
                      } catch {
                        return 'POST'
                      }
                    })()}
                    onChange={(e) => {
                      const p = JSON.parse(formData.params || '{}')
                      p.method = e.target.value
                      setFormData({ ...formData, params: JSON.stringify(p) })
                    }}
                    className="w-full px-2 py-1 bg-slate-700 border border-slate-600 text-white rounded text-xs"
                  >
                    <option>GET</option>
                    <option>POST</option>
                    <option>PUT</option>
                    <option>DELETE</option>
                    <option>PATCH</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Timeout (seconds)</label>
                  <input
                    type="number"
                    value={(() => {
                      try {
                        const p = JSON.parse(formData.params)
                        return p.timeout || 30
                      } catch {
                        return 30
                      }
                    })()}
                    onChange={(e) => {
                      const p = JSON.parse(formData.params || '{}')
                      p.timeout = parseInt(e.target.value)
                      setFormData({ ...formData, params: JSON.stringify(p) })
                    }}
                    className="w-full px-2 py-1 bg-slate-700 border border-slate-600 text-white rounded text-xs"
                    min="1"
                  />
                </div>
              </div>
            ) : formData.type === 'shell_exec' ? (
              <div>
                <label className="block text-xs text-slate-400 mb-1">Timeout (seconds)</label>
                <input
                  type="number"
                  value={(() => {
                    try {
                      const p = JSON.parse(formData.params)
                      return p.timeout || 300
                    } catch {
                      return 300
                    }
                  })()}
                  onChange={(e) => {
                    const p = JSON.parse(formData.params || '{}')
                    p.timeout = parseInt(e.target.value)
                    setFormData({ ...formData, params: JSON.stringify(p) })
                  }}
                  className="w-full px-2 py-1 bg-slate-700 border border-slate-600 text-white rounded text-xs"
                  min="1"
                />
              </div>
            ) : (
              <div>
                <label className="block text-xs text-slate-400 mb-1">Parameters (JSON)</label>
                <textarea
                  value={formData.params}
                  onChange={(e) => setFormData({ ...formData, params: e.target.value })}
                  className="w-full px-2 py-1 bg-slate-700 border border-slate-600 text-white rounded text-xs focus:outline-none focus:border-purple-500 font-mono"
                  placeholder='{}'
                  rows={3}
                />
              </div>
            )}
          </div>

          {/* Enabled Checkbox */}
          <div className="flex items-center gap-3 pt-2">
            <input
              type="checkbox"
              name="enabled"
              checked={formData.enabled}
              onChange={handleChange}
              className="w-4 h-4 rounded bg-slate-800 border border-slate-700 cursor-pointer"
            />
            <label className="text-sm text-slate-300 cursor-pointer">Enable job on creation</label>
          </div>

          {/* Buttons */}
          <div className="flex gap-3 pt-6 border-t border-slate-700">
            <button
              type="submit"
              disabled={submitting}
              className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? 'Saving...' : editingJob ? 'Update' : 'Create'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
