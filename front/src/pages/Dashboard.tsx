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

      {/* Right Column - Empty for now */}
      <div className="flex-1 bg-slate-900 rounded-lg border border-slate-800 flex items-center justify-center">
        <div className="text-center text-slate-500">
          <div className="text-3xl mb-2">📌</div>
          <p className="text-sm">Reserved for future features</p>
        </div>
      </div>
    </div>
  )
}
