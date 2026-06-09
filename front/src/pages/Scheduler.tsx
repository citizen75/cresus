import { useState, useEffect } from 'react'
import { api } from '@/services/api'

interface CronJob {
  name: string
  description: string
  enabled: boolean
  schedule: string
  type: string
  target: string
  params: Record<string, any>
}

interface FormState {
  name: string
  schedule: string
  target: string
  type: 'flow' | 'agent'
  description: string
  params: string
  enabled: boolean
}

export default function Scheduler() {
  const [jobs, setJobs] = useState<CronJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingJob, setEditingJob] = useState<string | null>(null)
  const [formData, setFormData] = useState<FormState>({
    name: '',
    schedule: '',
    target: '',
    type: 'flow',
    description: '',
    params: '{}',
    enabled: false,
  })

  // Load jobs on mount
  useEffect(() => {
    loadJobs()
  }, [])

  const loadJobs = async () => {
    try {
      setLoading(true)
      const response = await api.listCronJobs()
      setJobs(response.jobs || [])
      setError(null)
    } catch (err) {
      setError('Failed to load scheduler jobs')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.currentTarget
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? (e.currentTarget as HTMLInputElement).checked : value,
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      // Parse params
      let params = {}
      if (formData.params.trim()) {
        params = JSON.parse(formData.params)
      }

      if (editingJob) {
        await api.updateCronJob(editingJob, {
          schedule: formData.schedule,
          target: formData.target,
          type: formData.type,
          description: formData.description,
          params,
          enabled: formData.enabled,
        })
      } else {
        await api.createCronJob({
          name: formData.name,
          schedule: formData.schedule,
          target: formData.target,
          job_type: formData.type,
          description: formData.description,
          params,
          enabled: formData.enabled,
        })
      }

      // Reset form and reload
      resetForm()
      await loadJobs()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save job')
      console.error(err)
    }
  }

  const handleEdit = (job: CronJob) => {
    setEditingJob(job.name)
    setFormData({
      name: job.name,
      schedule: job.schedule,
      target: job.target,
      type: job.type as 'flow' | 'agent',
      description: job.description,
      params: JSON.stringify(job.params || {}),
      enabled: job.enabled,
    })
    setShowForm(true)
  }

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete job '${name}'?`)) return

    try {
      await api.deleteCronJob(name)
      await loadJobs()
    } catch (err) {
      setError('Failed to delete job')
      console.error(err)
    }
  }

  const handleToggle = async (name: string, enabled: boolean) => {
    try {
      if (enabled) {
        await api.enableCronJob(name)
      } else {
        await api.disableCronJob(name)
      }
      await loadJobs()
    } catch (err) {
      setError('Failed to toggle job status')
      console.error(err)
    }
  }

  const handleRun = async (name: string) => {
    try {
      await api.runCronJob(name)
      setError(null)
      // Show success message briefly
      const msg = `Job '${name}' queued for execution`
      alert(msg)
    } catch (err) {
      setError('Failed to run job')
      console.error(err)
    }
  }

  const handleDuplicate = async (name: string) => {
    const newName = prompt(`Duplicate '${name}' as:`, `${name}_copy`)
    if (!newName) return

    try {
      await api.duplicateCronJob(name, newName)
      await loadJobs()
      setError(null)
    } catch (err) {
      setError('Failed to duplicate job')
      console.error(err)
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      schedule: '',
      target: '',
      type: 'flow',
      description: '',
      params: '{}',
      enabled: false,
    })
    setShowForm(false)
    setEditingJob(null)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Scheduler</h1>
          <p className="text-sm text-slate-400 mt-1">Manage cron jobs and scheduled tasks</p>
        </div>
        <button
          onClick={() => (showForm ? resetForm() : setShowForm(true))}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition"
        >
          {showForm ? 'Cancel' : '+ New Job'}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-900/20 border border-red-700 text-red-400 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Form */}
      {showForm && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            {editingJob ? 'Edit Job' : 'Create New Job'}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Name */}
              <div>
                <label className="block text-sm text-slate-300 mb-2">Job Name</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleFormChange}
                  disabled={!!editingJob}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500 disabled:opacity-50"
                  placeholder="e.g., daily_backup"
                  required
                />
              </div>

              {/* Schedule (with underscore hint) */}
              <div>
                <label className="block text-sm text-slate-300 mb-2">Schedule (Cron)</label>
                <input
                  type="text"
                  name="schedule"
                  value={formData.schedule}
                  onChange={handleFormChange}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                  placeholder="e.g., 0_10_*_*_*"
                  required
                />
                <p className="text-xs text-slate-500 mt-1">Use underscores for spaces: 0_10_*_*_*</p>
              </div>

              {/* Target */}
              <div>
                <label className="block text-sm text-slate-300 mb-2">Target</label>
                <input
                  type="text"
                  name="target"
                  value={formData.target}
                  onChange={handleFormChange}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                  placeholder="e.g., premarket"
                  required
                />
              </div>

              {/* Type */}
              <div>
                <label className="block text-sm text-slate-300 mb-2">Type</label>
                <select
                  name="type"
                  value={formData.type}
                  onChange={handleFormChange}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                >
                  <option value="flow">Flow</option>
                  <option value="agent">Agent</option>
                </select>
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm text-slate-300 mb-2">Description</label>
              <input
                type="text"
                name="description"
                value={formData.description}
                onChange={handleFormChange}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                placeholder="Optional description"
              />
            </div>

            {/* Parameters - Dynamic based on target */}
            <div className="bg-slate-800/50 border border-slate-700 rounded p-4">
              <label className="block text-sm text-slate-300 mb-3 font-semibold">Parameters</label>

              {formData.target === 'http' ? (
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
                    <label className="block text-xs text-slate-400 mb-1">URL</label>
                    <input
                      type="text"
                      value={(() => {
                        try {
                          const p = JSON.parse(formData.params)
                          return p.url || ''
                        } catch {
                          return ''
                        }
                      })()}
                      onChange={(e) => {
                        const p = JSON.parse(formData.params || '{}')
                        p.url = e.target.value
                        setFormData({ ...formData, params: JSON.stringify(p) })
                      }}
                      placeholder="http://localhost:8000/api/..."
                      className="w-full px-2 py-1 bg-slate-700 border border-slate-600 text-white rounded text-xs focus:outline-none focus:border-purple-500"
                    />
                  </div>
                </div>
              ) : formData.target === 'shell_exec' ? (
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Command</label>
                  <input
                    type="text"
                    value={(() => {
                      try {
                        const p = JSON.parse(formData.params)
                        return p.command || ''
                      } catch {
                        return ''
                      }
                    })()}
                    onChange={(e) => {
                      const p = JSON.parse(formData.params || '{}')
                      p.command = e.target.value
                      setFormData({ ...formData, params: JSON.stringify(p) })
                    }}
                    placeholder="cresus data fetch all --portfolio all"
                    className="w-full px-2 py-1 bg-slate-700 border border-slate-600 text-white rounded text-xs focus:outline-none focus:border-purple-500 font-mono"
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

            {/* Enabled */}
            <div className="flex items-center">
              <input
                type="checkbox"
                name="enabled"
                checked={formData.enabled}
                onChange={handleFormChange}
                className="w-4 h-4 rounded"
              />
              <label className="ml-2 text-sm text-slate-300">Enable job on creation</label>
            </div>

            {/* Buttons */}
            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition"
              >
                {editingJob ? 'Update' : 'Create'}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Jobs List */}
      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-12">
            <div className="text-slate-500">Loading jobs...</div>
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-12 bg-slate-900 border border-slate-800 rounded-lg">
            <div className="text-slate-500">No cron jobs configured</div>
          </div>
        ) : (
          jobs.map((job) => (
            <div key={job.name} className="bg-slate-900 border border-slate-800 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-white">{job.name}</h3>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${job.enabled ? 'bg-green-900/30 text-green-400' : 'bg-slate-800 text-slate-500'}`}>
                      {job.enabled ? '● Active' : '○ Inactive'}
                    </span>
                    <span className="px-2 py-1 rounded text-xs font-medium bg-slate-800 text-slate-300">
                      {job.type}
                    </span>
                  </div>
                  {job.description && <p className="text-sm text-slate-400 mt-2">{job.description}</p>}

                  <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <div className="text-slate-500">Schedule</div>
                      <div className="text-slate-300 font-mono">{job.schedule}</div>
                    </div>
                    <div>
                      <div className="text-slate-500">Target</div>
                      <div className="text-slate-300">{job.target}</div>
                    </div>
                    {Object.keys(job.params).length > 0 && (
                      <div>
                        <div className="text-slate-500">Parameters</div>
                        <div className="text-slate-300 font-mono text-xs">{JSON.stringify(job.params)}</div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 ml-4">
                  <button
                    onClick={() => handleRun(job.name)}
                    className="px-3 py-2 text-xs font-medium text-blue-400 hover:text-blue-300 rounded transition"
                    title="Run job immediately"
                  >
                    Run
                  </button>
                  <button
                    onClick={() => handleToggle(job.name, !job.enabled)}
                    className="px-3 py-2 text-xs font-medium rounded transition"
                    title={job.enabled ? 'Disable' : 'Enable'}
                  >
                    {job.enabled ? (
                      <span className="text-green-400 hover:text-green-300">✓ Enable</span>
                    ) : (
                      <span className="text-slate-500 hover:text-slate-400">✗ Disable</span>
                    )}
                  </button>
                  <button
                    onClick={() => handleDuplicate(job.name)}
                    className="px-3 py-2 text-xs font-medium text-cyan-400 hover:text-cyan-300 rounded transition"
                    title="Duplicate this job"
                  >
                    Copy
                  </button>
                  <button
                    onClick={() => handleEdit(job)}
                    className="px-3 py-2 text-xs font-medium text-purple-400 hover:text-purple-300 rounded transition"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(job.name)}
                    className="px-3 py-2 text-xs font-medium text-red-400 hover:text-red-300 rounded transition"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
