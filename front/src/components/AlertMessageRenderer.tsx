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
          <div key={idx} className="text-sm leading-relaxed">
            {renderLineContent(line)}
          </div>
        )
      })}
    </div>
  )
}

function renderLineContent(line: string) {
  const parts: React.ReactNode[] = []
  let i = 0
  let buffer = ''
  let key = 0

  while (i < line.length) {
    // Check for bold (**text**)
    if (line[i] === '*' && line[i + 1] === '*') {
      // Flush buffer
      if (buffer) {
        parts.push(
          <span key={`text-${key++}`} className="text-slate-300">
            {buffer}
          </span>
        )
        buffer = ''
      }

      // Find closing **
      i += 2
      let boldText = ''
      while (i < line.length) {
        if (line[i] === '*' && line[i + 1] === '*') {
          parts.push(
            <span key={`bold-${key++}`} className="font-bold text-white">
              {boldText}
            </span>
          )
          i += 2
          break
        }
        boldText += line[i]
        i++
      }
    }
    // Check for code (`text`)
    else if (line[i] === '`') {
      // Flush buffer
      if (buffer) {
        parts.push(
          <span key={`text-${key++}`} className="text-slate-300">
            {buffer}
          </span>
        )
        buffer = ''
      }

      // Find closing `
      i += 1
      let codeText = ''
      while (i < line.length) {
        if (line[i] === '`') {
          parts.push(
            <code
              key={`code-${key++}`}
              className="bg-black/30 px-1.5 py-0.5 rounded text-xs font-mono text-slate-200"
            >
              {codeText}
            </code>
          )
          i += 1
          break
        }
        codeText += line[i]
        i++
      }
    }
    // Check for bullet point (•)
    else if (line[i] === '•') {
      // Flush buffer
      if (buffer) {
        parts.push(
          <span key={`text-${key++}`} className="text-slate-300">
            {buffer}
          </span>
        )
        buffer = ''
      }

      // Parse bullet point
      i += 1 // skip •
      while (i < line.length && line[i] === ' ') i++ // skip spaces

      // Get ticker
      let ticker = ''
      while (i < line.length && line[i] !== ':') {
        ticker += line[i]
        i++
      }

      // Skip colon and space
      if (line[i] === ':') i++
      while (i < line.length && line[i] === ' ') i++

      // Get rest of line
      let rest = ''
      while (i < line.length) {
        rest += line[i]
        i++
      }

      parts.push(
        <span key={`bullet-${key++}`} className="inline-flex items-baseline gap-1">
          <span className="text-yellow-400">•</span>
          <span className="font-bold text-purple-400">{ticker.trim()}</span>
          <span>{rest}</span>
        </span>
      )
    } else {
      buffer += line[i]
      i++
    }
  }

  // Flush remaining buffer
  if (buffer) {
    parts.push(
      <span key={`text-${key++}`} className="text-slate-300">
        {buffer}
      </span>
    )
  }

  return parts.length > 0 ? parts : [<span key="empty">{line}</span>]
}
