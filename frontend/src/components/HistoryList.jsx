import { useState } from 'react'

function formatTime(ts) {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleTimeString(undefined, {
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return ''
  }
}

function formatDate(ts) {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleDateString(undefined, {
      month: 'short', day: 'numeric',
    })
  } catch {
    return ''
  }
}

export default function HistoryList({ history, loading, onSelect, onDelete, selectedId }) {
  const [deletingId, setDeletingId] = useState(null)

  const handleDelete = async (e, id) => {
    e.stopPropagation()
    setDeletingId(id)
    await onDelete(id)
    setDeletingId(null)
  }

  if (loading) {
    return (
      <div style={styles.empty}>
        <span style={styles.emptyText}>Loading history…</span>
      </div>
    )
  }

  if (!history || history.length === 0) {
    return (
      <div style={styles.empty}>
        <span style={styles.emptyText}>No tasks yet</span>
        <span style={styles.emptyHint}>Past tasks will appear here</span>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      {history.map((item) => {
        const isSelected = item.id === selectedId
        const toolName = item.tools_used?.[0]?.replace('Tool', '') ?? '—'

        return (
          <div
            key={item.id}
            onClick={() => onSelect(item.id)}
            style={{
              ...styles.item,
              ...(isSelected ? styles.itemSelected : {}),
            }}
          >
            <div style={styles.itemLeft}>
              <span style={item.success ? styles.dot : styles.dotError} />
              <div style={styles.itemContent}>
                <span style={styles.itemTask}>{item.task}</span>
                <span style={styles.itemMeta}>{toolName} · {formatDate(item.timestamp)} {formatTime(item.timestamp)}</span>
              </div>
            </div>
            <button
              onClick={(e) => handleDelete(e, item.id)}
              disabled={deletingId === item.id}
              style={styles.deleteBtn}
              title="Delete"
            >
              {deletingId === item.id ? '…' : '✕'}
            </button>
          </div>
        )
      })}
    </div>
  )
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    overflowY: 'auto',
    maxHeight: '100%',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 20px',
    gap: '8px',
  },
  emptyText: {
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--text-muted)',
    letterSpacing: '0.1em',
  },
  emptyHint: {
    fontSize: '11px',
    color: 'var(--text-muted)',
    fontFamily: 'var(--font-mono)',
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 12px',
    borderRadius: 'var(--radius)',
    cursor: 'pointer',
    border: '1px solid transparent',
    transition: 'all var(--transition)',
    gap: '8px',
  },
  itemSelected: {
    background: 'var(--bg-hover)',
    border: '1px solid var(--border-bright)',
  },
  itemLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flex: 1,
    minWidth: 0,
  },
  dot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: 'var(--accent)',
    flexShrink: 0,
  },
  dotError: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: 'var(--error)',
    flexShrink: 0,
  },
  itemContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    minWidth: 0,
  },
  itemTask: {
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    color: 'var(--text-primary)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    maxWidth: '200px',
  },
  itemMeta: {
    fontFamily: 'var(--font-mono)',
    fontSize: '10px',
    color: 'var(--text-muted)',
    letterSpacing: '0.05em',
  },
  deleteBtn: {
    background: 'transparent',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    fontSize: '11px',
    padding: '4px 6px',
    borderRadius: 'var(--radius)',
    transition: 'color var(--transition)',
    flexShrink: 0,
    lineHeight: 1,
  },
}
