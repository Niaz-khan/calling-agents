import { useCallback, useEffect, useRef, useState } from 'react'

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
  }, [reloadKey, ...deps])

  const reload = useCallback(() => setReloadKey((key) => key + 1), [])

  return { ...state, reload }
}

export function Loading() {
  return <div className="muted pad center">Loading…</div>
}

export function ErrorBox({ message, onRetry }) {
  return (
    <div className="alert error">
      <span>{message}</span>
      {onRetry && (
        <button className="btn small" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}

export function Empty({ children }) {
  return <div className="empty muted">{children}</div>
}

export function Badge({ variant, children }) {
  return <span className={`badge ${variant || ''}`}>{children}</span>
}

export function PageTitle({ title, actions }) {
  return (
    <div className="page-head">
      <h1>{title}</h1>
      <div className="page-actions">{actions}</div>
    </div>
  )
}

export function Card({ title, children, className = '' }) {
  return (
    <div className={`card ${className}`}>
      {title && <div className="card-head">{title}</div>}
      <div className="card-body">{children}</div>
    </div>
  )
}

export function Field({ label, children }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
    </label>
  )
}

export function statusVariant(status) {
  const map = {
    completed: 'success',
    scheduled: 'success',
    in_progress: 'info',
    ringing: 'warn',
    transferred: 'info',
    failed: 'danger',
    cancelled: 'danger',
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

export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  return `${minutes}m ${rest}s`
}