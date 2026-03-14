import TraceViewer from './TraceViewer'

function formatTimestamp(ts) {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleString(undefined, {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    })
  } catch {
    return ts
  }
}

function formatOutput(output) {
  if (output === null || output === undefined) return null
  if (typeof output === 'string') return output
  return JSON.stringify(output, null, 2)
}

export default function ResultPanel({ result }) {
  if (!result) {
    return (
      <div style={styles.empty}>
        <div style={styles.emptyIcon}>◌</div>
        <div style={styles.emptyText}>No result yet</div>
        <div style={styles.emptyHint}>Submit a task to see the output here</div>
      </div>
    )
  }

  const hasError = !!result.error
  const outputText = hasError ? result.error : formatOutput(result.output)

  return (
    <div style={styles.container} className="fade-in">
      {/* Meta row */}
      <div style={styles.meta}>
        <div style={styles.metaLeft}>
          <span style={styles.taskLabel}>TASK</span>
          <span style={styles.taskText}>{result.task}</span>
        </div>
        <div style={styles.metaRight}>
          {result.id && (
            <span style={styles.taskId}>#{result.id}</span>
          )}
          <span style={styles.timestamp}>{formatTimestamp(result.timestamp)}</span>
        </div>
      </div>

      {/* Status */}
      <div style={styles.statusRow}>
        <span style={hasError ? styles.statusError : styles.statusSuccess}>
          {hasError ? '✗ ERROR' : '✓ SUCCESS'}
        </span>
        {result.tools_used && result.tools_used.length > 0 && (
          <div style={styles.toolsRow}>
            {result.tools_used.map((t) => (
              <span key={t} style={styles.toolChip}>{t}</span>
            ))}
          </div>
        )}
      </div>

      {/* Output box */}
      <div style={{ ...styles.outputBox, ...(hasError ? styles.outputBoxError : {}) }}>
        <div style={styles.outputLabel}>OUTPUT</div>
        <pre style={styles.outputText}>{outputText}</pre>
      </div>

      {/* Trace */}
      {result.steps && result.steps.length > 0 && (
        <TraceViewer steps={result.steps} toolsUsed={result.tools_used} />
      )}
    </div>
  )
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    gap: '10px',
    background: 'var(--bg-panel)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    minHeight: '200px',
  },
  emptyIcon: {
    fontSize: '36px',
    color: 'var(--text-muted)',
    lineHeight: 1,
  },
  emptyText: {
    fontFamily: 'var(--font-mono)',
    fontSize: '13px',
    color: 'var(--text-muted)',
    letterSpacing: '0.1em',
  },
  emptyHint: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
  },
  meta: {
    background: 'var(--bg-panel)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: '14px 16px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '16px',
  },
  metaLeft: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    flex: 1,
    minWidth: 0,
  },
  taskLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '0.15em',
    color: 'var(--text-muted)',
  },
  taskText: {
    fontFamily: 'var(--font-mono)',
    fontSize: '13px',
    color: 'var(--text-primary)',
    wordBreak: 'break-word',
  },
  metaRight: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: '4px',
    flexShrink: 0,
  },
  taskId: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--accent)',
    letterSpacing: '0.1em',
  },
  timestamp: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--text-muted)',
  },
  statusRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap',
  },
  statusSuccess: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    fontWeight: 700,
    letterSpacing: '0.1em',
    color: 'var(--accent)',
    background: 'var(--accent-glow)',
    border: '1px solid rgba(0,229,160,0.3)',
    padding: '3px 10px',
    borderRadius: '3px',
  },
  statusError: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    fontWeight: 700,
    letterSpacing: '0.1em',
    color: 'var(--error)',
    background: 'var(--error-glow)',
    border: '1px solid rgba(255,71,87,0.3)',
    padding: '3px 10px',
    borderRadius: '3px',
  },
  toolsRow: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
  },
  toolChip: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--warn)',
    background: 'rgba(245,166,35,0.08)',
    border: '1px solid rgba(245,166,35,0.25)',
    padding: '3px 9px',
    borderRadius: '3px',
    letterSpacing: '0.05em',
  },
  outputBox: {
    background: 'var(--bg)',
    border: '1px solid var(--border-bright)',
    borderRadius: 'var(--radius-lg)',
    padding: '16px',
    position: 'relative',
  },
  outputBoxError: {
    border: '1px solid rgba(255,71,87,0.3)',
    background: 'var(--error-glow)',
  },
  outputLabel: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '0.15em',
    color: 'var(--text-muted)',
    marginBottom: '10px',
  },
  outputText: {
    fontFamily: 'var(--font-mono)',
    fontSize: '14px',
    color: 'var(--text-primary)',
    lineHeight: '1.7',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    margin: 0,
  },
}
