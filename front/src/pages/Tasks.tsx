import { useState, useEffect } from 'react'
import { api } from '@/services/api'

interface Task {
  id: number
  title: string
  description?: string
  priority: string
  due_date?: string
  status: string
  assignee?: string
  portfolio?: string
  ticker?: string
  tags?: string[]
  dependencies?: number[]
  checklist?: Array<{ text: string; done: boolean }>
  attachments?: Array<{ name: string; url: string }>
  created_at: string
  updated_at: string
}

interface TaskStats {
  total: number
  completed: number
  in_progress: number
  blocked: number
  high_priority: number
  completion_rate: number
}

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [stats, setStats] = useState<TaskStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [editingPanel, setEditingPanel] = useState(false)
  const [panelFormData, setPanelFormData] = useState({
    title: '',
    description: '',
    priority: 'Medium',
    due_date: '',
    status: 'To-Do',
    assignee: '',
    portfolio: '',
    ticker: '',
    tags: '',
  })

  const [filterStatus, setFilterStatus] = useState<string>('')
  const [filterPriority, setFilterPriority] = useState<string>('')
  const [filterPortfolio, setFilterPortfolio] = useState<string>('')
  const [portfolios, setPortfolios] = useState<string[]>([])
  const [searchQuery, setSearchQuery] = useState('')

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'Medium',
    due_date: '',
    status: 'To-Do',
    assignee: '',
    portfolio: '',
    ticker: '',
    tags: '',
  })

  useEffect(() => {
    loadTasks()
    loadStats()
    loadPortfolios()
  }, [filterStatus, filterPriority, filterPortfolio])

  useEffect(() => {
    if (selectedTask) {
      setPanelFormData({
        title: selectedTask.title,
        description: selectedTask.description || '',
        priority: selectedTask.priority,
        due_date: selectedTask.due_date || '',
        status: selectedTask.status,
        assignee: selectedTask.assignee || '',
        portfolio: selectedTask.portfolio || '',
        ticker: selectedTask.ticker || '',
        tags: selectedTask.tags?.join(', ') || '',
      })
      setEditingPanel(false)
    }
  }, [selectedTask])

  const loadTasks = async () => {
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams()
      if (filterStatus) params.append('status', filterStatus)
      if (filterPriority) params.append('priority', filterPriority)

      const response = await fetch(
        `http://192.168.0.130:6501/api/v1/tasks?${params.toString()}`
      )
      if (!response.ok) throw new Error('Failed to load tasks')

      const data = await response.json()
      const allTasks = data.tasks || []

      // Client-side filter by portfolio if selected
      const filteredTasks = filterPortfolio
        ? allTasks.filter((t: Task) => t.portfolio === filterPortfolio)
        : allTasks

      setTasks(filteredTasks)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks')
    } finally {
      setLoading(false)
    }
  }

  const loadPortfolios = async () => {
    try {
      const response = await fetch('http://192.168.0.130:6501/api/v1/portfolios')
      if (!response.ok) throw new Error('Failed to load portfolios')

      const data = await response.json()
      // Only show real portfolios (exclude special ones starting with _)
      const portfolioNames = (data.portfolios?.map((p: any) => p.name) || []).filter(
        (name: string) => !name.startsWith('_')
      )
      setPortfolios(portfolioNames)
    } catch (err) {
      console.error('Failed to load portfolios:', err)
    }
  }

  const loadStats = async () => {
    try {
      const response = await fetch('http://192.168.0.130:6501/api/v1/tasks/stats/overview')
      if (!response.ok) throw new Error('Failed to load stats')

      const data = await response.json()
      setStats(data.stats)
    } catch (err) {
      console.error('Failed to load stats:', err)
    }
  }

  const createOrUpdateTask = async () => {
    try {
      if (!formData.title) {
        setError('Title is required')
        return
      }

      const payload = {
        ...formData,
        tags: formData.tags ? formData.tags.split(',').map(t => t.trim()) : [],
      }

      const url = editingTask
        ? `http://192.168.0.130:6501/api/v1/tasks/${editingTask.id}`
        : 'http://192.168.0.130:6501/api/v1/tasks'

      const method = editingTask ? 'PUT' : 'POST'

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) throw new Error('Failed to save task')

      resetForm()
      loadTasks()
      loadStats()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save task')
    }
  }

  const savePanelEdits = async () => {
    if (!selectedTask) return

    try {
      const payload = {
        ...panelFormData,
        tags: panelFormData.tags ? panelFormData.tags.split(',').map(t => t.trim()) : [],
      }

      const response = await fetch(`http://192.168.0.130:6501/api/v1/tasks/${selectedTask.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) throw new Error('Failed to save task')

      setEditingPanel(false)
      loadTasks()
      setSelectedTask(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save task')
    }
  }

  const deleteTask = async (id: number) => {
    if (!confirm('Delete this task?')) return

    try {
      const response = await fetch(`http://192.168.0.130:6501/api/v1/tasks/${id}`, {
        method: 'DELETE',
      })

      if (!response.ok) throw new Error('Failed to delete task')

      loadTasks()
      loadStats()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete task')
    }
  }

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      priority: 'Medium',
      due_date: '',
      status: 'To-Do',
      assignee: '',
      portfolio: '',
      ticker: '',
      tags: '',
    })
    setEditingTask(null)
    setShowCreateModal(false)
  }

  const startEdit = (task: Task) => {
    setEditingTask(task)
    setFormData({
      title: task.title,
      description: task.description || '',
      priority: task.priority,
      due_date: task.due_date || '',
      status: task.status,
      assignee: task.assignee || '',
      portfolio: task.portfolio || '',
      ticker: task.ticker || '',
      tags: task.tags?.join(', ') || '',
    })
    setShowCreateModal(true)
  }

  const filteredTasks = tasks.filter(task =>
    task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    task.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'High':
        return 'bg-red-900/30 text-red-300'
      case 'Medium':
        return 'bg-yellow-900/30 text-yellow-300'
      case 'Low':
        return 'bg-green-900/30 text-green-300'
      default:
        return 'bg-slate-800 text-slate-300'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Done':
        return 'bg-green-900/30 text-green-300'
      case 'In Progress':
        return 'bg-blue-900/30 text-blue-300'
      case 'Blocked':
        return 'bg-red-900/30 text-red-300'
      default:
        return 'bg-slate-800 text-slate-300'
    }
  }

  return (
    <div className="flex-1 bg-slate-950 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
        <h1 className="text-2xl font-bold text-white">Tasks</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition"
        >
          + Create Task
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="px-6 py-4 border-b border-slate-800 grid grid-cols-6 gap-4">
          <div className="bg-slate-900 rounded p-3">
            <div className="text-xs text-slate-400">Total</div>
            <div className="text-2xl font-bold text-white mt-1">{stats.total}</div>
          </div>
          <div className="bg-slate-900 rounded p-3">
            <div className="text-xs text-slate-400">Completed</div>
            <div className="text-2xl font-bold text-green-400 mt-1">{stats.completed}</div>
          </div>
          <div className="bg-slate-900 rounded p-3">
            <div className="text-xs text-slate-400">In Progress</div>
            <div className="text-2xl font-bold text-blue-400 mt-1">{stats.in_progress}</div>
          </div>
          <div className="bg-slate-900 rounded p-3">
            <div className="text-xs text-slate-400">Blocked</div>
            <div className="text-2xl font-bold text-red-400 mt-1">{stats.blocked}</div>
          </div>
          <div className="bg-slate-900 rounded p-3">
            <div className="text-xs text-slate-400">High Priority</div>
            <div className="text-2xl font-bold text-red-400 mt-1">{stats.high_priority}</div>
          </div>
          <div className="bg-slate-900 rounded p-3">
            <div className="text-xs text-slate-400">Completion</div>
            <div className="text-2xl font-bold text-white mt-1">{stats.completion_rate.toFixed(0)}%</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="px-6 py-4 border-b border-slate-800 flex gap-4">
        <select
          value={filterPortfolio}
          onChange={(e) => setFilterPortfolio(e.target.value)}
          className="px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
        >
          <option value="">All Portfolios</option>
          {portfolios.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search tasks..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
        />
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
        >
          <option value="">All Status</option>
          <option value="To-Do">To-Do</option>
          <option value="In Progress">In Progress</option>
          <option value="Done">Done</option>
          <option value="Blocked">Blocked</option>
        </select>
        <select
          value={filterPriority}
          onChange={(e) => setFilterPriority(e.target.value)}
          className="px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
        >
          <option value="">All Priority</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
      </div>

      {/* Two Panel Layout */}
      <div className="flex-1 flex gap-4 px-6 py-4 overflow-hidden">
        {/* Left Panel: Task List */}
        <div className="flex-1 flex flex-col border-r border-slate-800">
          <div className="flex-1 overflow-y-auto pr-4">
        {error && (
          <div className="mb-4 p-4 bg-red-900/20 border border-red-800 text-red-400 rounded">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center h-full text-slate-400">
            Loading tasks...
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-400">
            No tasks found
          </div>
        ) : (
          <div className="space-y-3">
            {filteredTasks.map(task => (
              <div
                key={task.id}
                onClick={() => setSelectedTask(task)}
                className={`bg-slate-900 border rounded-lg p-4 transition cursor-pointer ${
                  selectedTask?.id === task.id
                    ? 'border-purple-500 bg-slate-800'
                    : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h3 className="font-semibold text-white">{task.title}</h3>
                    {task.description && (
                      <p className="text-sm text-slate-400 mt-1">{task.description}</p>
                    )}
                  </div>
                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => startEdit(task)}
                      className="px-3 py-1 bg-blue-600/20 text-blue-300 rounded text-sm hover:bg-blue-600/30 transition"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => deleteTask(task.id)}
                      className="px-3 py-1 bg-red-600/20 text-red-300 rounded text-sm hover:bg-red-600/30 transition"
                    >
                      Delete
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap mt-3">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(task.status)}`}>
                    {task.status}
                  </span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getPriorityColor(task.priority)}`}>
                    {task.priority}
                  </span>
                  {task.portfolio && (
                    <span className="px-2 py-1 bg-blue-900/30 text-blue-300 rounded text-xs">
                      💼 {task.portfolio}
                    </span>
                  )}
                  {task.ticker && (
                    <span className="px-2 py-1 bg-green-900/30 text-green-300 rounded text-xs">
                      📈 {task.ticker}
                    </span>
                  )}
                  {task.assignee && (
                    <span className="px-2 py-1 bg-purple-900/30 text-purple-300 rounded text-xs">
                      👤 {task.assignee}
                    </span>
                  )}
                  {task.due_date && (
                    <span className="px-2 py-1 bg-slate-800 text-slate-300 rounded text-xs">
                      📅 {new Date(task.due_date).toLocaleDateString()}
                    </span>
                  )}
                  {task.tags && task.tags.length > 0 && (
                    <div className="flex gap-1">
                      {task.tags.map(tag => (
                        <span key={tag} className="px-2 py-1 bg-slate-800 text-slate-300 rounded text-xs">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {task.checklist && task.checklist.length > 0 && (
                  <div className="mt-3 text-sm text-slate-400">
                    ✓ {task.checklist.filter(c => c.done).length}/{task.checklist.length} steps done
                  </div>
                )}
              </div>
            ))}
          </div>
          )}
          </div>
        </div>

        {/* Right Panel: Selected Task Details */}
        <div className="flex-1 overflow-y-auto">
          {selectedTask ? (
            <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
              {!editingPanel ? (
                <>
                  {/* Header */}
                  <div className="flex items-start justify-between mb-6">
                    <div className="flex-1">
                      <h2 className="text-2xl font-bold text-white mb-2">{selectedTask.title}</h2>
                      {selectedTask.portfolio && (
                        <p className="text-sm text-slate-400 mb-1">Portfolio: <span className="text-blue-400 font-medium">{selectedTask.portfolio}</span></p>
                      )}
                      {selectedTask.ticker && (
                        <p className="text-sm text-slate-400">Ticker: <span className="text-green-400 font-medium">{selectedTask.ticker}</span></p>
                      )}
                    </div>
                    <button
                      onClick={() => setEditingPanel(true)}
                      className="px-3 py-1 bg-blue-600/20 text-blue-300 rounded text-sm hover:bg-blue-600/30 transition"
                    >
                      Edit
                    </button>
                  </div>

              {/* Description */}
              {selectedTask.description && (
                <div className="mb-6 pb-6 border-b border-slate-700">
                  <h3 className="text-sm font-semibold text-slate-300 mb-2">Description</h3>
                  <p className="text-sm text-slate-400 whitespace-pre-wrap">{selectedTask.description}</p>
                </div>
              )}

              {/* Status & Priority */}
              <div className="grid grid-cols-2 gap-4 mb-6 pb-6 border-b border-slate-700">
                <div>
                  <p className="text-xs text-slate-500 mb-1">Status</p>
                  <span className={`px-3 py-1 rounded text-sm font-medium inline-block ${getStatusColor(selectedTask.status)}`}>
                    {selectedTask.status}
                  </span>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-1">Priority</p>
                  <span className={`px-3 py-1 rounded text-sm font-medium inline-block ${getPriorityColor(selectedTask.priority)}`}>
                    {selectedTask.priority}
                  </span>
                </div>
              </div>

              {/* Details */}
              <div className="grid grid-cols-2 gap-4 mb-6 pb-6 border-b border-slate-700">
                {selectedTask.due_date && (
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Due Date</p>
                    <p className="text-sm text-slate-300">📅 {new Date(selectedTask.due_date).toLocaleDateString()}</p>
                  </div>
                )}
                {selectedTask.assignee && (
                  <div>
                    <p className="text-xs text-slate-500 mb-1">Assignee</p>
                    <p className="text-sm text-slate-300">👤 {selectedTask.assignee}</p>
                  </div>
                )}
              </div>

              {/* Tags */}
              {selectedTask.tags && selectedTask.tags.length > 0 && (
                <div className="mb-6 pb-6 border-b border-slate-700">
                  <p className="text-xs text-slate-500 mb-2">Tags</p>
                  <div className="flex flex-wrap gap-2">
                    {selectedTask.tags.map(tag => (
                      <span key={tag} className="px-2 py-1 bg-slate-800 text-slate-300 rounded text-xs">
                        #{tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Checklist */}
              {selectedTask.checklist && selectedTask.checklist.length > 0 && (
                <div className="mb-6 pb-6 border-b border-slate-700">
                  <p className="text-xs text-slate-500 mb-2">Checklist</p>
                  <div className="space-y-2">
                    {selectedTask.checklist.map((item, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={item.done}
                          readOnly
                          className="w-4 h-4"
                        />
                        <span className={item.done ? 'text-slate-500 line-through' : 'text-slate-300'}>
                          {item.text}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Timestamps */}
              <div className="text-xs text-slate-500">
                <p>Created: {new Date(selectedTask.created_at).toLocaleString()}</p>
                <p>Updated: {new Date(selectedTask.updated_at).toLocaleString()}</p>
              </div>

              {/* Delete Button */}
              <button
                onClick={() => {
                  deleteTask(selectedTask.id)
                  setSelectedTask(null)
                }}
                className="mt-6 w-full px-4 py-2 bg-red-600/20 text-red-300 rounded text-sm hover:bg-red-600/30 transition font-medium"
              >
                Delete Task
              </button>
                </>
              ) : (
                <>
                  {/* Edit Mode */}
                  <h2 className="text-2xl font-bold text-white mb-6">Edit Task</h2>

                  <div className="space-y-4 max-h-[calc(100vh-300px)] overflow-y-auto">
                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Title</label>
                      <input
                        type="text"
                        value={panelFormData.title}
                        onChange={(e) => setPanelFormData({ ...panelFormData, title: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Description</label>
                      <textarea
                        value={panelFormData.description}
                        onChange={(e) => setPanelFormData({ ...panelFormData, description: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                        rows={3}
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm text-slate-400 mb-2">Priority</label>
                        <select
                          value={panelFormData.priority}
                          onChange={(e) => setPanelFormData({ ...panelFormData, priority: e.target.value })}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                        >
                          <option value="Low">Low</option>
                          <option value="Medium">Medium</option>
                          <option value="High">High</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm text-slate-400 mb-2">Status</label>
                        <select
                          value={panelFormData.status}
                          onChange={(e) => setPanelFormData({ ...panelFormData, status: e.target.value })}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                        >
                          <option value="To-Do">To-Do</option>
                          <option value="In Progress">In Progress</option>
                          <option value="Done">Done</option>
                          <option value="Blocked">Blocked</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Due Date</label>
                      <input
                        type="date"
                        value={panelFormData.due_date}
                        onChange={(e) => setPanelFormData({ ...panelFormData, due_date: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Assignee</label>
                      <input
                        type="text"
                        value={panelFormData.assignee}
                        onChange={(e) => setPanelFormData({ ...panelFormData, assignee: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                        placeholder="Name"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm text-slate-400 mb-2">Portfolio</label>
                        <select
                          value={panelFormData.portfolio || ''}
                          onChange={(e) => setPanelFormData({ ...panelFormData, portfolio: e.target.value })}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                        >
                          <option value="">None</option>
                          {portfolios.map((p) => (
                            <option key={p} value={p}>
                              {p}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm text-slate-400 mb-2">Ticker</label>
                        <input
                          type="text"
                          value={panelFormData.ticker || ''}
                          onChange={(e) => setPanelFormData({ ...panelFormData, ticker: e.target.value.toUpperCase() })}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                          placeholder="AAPL"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm text-slate-400 mb-2">Tags (comma-separated)</label>
                      <input
                        type="text"
                        value={panelFormData.tags}
                        onChange={(e) => setPanelFormData({ ...panelFormData, tags: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                        placeholder="urgent, project-x"
                      />
                    </div>
                  </div>

                  <div className="flex gap-3 mt-6 pt-6 border-t border-slate-700">
                    <button
                      onClick={savePanelEdits}
                      className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingPanel(false)}
                      className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition"
                    >
                      Cancel
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-500">
              <p>Select a task to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Create/Edit Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold text-white mb-4">
              {editingTask ? 'Edit Task' : 'Create Task'}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Title *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                  placeholder="Task title"
                />
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-2">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                  placeholder="Task description"
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Priority</label>
                  <select
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                  >
                    <option value="Low">Low</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-2">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                  >
                    <option value="To-Do">To-Do</option>
                    <option value="In Progress">In Progress</option>
                    <option value="Done">Done</option>
                    <option value="Blocked">Blocked</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-2">Due Date</label>
                <input
                  type="date"
                  value={formData.due_date}
                  onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-2">Assignee</label>
                <input
                  type="text"
                  value={formData.assignee}
                  onChange={(e) => setFormData({ ...formData, assignee: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                  placeholder="Name"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-2">Portfolio</label>
                  <select
                    value={formData.portfolio}
                    onChange={(e) => setFormData({ ...formData, portfolio: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                  >
                    <option value="">None</option>
                    {portfolios.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-2">Ticker</label>
                  <input
                    type="text"
                    value={formData.ticker}
                    onChange={(e) => setFormData({ ...formData, ticker: e.target.value.toUpperCase() })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                    placeholder="AAPL"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-2">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={formData.tags}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 text-white rounded text-sm focus:outline-none focus:border-purple-500"
                  placeholder="urgent, project-x"
                />
              </div>

              <div className="flex gap-3 pt-4 border-t border-slate-700">
                <button
                  onClick={createOrUpdateTask}
                  className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded font-medium transition"
                >
                  {editingTask ? 'Update' : 'Create'}
                </button>
                <button
                  onClick={resetForm}
                  className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded font-medium transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
