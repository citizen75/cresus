import { Link, useLocation } from 'react-router-dom'

interface LayoutProps {
  children: React.ReactNode
}

const menuItems = [
  { icon: '🏠', label: 'Home', path: '/' },
  { icon: '💼', label: 'Portfolios', path: '/portfolios' },
  { icon: '📊', label: 'Insights', path: '#' },
  { icon: '🔍', label: 'Explore', path: '#' },
  { icon: '🔖', label: 'Watchlist', path: '#' },
  { icon: '⚡', label: 'Simulator', path: '#' },
  { icon: '🔔', label: 'Alerts', path: '#' },
  { icon: '⚙️', label: 'Settings', path: '#' },
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  return (
    <div className="flex h-screen bg-slate-950">
      {/* Sidebar */}
      <aside className="w-56 bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 border-r border-slate-800 flex flex-col">
        {/* Logo */}
        <div className="px-6 py-8 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-violet-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-white font-bold">C</span>
            </div>
            <div>
              <div className="text-white font-bold text-base">CRESUS</div>
              <div className="text-xs text-slate-500">AI Capital</div>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-6 space-y-1 overflow-y-auto">
          {menuItems.map((item, index) => {
            const isActive = location.pathname === item.path
            return (
              <Link
                key={`${item.label}-${index}`}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition text-sm font-medium ${
                  isActive
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20'
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-300'
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>

        {/* Bottom Section */}
        <div className="px-3 py-6 border-t border-slate-800 space-y-4">
          <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition text-sm font-medium">
            <span>💬</span>
            <span>Ask Cresus</span>
          </button>
          <div className="px-4 py-2 text-center">
            <div className="text-xs text-slate-600">v1.0.0</div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-slate-950">
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
