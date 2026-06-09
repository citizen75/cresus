import { useState, useEffect } from 'react'
import { api } from '@/services/api'
import { JobModal } from '@/components/JobModal'

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
  type: 'http' | 'shell_exec' | 'flow' | 'agent'
  description: string
  params: string
  enabled: boolean
}

export default function Scheduler() {
  const [jobs, setJobs] = useState<CronJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
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

  const handleSubmit = async (submitData: FormState) => {
    try {
      // Parse params
      let params = {}
      if (submitData.params.trim()) {
        params = JSON.parse(submitData.params)
      }

      if (editingJob) {
        await api.updateCronJob(editingJob, {
          schedule: submitData.schedule,
          target: submitData.target,
          job_type: submitData.type,
          description: submitData.description,
          params,
          enabled: submitData.enabled,
        })
      } else {
        await api.createCronJob({
          name: submitData.name,
          schedule: submitData.schedule,
          target: submitData.target,
          job_type: submitData.type,
          description: submitData.description,
          params,
          enabled: submitData.enabled,
        })
      }

      // Reset form and reload
      resetForm()
      await loadJobs()
    } catch (err) {
      throw err
    }
  }

  const handleEdit = (job: CronJob) => {
    setEditingJob(job.name)
    setFormData({
      name: job.name,
      schedule: job.schedule,
      target: job.target,
      type: job.type as 'http' | 'shell_exec' | 'flow' | 'agent',
      description: job.description,
      params: JSON.stringify(job.params || {}),
      enabled: job.enabled,
    })
    setModalOpen(true)
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
      setError(null)
      // Fire-and-forget: start the job and return immediately
      api.runCronJob(name).catch((err) => {
        console.error(`Job '${name}' execution error:`, err)
        setError(`Job '${name}' failed to start`)
      })
      // Show success message immediately (before job completes)
      const msg = `Job '${name}' started (running in background)`
      alert(msg)
    } catch (err) {
      setError('Failed to start job')
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
    setModalOpen(false)
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
          onClick={() => setModalOpen(true)}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition"
        >
          + New Job
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-900/20 border border-red-700 text-red-400 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Form */}
      {/* Job Modal */}
      <JobModal
        isOpen={modalOpen}
        onClose={() => {
          setModalOpen(false)
          setEditingJob(null)
        }}
        onSubmit={handleSubmit}
        editingJob={editingJob}
        initialData={editingJob ? formData : undefined}
      />

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
