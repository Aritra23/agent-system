import { useState } from 'react'

const STEP_ICONS = {
  'Received': '📥',
  'Selected tool': '🔧',
  'Executing': '⚡',
  'Returning result': '📤',
  'Error': '⚠️',
  'Extracted': '🔍',
  'Operation': '⚙️',
  'Computed': '✓',
  'Identified': '🎯',
  'Found city': '📍',
  'Assembled': '📋',
  'Retry': '🔄',
  'Fallback': '↩️',
  'Parsed': '✅',
}

function getIcon(step) {
  for (const [key, icon] of Object.entries(STEP_ICONS)) {
    if (step.toLowerCase().includes(key.toLowerCase())) return icon
  }
  return '◦'
}

function getStepStyle(step) {
  const lower = step.toLowerCase()
  if (lower.includes('error')) return 'error'
  if (lower.includes('selected tool')) return 'selected'
  if (lower.includes('returning result')) return 'success'
  if (lower.includes('step 1') || lower.includes('received')) return 'input'
  return 'normal'
}

export default function TraceViewer({ steps, toolsUsed }) {
  const [collapsed, setCollapsed] = useState(false)

  if (!steps || steps.length === 0) return null

  return (
    <div style={styles.container}>
      <div style={styles.header} onClick={() => setCollapsed(!collapsed)}>
        <div style={styles.headerLeft}>
          <span style={styles.headerIcon}>⚡</span>
          <span style={styles.headerTitle}>EXECUTION TRACE</span>
          <span style={styles.stepCount}>{steps.length} steps</span>
        </div>
        <div style={styles.headerRight}>
          {toolsUsed && toolsUsed.length > 0 && (
            <div style={styles.tools}>
              {toolsUsed.map((t) => (
                <span key={t} style={styles.toolBadge}>{t}</span>
              ))}
            </div>
          )}
          <span style={styles.chevron}>{collapsed ? '▼' : '▲'}</span>
        </div>
      </div>

      {!collapsed && (
        <div style={styles.stepsContainer}>
          {steps.map((step, i) => {
            const kind = getStepStyle(step)
            const icon = getIcon(step)
            // Parse "Step N: content"
            const match = step.match(/^(Step \d+):\s*(.+)$/s)
            const label = match ? match[1] : null
            const content = match ? match[2] : step

            return (
              <div key={i} style={{ ...styles.step, ...stepVariants[kind] }} className="fade-in">
                <div style={styles.stepLeft}>
                  {label && <span style={styles.stepNumber}>{label}</span>}
                  <span style={styles.stepIcon}>{icon}</span>
                </div>
                <span style={styles.stepContent}>{content}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

const stepVariants = {
  normal: {},
  input: { borderLeft: '2px solid var(--text-muted)' },
  selected: { borderLeft: '2px solid var(--warn)', background: 'rgba(245,166,35,0.04)' },
  success: { borderLeft: '2px solid var(--accent)', background: 'var(--accent-glow)' },
  error: { borderLeft: '2px solid var(--error)', background: 'var(--error-glow)' },
}

const styles = {
  container: {
    background: 'var(--bg-panel)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    background: 'var(--bg-raised)',
    cursor: 'pointer',
    userSelect: 'none',
    borderBottom: '1px solid var(--border)',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  headerIcon: { fontSize: '14px' },
  headerTitle: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    letterSpacing: '0.15em',
    color: 'var(--accent)',
    fontWeight: 700,
  },
  stepCount: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-muted)',
    background: 'var(--bg)',
    padding: '2px 8px',
    borderRadius: '10px',
    border: '1px solid var(--border)',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  tools: {
    display: 'flex',
    gap: '6px',
  },
  toolBadge: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--warn)',
    background: 'rgba(245,166,35,0.1)',
    border: '1px solid rgba(245,166,35,0.3)',
    padding: '2px 8px',
    borderRadius: '3px',
    letterSpacing: '0.05em',
  },
  chevron: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--text-muted)',
  },
  stepsContainer: {
    padding: '4px 0',
  },
  step: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    padding: '8px 16px',
    borderLeft: '2px solid transparent',
    transition: 'background var(--transition)',
  },
  stepLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexShrink: 0,
    width: '90px',
  },
  stepNumber: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--text-muted)',
    letterSpacing: '0.05em',
    flexShrink: 0,
  },
  stepIcon: {
    fontSize: '12px',
  },
  stepContent: {
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    lineHeight: 1.5,
    wordBreak: 'break-word',
  },
}
