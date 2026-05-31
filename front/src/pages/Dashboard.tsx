import { useState } from 'react'
import GlobalConversationPanel from '@/components/portfolio/GlobalConversationPanel'

export default function Dashboard() {
  const [conversationOpen, setConversationOpen] = useState(true)

  return (
    <div className="flex gap-6 h-[calc(100vh-120px)]">
      {/* Center Column - Conversations */}
      {conversationOpen && (
        <div className="w-[500px] flex-shrink-0">
          <GlobalConversationPanel onClose={() => setConversationOpen(false)} />
        </div>
      )}

      {/* Right Column - Chart */}
      <div className="flex-1 flex flex-col bg-slate-900 rounded-lg border border-slate-800">
        {/* Header */}
        <div className="px-4 py-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <span className="text-lg">📈</span>
            <h3 className="text-sm font-semibold text-white">Chart</h3>
          </div>
        </div>

        {/* Placeholder */}
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-slate-500">
            <div className="text-4xl mb-2">📌</div>
            <div className="text-xs">Reserved for future features</div>
          </div>
        </div>
      </div>
    </div>
  )
}
