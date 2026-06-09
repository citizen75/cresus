/**
 * Simple markdown renderer for alert messages
 * Supports: bold (**text**), code (`text`), emoji, line breaks
 */
export function AlertMessageRenderer({ content }: { content: string }) {
  // Split by lines
  const lines = content.split('\n')

  return (
    <div className="text-slate-300 space-y-1">
      {lines.map((line, idx) => {
        // Skip empty lines but preserve spacing
        if (line.trim() === '') {
          return <div key={idx} className="h-1" />
        }

        // Render line with markdown parsing
        return (
          <div key={idx} className="flex flex-wrap gap-1 items-baseline">
            {renderLineContent(line)}
          </div>
        )
      })}
    </div>
  )
}

function renderLineContent(line: string) {
  const parts: React.ReactNode[] = []
  let currentPos = 0

  // Better regex to match: bold (**text**), code (`text`), or bullet points
  const regex = /\*\*([^*]+)\*\*|`([^`]+)`|•\s+([^:]+):\s+(.+?)(?=•|$)|([^*`•]+)/g
  let match

  while ((match = regex.exec(line)) !== null) {
    if (match[1]) {
      // Bold text
      parts.push(
        <span key={`bold-${match.index}`} className="font-bold text-white">
          {match[1]}
        </span>
      )
    } else if (match[2]) {
      // Code text
      parts.push(
        <code
          key={`code-${match.index}`}
          className="bg-black/30 px-1.5 py-0.5 rounded text-xs font-mono text-slate-200"
        >
          {match[2]}
        </code>
      )
    } else if (match[3]) {
      // Bullet point - highlight ticker
      parts.push(
        <span key={`bullet-${match.index}`}>
          <span className="text-yellow-400">•</span>
          <span className="font-bold text-purple-400 ml-1">{match[3]}</span>
          <span>: {match[4]}</span>
        </span>
      )
    } else if (match[5]) {
      // Regular text
      const text = match[5].trim()
      if (text) {
        parts.push(
          <span key={`text-${match.index}`} className="text-slate-300">
            {text}
          </span>
        )
      }
    }
  }

  return parts.length > 0 ? parts : [<span key="empty">{line}</span>]
}
