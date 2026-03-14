export default function ToolsPanel({ tools }) {
  if (!tools || tools.length === 0) return null

  const icons = {
    TextProcessorTool: '📝',
    CalculatorTool: '🧮',
    WeatherMockTool: '🌤️',
  }

  return (
    <div style={styles.container}>
      <div style={styles.label}>AVAILABLE TOOLS</div>
      <div style={styles.list}>
        {tools.map((tool) => (
          <div key={tool.name} style={styles.tool}>
            <span style={styles.toolIcon}>{icons[tool.name] ?? '🔧'}</span>
            <div style={styles.toolInfo}>
              <span style={styles.toolName}>{tool.name}</span>
              <span style={styles.toolDesc}>{tool.description}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const styles = {
  container: {
    background: 'var(--bg-panel)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: '14px 16px',
  },
  label: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '0.15em',
    color: 'var(--text-muted)',
    marginBottom: '12px',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  tool: {
    display: 'flex',
    gap: '10px',
    alignItems: 'flex-start',
  },
  toolIcon: {
    fontSize: '16px',
    flexShrink: 0,
    marginTop: '1px',
  },
  toolInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  toolName: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--warn)',
    letterSpacing: '0.05em',
  },
  toolDesc: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--text-muted)',
    lineHeight: 1.5,
  },
}
