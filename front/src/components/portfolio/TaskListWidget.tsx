import { useState } from 'react'
import { api } from '@/services/api'
import { usePortfolioTasks } from '@/hooks/usePortfolio'

interface Task {
  id: number
  title: string
  description?: string
  priority: string
  due_date?: string
  status: string
  portfolio?: string
  ticker?: string
}

interface TaskListWidgetProps {
  portfolioName: string
}

function getPriorityColor(priority: string) {
  if (priority === 'High') return 'bg-red-900/30 text-red-300'
  if (priority === 'Low') return 'bg-green-900/30 text-green-300'
  return 'bg-yellow-900/30 text-yellow-300'
}

export default function TaskListWidget({ portfolioName }: TaskListWidgetProps) {
  const { data, isLoading, refetch } = usePortfolioTasks(portfolioName)
  const [newTitle, setNewTitle] = useState('')
  const [isAdding, setIsAdding] = useState(false)
  const [showDone, setShowDone] = useState(false)

  const tasks: Task[] = data?.tasks || []
  const filtered = tasks.filter((t) => (showDone ? true : t.status !== 'Done'))

  const handleAdd = async () => {
    const title = newTitle.trim()
    if (!title) return
    setIsAdding(true)
    try {
      await api.createTask({ title, portfolio: portfolioName, status: 'To-Do', priority: 'Medium' })
      setNewTitle('')
      refetch()
    } catch (err) {
      console.error('Failed to create task:', err)
    } finally {
      setIsAdding(false)
    }
  }

  const handleToggleDone = async (task: Task) => {
    const nextStatus = task.status === 'Done' ? 'To-Do' : 'Done'
    try {
      await api.updateTask(task.id, { ...task, status: nextStatus })
      refetch()
    } catch (err) {
      console.error('Failed to update task:', err)
    }
  }

  return (
    <div className="flex flex-col h-full bg-slate-900 border border-slate-800 rounded-lg overflow-hidden">
      <div className="border-b border-slate-800 flex-shrink-0 px-4 py-2 flex items-center justify-between gap-3">
        <h3 className="text-sm font-medium text-white">Tasks</h3>
        <button
          onClick={() => setShowDone(!showDone)}
          className="text-xs text-slate-400 hover:text-slate-300 transition"
        >
          {showDone ? 'Hide done' : 'Show done'}
        </button>
      </div>

      <div className="px-4 py-2 border-b border-slate-800 flex-shrink-0 flex gap-2">
        <input
          type="text"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleAdd()
          }}
          placeholder="Add a task..."
          className="flex-1 px-3 py-1.5 bg-slate-800 border border-slate-700 rounded text-white text-sm placeholder-slate-500 focus:outline-none focus:border-purple-600 transition"
        />
        <button
          onClick={handleAdd}
          disabled={isAdding || !newTitle.trim()}
          className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm font-medium transition disabled:opacity-50"
        >
          Add
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="text-center py-8 text-slate-400 text-sm">Loading tasks...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">No tasks for this portfolio</div>
        ) : (
          <ul className="divide-y divide-slate-800">
            {filtered.map((task) => (
              <li key={task.id} className="flex items-center gap-3 px-4 py-2 hover:bg-slate-800/30 transition">
                <input
                  type="checkbox"
                  checked={task.status === 'Done'}
                  onChange={() => handleToggleDone(task)}
                  className="w-4 h-4 rounded accent-purple-600 flex-shrink-0 cursor-pointer"
                />
                <span className={`flex-1 text-sm truncate ${task.status === 'Done' ? 'text-slate-500 line-through' : 'text-white'}`}>
                  {task.title}
                </span>
                {task.due_date && (
                  <span className="text-xs text-slate-500 flex-shrink-0">{task.due_date.slice(0, 10)}</span>
                )}
                <span className={`px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 ${getPriorityColor(task.priority)}`}>
                  {task.priority}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
