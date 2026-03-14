import { useState, useEffect, useCallback } from 'react'
import { api } from './api'
import TaskInput from './components/TaskInput'
import ResultPanel from './components/ResultPanel'
import HistoryList from './components/HistoryList'
import ToolsPanel from './components/ToolsPanel'

export default function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [tools, setTools] = useState([])
  const [error, setError] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [status, setStatus] = useState(null) // 'online' | 'offline'

  // Load history + tools on mount
  useEffect(() => {
    loadHistory()
    api.listTools().then((d) => setTools(d.tools)).catch(() => {})
    api.health()
      .then(() => setStatus('online'))
      .catch(() => setStatus('offline'))
  }, [])

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true)
    try {
      const data = await api.listTasks(50)
      setHistory(data)
    } catch {
      // silently fail
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  const handleSubmit = async (task) => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.runTask(task)
      setResult(data)
      setSelectedId(data.id)
      setHistory((prev) => [
        { id: data.id, task: data.task, tools_used: data.tools_used, timestamp: data.timestamp, success: !data.error },
        ...prev,
      ])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectHistory = async (id) => {
    if (id === selectedId) return
    setSelectedId(id)
    try {
      const data = await api.getTask(id)
      setResult(data)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDelete = async (id) => {
    try {
      await api.deleteTask(id)
      setHistory((prev) => prev.filter((h) => h.id !== id))
      if (selectedId === id) {
        setResult(null)
        setSelectedId(null)
      }
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div style={styles.root}>
      {/* Noise overlay */}
      <div style={styles.noise} />

      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.logo}>
            <span style={styles.logoBracket}>[</span>
            <span style={styles.logoText}>AGENT</span>
            <span style={styles.logoBracket}>]</span>
          </div>
          <span style={styles.headerSub}>Intelligent Task Runner</span>
        </div>
        <div style={styles.headerRight}>
          <span style={{
            ...styles.statusDot,
            background: status === 'online' ? 'var(--accent)' : status === 'offline' ? 'var(--error)' : 'var(--text-muted)',
            boxShadow: status === 'online' ? '0 0 8px var(--accent)' : 'none',
          }} />
          <span style={styles.statusText}>
            {status === 'online' ? 'API ONLINE' : status === 'offline' ? 'API OFFLINE' : 'CONNECTING…'}
          </span>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div style={styles.errorBanner}>
          <span style={styles.errorIcon}>⚠</span>
          <span style={styles.errorText}>{error}</span>
          <button onClick={() => setError(null)} style={styles.errorDismiss}>✕</button>
        </div>
      )}

      {/* Main layout */}
      <main style={styles.main}>
        {/* Left sidebar */}
        <aside style={styles.sidebar}>
          <div style={styles.sidebarSection}>
            <div style={styles.sectionHeader}>
              <span style={styles.sectionTitle}>HISTORY</span>
              <span style={styles.sectionCount}>{history.length}</span>
            </div>
            <div style={styles.historyContainer}>
              <HistoryList
                history={history}
                loading={historyLoading}
                onSelect={handleSelectHistory}
                onDelete={handleDelete}
                selectedId={selectedId}
              />
            </div>
          </div>
          <div style={styles.sidebarDivider} />
          <div style={styles.sidebarSection}>
            <ToolsPanel tools={tools} />
          </div>
        </aside>

        {/* Main content */}
        <div style={styles.content}>
          <TaskInput onSubmit={handleSubmit} loading={loading} />
          <div style={styles.resultWrapper}>
            <ResultPanel result={result} />
          </div>
        </div>
      </main>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        button:hover:not(:disabled) {
          opacity: 0.85;
        }
        textarea::placeholder {
          color: var(--text-muted);
        }
      `}</style>
    </div>
  )
}

const styles = {
  root: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    overflow: 'hidden',
  },
  noise: {
    position: 'fixed',
    inset: 0,
    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E")`,
    pointerEvents: 'none',
    zIndex: 0,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 28px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg-panel)',
    position: 'relative',
    zIndex: 10,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '2px',
  },
  logoBracket: {
    fontFamily: 'var(--font-mono)',
    fontSize: '20px',
    color: 'var(--accent)',
    fontWeight: 700,
  },
  logoText: {
    fontFamily: 'var(--font-sans)',
    fontSize: '18px',
    fontWeight: 800,
    letterSpacing: '0.2em',
    color: 'var(--text-primary)',
  },
  headerSub: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-muted)',
    letterSpacing: '0.1em',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  statusDot: {
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    display: 'inline-block',
    transition: 'all 0.3s ease',
  },
  statusText: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '0.12em',
    color: 'var(--text-muted)',
  },
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 28px',
    background: 'var(--error-glow)',
    borderBottom: '1px solid rgba(255,71,87,0.3)',
    position: 'relative',
    zIndex: 10,
  },
  errorIcon: {
    color: 'var(--error)',
    fontSize: '14px',
  },
  errorText: {
    flex: 1,
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--error)',
  },
  errorDismiss: {
    background: 'transparent',
    border: 'none',
    color: 'var(--error)',
    cursor: 'pointer',
    fontSize: '12px',
    padding: '2px 6px',
  },
  main: {
    flex: 1,
    display: 'flex',
    overflow: 'hidden',
    position: 'relative',
    zIndex: 1,
  },
  sidebar: {
    width: '280px',
    flexShrink: 0,
    borderRight: '1px solid var(--border)',
    background: 'var(--bg-panel)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  sidebarSection: {
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    minHeight: 0,
  },
  sidebarDivider: {
    height: '1px',
    background: 'var(--border)',
    flexShrink: 0,
  },
  sectionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionTitle: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    letterSpacing: '0.15em',
    color: 'var(--text-muted)',
  },
  sectionCount: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--text-muted)',
    background: 'var(--bg-raised)',
    padding: '1px 7px',
    borderRadius: '10px',
    border: '1px solid var(--border)',
  },
  historyContainer: {
    flex: 1,
    overflowY: 'auto',
    minHeight: '100px',
    maxHeight: '340px',
  },
  content: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    padding: '24px 28px',
    overflowY: 'auto',
  },
  resultWrapper: {
    flex: 1,
  },
}
