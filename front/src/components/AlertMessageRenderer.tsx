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

  // Regex to match: bold (**text**), code (`text`), or bullet points
  const regex = /(\*\*[^*]+\*\*|`[^`]+`|•\s+[^:]+:|[^*`•]+)/g
  let match

  while ((match = regex.exec(line)) !== null) {
    const text = match[0]

    if (text.startsWith('**') && text.endsWith('**')) {
      // Bold text
      const boldText = text.slice(2, -2)
      parts.push(
        <span key={`bold-${match.index}`} className="font-bold text-white">
          {boldText}
        </span>
      )
    } else if (text.startsWith('`') && text.endsWith('`')) {
      // Code text
      const codeText = text.slice(1, -1)
      parts.push(
        <code
          key={`code-${match.index}`}
          className="bg-black/30 px-1.5 py-0.5 rounded text-xs font-mono text-slate-200"
        >
          {codeText}
        </code>
      )
    } else if (text.startsWith('•')) {
      // Bullet point - highlight ticker
      const parts2 = text.split(':')
      const ticker = parts2[0].replace('•', '').trim()
      const rest = parts2.slice(1).join(':')

      parts.push(
        <span key={`bullet-${match.index}`}>
          <span className="text-yellow-400">•</span>
          <span className="font-bold text-purple-400 ml-1">{ticker}</span>
          <span>{rest}</span>
        </span>
      )
    } else {
      // Regular text
      parts.push(
        <span key={`text-${match.index}`} className="text-slate-300">
          {text}
        </span>
      )
    }
  }

  return parts
}
