import React from 'react'

/**
 * Simple markdown renderer for alert messages using regex replacement
 * Supports: bold (**text**), code (`text`), bullet points
 */
export function AlertMessageRenderer({ content }: { content: string }) {
  const lines = content.split('\n')

  return (
    <div className="text-slate-300 space-y-0.5">
      {lines.map((line, idx) => {
        if (!line.trim()) return <div key={idx} className="h-px" />
        return <Line key={idx} text={line} />
      })}
    </div>
  )
}

function Line({ text }: { text: string }) {
  // Process the line with regex replacements
  const parts: Array<{ type: 'text' | 'bold' | 'code' | 'bullet'; content: string | Array<string> }> = []

  // Split by patterns: **bold**, `code`, or bullet points
  let remaining = text
  let index = 0

  while (remaining.length > 0) {
    // Try to match bold
    const boldMatch = remaining.match(/^\*\*([^*]+)\*\*/)
    if (boldMatch) {
      if (index > 0 && parts[parts.length - 1]?.type === 'text') {
        parts[parts.length - 1].content = (parts[parts.length - 1].content as string) + boldMatch[0].substring(0, 0)
      }
      parts.push({ type: 'bold', content: boldMatch[1] })
      remaining = remaining.substring(boldMatch[0].length)
      continue
    }

    // Try to match code
    const codeMatch = remaining.match(/^`([^`]+)`/)
    if (codeMatch) {
      parts.push({ type: 'code', content: codeMatch[1] })
      remaining = remaining.substring(codeMatch[0].length)
      continue
    }

    // Try to match bullet
    const bulletMatch = remaining.match(/^•\s+([^:]+):\s+(.+)$/)
    if (bulletMatch) {
      parts.push({ type: 'bullet', content: [bulletMatch[1].trim(), bulletMatch[2]] })
      remaining = ''
      continue
    }

    // Regular text - consume until next markdown
    const nextMarkdown = remaining.search(/(\*\*|`|•\s+)/)
    if (nextMarkdown === -1) {
      parts.push({ type: 'text', content: remaining })
      remaining = ''
    } else {
      parts.push({ type: 'text', content: remaining.substring(0, nextMarkdown) })
      remaining = remaining.substring(nextMarkdown)
    }
  }

  return (
    <div className="text-sm leading-relaxed whitespace-normal">
      {parts.map((part, idx) => {
        switch (part.type) {
          case 'bold':
            return (
              <strong key={idx} className="font-bold text-white">
                {part.content}
              </strong>
            )
          case 'code':
            return (
              <code key={idx} className="bg-black/30 px-1 py-0.5 rounded text-xs font-mono text-slate-200 mx-0.5">
                {part.content}
              </code>
            )
          case 'bullet':
            const [ticker, info] = part.content as [string, string]
            return (
              <div key={idx} className="ml-2">
                <span className="text-yellow-400">•</span>
                <span className="font-bold text-purple-400 ml-1">{ticker}</span>
                <span className="text-slate-300">: {info}</span>
              </div>
            )
          default:
            return (
              <span key={idx} className="text-slate-300">
                {part.content}
              </span>
            )
        }
      })}
    </div>
  )
}
