/**
 * Simple markdown renderer for alert messages
 * Converts: **text** → bold, `text` → code, • text: → bullet
 */
export function AlertMessageRenderer({ content }: { content: string }) {
  // Split content into paragraphs and lines
  const paragraphs = content.split('\n')

  return (
    <div style={{ color: '#cbd5e1', lineHeight: '1.25rem', fontSize: '0.875rem' }}>
      {paragraphs.map((line, idx) => (
        <div key={idx} style={{ wordBreak: 'break-word' }}>
          {renderMarkdown(line)}
        </div>
      ))}
    </div>
  )
}

function renderMarkdown(text: string) {
  if (!text.trim()) return null

  // Split by bold, code, and bullet patterns
  const parts: React.ReactNode[] = []
  let remaining = text
  let key = 0

  while (remaining.length > 0) {
    // Match bold: **text**
    const boldMatch = remaining.match(/\*\*([^*]*)\*\*/)
    if (boldMatch && boldMatch.index === 0) {
      parts.push(
        <strong key={key++} style={{ fontWeight: 'bold', color: '#ffffff' }}>
          {boldMatch[1]}
        </strong>
      )
      remaining = remaining.slice(boldMatch[0].length)
      continue
    }

    // Match code: `text`
    const codeMatch = remaining.match(/`([^`]*)`/)
    if (codeMatch && codeMatch.index === 0) {
      parts.push(
        <code key={key++} style={{
          backgroundColor: 'rgba(0, 0, 0, 0.3)',
          paddingLeft: '0.375rem',
          paddingRight: '0.375rem',
          paddingTop: '0.125rem',
          paddingBottom: '0.125rem',
          borderRadius: '0.25rem',
          fontSize: '0.75rem',
          fontFamily: 'monospace',
          color: '#cbd5e1'
        }}>
          {codeMatch[1]}
        </code>
      )
      remaining = remaining.slice(codeMatch[0].length)
      continue
    }

    // Match bullet: • text: info
    const bulletMatch = remaining.match(/^•\s+([^:]+):\s+(.+)/)
    if (bulletMatch) {
      parts.push(
        <div key={key++} style={{ marginLeft: '0.5rem', display: 'inline-block' }}>
          <span style={{ color: '#facc15' }}>•</span>
          <span style={{ fontWeight: 'bold', color: '#c084fc', marginLeft: '0.25rem' }}>{bulletMatch[1]}</span>
          <span>: {bulletMatch[2]}</span>
        </div>
      )
      remaining = ''
      continue
    }

    // Find next markdown token
    const boldIndex = remaining.search(/\*\*/)
    const codeIndex = remaining.search(/`/)
    const bulletIndex = remaining.search(/•/)

    const indices = [boldIndex, codeIndex, bulletIndex].filter((i) => i >= 0)
    const nextIndex = indices.length > 0 ? Math.min(...indices) : -1

    if (nextIndex === -1) {
      // No more markdown, add rest as text
      if (remaining) {
        parts.push(
          <span key={key++} style={{ color: '#cbd5e1' }}>
            {remaining}
          </span>
        )
      }
      remaining = ''
    } else {
      // Add text up to next markdown
      if (nextIndex > 0) {
        parts.push(
          <span key={key++} style={{ color: '#cbd5e1' }}>
            {remaining.slice(0, nextIndex)}
          </span>
        )
      }
      remaining = remaining.slice(nextIndex)
    }
  }

  return <>{parts}</>
}
