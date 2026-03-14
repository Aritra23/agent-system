import { useState, useRef, useEffect } from 'react'

const EXAMPLES = [
  'uppercase "hello world"',
  '(3 + 5) * 12 / 4',
  'weather in Tokyo',
  'word count of "the quick brown fox jumped"',
  'sqrt(144)',
  'reverse "racecar"',
  'weather in New York',
  'palindrome check "A man a plan a canal Panama"',
  'base64 encode "hello world"'
]

export default function TaskInput({ onSubmit, loading }) {
  const [value, setValue] = useState('')
  const [exampleIdx, setExampleIdx] = useState(0)
  const textareaRef = useRef(null)

  useEffect(() => {
    const interval = setInterval(() => {
      setExampleIdx((i) => (i + 1) % EXAMPLES.length)
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleSubmit = () => {
    const trimmed = value.trim()
    if (!trimmed || loading) return
    onSubmit(trimmed)
    setValue('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit()
  }

  const handleExample = () => {
    setValue(EXAMPLES[exampleIdx])
    textareaRef.current?.focus()
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.label}>TASK INPUT</span>
        <span style={styles.hint}>⌘↵ to run</span>
      </div>

      <div style={styles.inputWrapper}>
        <span style={styles.prompt}>{'>'}</span>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Try: ${EXAMPLES[exampleIdx]}`}
          disabled={loading}
          rows={3}
          style={styles.textarea}
        />
      </div>

      <div style={styles.actions}>
        <button onClick={handleExample} style={styles.exampleBtn} disabled={loading}>
          USE EXAMPLE
        </button>
        <button
          onClick={handleSubmit}
          disabled={!value.trim() || loading}
          style={{
            ...styles.submitBtn,
            ...((!value.trim() || loading) ? styles.submitBtnDisabled : {}),
          }}
        >
          {loading ? (
            <span style={styles.loadingRow}>
              <span style={styles.spinner} />
              RUNNING…
            </span>
          ) : (
            <>RUN TASK <span style={styles.arrow}>→</span></>
          )}
        </button>
      </div>
    </div>
  )
}

const styles = {
  container: {
    background: 'var(--bg-panel)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  label: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    letterSpacing: '0.15em',
    color: 'var(--accent)',
    fontWeight: 700,
  },
  hint: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--text-muted)',
  },
  inputWrapper: {
    display: 'flex',
    gap: '10px',
    alignItems: 'flex-start',
    background: 'var(--bg)',
    border: '1px solid var(--border-bright)',
    borderRadius: 'var(--radius)',
    padding: '12px 14px',
    transition: 'border-color var(--transition)',
  },
  prompt: {
    fontFamily: 'var(--font-mono)',
    color: 'var(--accent)',
    fontSize: '16px',
    marginTop: '1px',
    userSelect: 'none',
    flexShrink: 0,
  },
  textarea: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
    fontSize: '14px',
    lineHeight: '1.6',
    resize: 'none',
    caretColor: 'var(--accent)',
  },
  actions: {
    display: 'flex',
    gap: '10px',
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  exampleBtn: {
    background: 'transparent',
    border: '1px solid var(--border-bright)',
    color: 'var(--text-secondary)',
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    letterSpacing: '0.1em',
    padding: '8px 14px',
    borderRadius: 'var(--radius)',
    cursor: 'pointer',
    transition: 'all var(--transition)',
  },
  submitBtn: {
    background: 'var(--accent)',
    border: '1px solid var(--accent)',
    color: '#0a0c0f',
    fontFamily: 'var(--font-mono)',
    fontSize: '12px',
    fontWeight: 700,
    letterSpacing: '0.12em',
    padding: '9px 20px',
    borderRadius: 'var(--radius)',
    cursor: 'pointer',
    transition: 'all var(--transition)',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  submitBtnDisabled: {
    opacity: 0.4,
    cursor: 'not-allowed',
  },
  arrow: {
    fontSize: '14px',
  },
  loadingRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  spinner: {
    width: '10px',
    height: '10px',
    border: '2px solid rgba(10,12,15,0.3)',
    borderTopColor: '#0a0c0f',
    borderRadius: '50%',
    display: 'inline-block',
    animation: 'spin 0.6s linear infinite',
  },
}
