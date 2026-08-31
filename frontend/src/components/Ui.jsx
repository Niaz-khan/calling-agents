import { useCallback, useEffect, useRef, useState } from 'react'

/* ============================================================
   Data fetching
   ============================================================ */

export function useFetch(factory, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [reloadKey, setReloadKey] = useState(0)
  const factoryRef = useRef(factory)

  useEffect(() => {
    factoryRef.current = factory
  })

  useEffect(() => {
    let alive = true
    setState((previous) => ({ ...previous, loading: true, error: null }))

    factoryRef
      .current()
      .then((data) => {
        if (alive) setState({ data, error: null, loading: false })
      })
      .catch((error) => {
        if (alive) {
          setState({
            data: null,
            error: error.message || String(error),
            loading: false,
          })
        }
      })

    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey, ...(Array.isArray(deps) ? deps : [])])

  const reload = useCallback(() => setReloadKey((key) => key + 1), [])

  return { ...state, reload }
}

/* ============================================================
   Feedback states
   ============================================================ */

export function Loading() {
  return (
    <div className="empty-state">
      <Loader />
      <span className="muted">Loading…</span>
    </div>
  )
}

export function Loader({ size = 20 }) {
  return <span className="loader" style={{ width: size, height: size }} aria-hidden="true" />
}

export function ErrorBox({ message, onRetry }) {
  return (
    <div className="alert error">
      <span>{message}</span>
      {onRetry && (
        <Button className="small" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  )
}

export function Empty({ children, title, icon }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon || <span aria-hidden="true">•</span>}</div>
      <div className="empty-title">{title || children}</div>
      {children && title ? <div className="muted">{children}</div> : null}
    </div>
  )
}

export function Skeleton({ width = '100%', height = 14, style }) {
  return <div className="skeleton" style={{ width, height, ...style }} />
}

/* ============================================================
   Buttons
   ============================================================ */

export function Button({
  children,
  variant = '',
  size = '',
  loading = false,
  disabled,
  className = '',
  ...rest
}) {
  const classes = ['btn', variant, size, loading ? 'loading' : '', className]
    .filter(Boolean)
    .join(' ')
  return (
    <button className={classes} disabled={disabled || loading} {...rest}>
      {children}
    </button>
  )
}

/* ============================================================
   Badges / status indicators
   ============================================================ */

export function Badge({ variant, children, dot }) {
  if (dot) {
    return (
      <span className={`badge ${variant || ''}`}>
        <span className={`status-dot ${dot === 'pulse' ? 'pulse' : ''}`} />
        {children}
      </span>
    )
  }
  return <span className={`badge ${variant || ''}`}>{children}</span>
}

export function StatusIndicator({ status, label, pulse }) {
  const variant = statusVariant(status) || 'info'
  return (
    <Badge variant={variant} dot={pulse ? 'pulse' : ''}>
      {label || status}
    </Badge>
  )
}

/* ============================================================
   Cards
   ============================================================ */

export function Card({ title, children, className = '', bodyClassName = '', actions }) {
  return (
    <div className={`card ${className}`}>
      {title && (
        <div className="card-head">
          <span className="card-title">{title}</span>
          {actions && <div className="page-actions">{actions}</div>}
        </div>
      )}
      <div className={`card-body ${bodyClassName}`}>{children}</div>
    </div>
  )
}

export function StatCard({ label, value, variant, delta, icon }) {
  return (
    <Card className="stat">
      <div className="stat-label">
        <span>
          {icon && <span className="stat-icon">{icon}</span>}
          {label}
        </span>
        {variant && <Badge variant={variant}>{variant}</Badge>}
      </div>
      <div className="stat-value">{value}</div>
      {delta != null && <div className={`stat-delta ${delta < 0 ? 'down' : ''}`}>{delta}</div>}
    </Card>
  )
}

export function ChartCard({ title, subtitle, actions, children }) {
  return (
    <Card className="chart-card">
      <div className="chart-head">
        <div>
          <div className="ch-title">{title}</div>
          {subtitle && <div className="ch-sub">{subtitle}</div>}
        </div>
        {actions}
      </div>
      {children}
    </Card>
  )
}

/* ============================================================
   Page header / layout
   ============================================================ */

export function PageTitle({ title, subtitle, actions }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle && <div className="subtitle">{subtitle}</div>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  )
}

/* ============================================================
   Forms
   ============================================================ */

export function Field({ label, hint, children }) {
  return (
    <label className="field">
      {label && <span className="field-label">{label}</span>}
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  )
}

export function Input(props) {
  return <input className="input" {...props} />
}

export function Select({ children, className = '', ...rest }) {
  return (
    <select className={`input ${className}`} {...rest}>
      {children}
    </select>
  )
}

export function Textarea({ className = '', ...rest }) {
  return <textarea className={`input ${className}`} {...rest} />
}

/* ============================================================
   Modal
   ============================================================ */

export function Modal({ open, onClose, title, size = 'md', children }) {
  useEffect(() => {
    if (!open) return undefined
    const onKey = (event) => {
      if (event.key === 'Escape') onClose?.()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  useEffect(() => {
    if (!open) return undefined
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [open])

  if (!open) return null

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className={`modal ${size}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}

/* ============================================================
   Tabs
   ============================================================ */

export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((tab) => {
        const value = typeof tab === 'string' ? tab : tab.value
        const label = typeof tab === 'string' ? tab : tab.label
        return (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={active === value}
            className={`tab ${active === value ? 'active' : ''}`}
            onClick={() => onChange(value)}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}

export function Seg({ options, value, onChange }) {
  return (
    <div className="seg">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={value === option.value ? 'active' : ''}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

/* ============================================================
   Table
   ============================================================ */

export function Table({ columns, rows, rowKey = (row, index) => index, onRowClick, empty }) {
  if (!rows || rows.length === 0) {
    return <Empty>{empty || 'No records yet.'}</Empty>
  }
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr
              key={rowKey(row, index)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              style={onRowClick ? { cursor: 'pointer' } : undefined}
            >
              {columns.map((column) => (
                <td key={column.key}>{column.render ? column.render(row) : row[column.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ============================================================
   Toast
   ============================================================ */

let toastId = 0

export function toast(message, kind = '') {
  const event = new CustomEvent('app:toast', {
    detail: { id: ++toastId, message, kind },
  })
  window.dispatchEvent(event)
}

export function ToastStack() {
  const [items, setItems] = useState([])

  useEffect(() => {
    const onToast = (event) => {
      const item = event.detail
      setItems((previous) => [...previous, item])
      window.setTimeout(() => {
        setItems((previous) => previous.filter((entry) => entry.id !== item.id))
      }, 3600)
    }
    window.addEventListener('app:toast', onToast)
    return () => window.removeEventListener('app:toast', onToast)
  }, [])

  if (items.length === 0) return null
  return (
    <div className="toast-stack" role="status" aria-live="polite">
      {items.map((item) => (
        <div key={item.id} className="toast">
          <span className={`status-dot ${item.kind || 'pulse'}`} />
          {item.message}
        </div>
      ))}
    </div>
  )
}

/* ============================================================
   Code block + copy
   ============================================================ */

export function CodeBlock({ code }) {
  const [copied, setCopied] = useState(false)
  const timer = useRef(null)

  useEffect(() => () => clearTimeout(timer.current), [])

  async function copy() {
    try {
      await navigator.clipboard.writeText(code)
    } catch {
      window.prompt('Copy the code manually:', code)
    }
    setCopied(true)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="code-block">
      <pre className="snippet">
        <code>{code}</code>
      </pre>
      <button className={`copy-btn ${copied ? 'copied' : ''}`} onClick={copy}>
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  )
}

/* ============================================================
   Bar chart (lightweight, CSS bars)
   ============================================================ */

export function BarChart({ data, height = 180 }) {
  const max = Math.max(1, ...data.map((entry) => entry.count))
  return (
    <div className="bars" style={{ height }}>
      {data.map((entry) => (
        <div className="bar-col" key={entry.day} title={`${entry.day}: ${entry.count}`}>
          <div className="bar-track">
            <div
              className="bar"
              style={{
                height: entry.count === 0 ? 2 : `${Math.max(8, (entry.count / max) * 100)}%`,
              }}
            />
          </div>
          <span className="bar-day">{String(entry.day).slice(5)}</span>
        </div>
      ))}
    </div>
  )
}

/* ============================================================
   Helpers (kept for compatibility)
   ============================================================ */

export function statusVariant(status) {
  const map = {
    completed: 'success',
    scheduled: 'success',
    in_progress: 'info',
    ringing: 'warn',
    transferred: 'info',
    failed: 'danger',
    cancelled: 'danger',
    active: 'success',
    enabled: 'success',
    disabled: '',
  }
  return map[status] || ''
}

export function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatDay(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  if (minutes < 60) return `${minutes}m ${rest}s`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ${minutes % 60}m`
}

export function initials(name) {
  if (!name) return '?'
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}