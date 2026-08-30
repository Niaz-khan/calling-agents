import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { Badge, Card, ErrorBox, Field, Loading, useFetch } from '../components/Ui'

function normalizeWidgetOrigin(value) {
  const cleaned = String(value).trim().replace(/\/+$/, '')
  if (/^https?:\/\//i.test(cleaned)) return cleaned
  return `https://${cleaned}`
}

const WIDGET_BASE = normalizeWidgetOrigin(
  import.meta.env.VITE_WIDGET_BASE_URL ||
    import.meta.env.VITE_API_BASE ||
    window.location.origin
)

export default function DeploymentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data, error, loading, reload } = useFetch(() => api.get(`/deployments/${id}`), [id])
  const agentsFetch = useFetch(() => api.get('/agents'), [])

  const [form, setForm] = useState(null)
  const [domains, setDomains] = useState([])
  const [dirty, setDirty] = useState(false)
  const [domainInput, setDomainInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [saved, setSaved] = useState(false)
  const [copied, setCopied] = useState(false)
  const copyTimer = useRef(null)

  useEffect(() => {
    if (!data) return
    setForm({
      agent_id: String(data.agent_id),
      name: data.name || '',
      widget_title: data.widget_title || '',
      widget_primary_color: data.widget_primary_color || '#4f46e5',
      welcome_message: data.welcome_message || '',
      enabled: data.enabled,
    })
    setDomains(data.allowed_domains || [])
    setDirty(false)
    setSaved(false)
  }, [data])

  useEffect(() => () => clearTimeout(copyTimer.current), [])

  if (loading) return <Loading />
  if (error) {
    return (
      <div>
        <p>
          <a href="#/deployments" onClick={() => navigate('/deployments')}>
            ← Deployments
          </a>
        </p>
        <ErrorBox message={error} onRetry={reload} />
      </div>
    )
  }
  if (!form) return <Loading />

  const deployment = data

  function patchForm(fields) {
    setDirty(true)
    setForm((previous) => ({ ...previous, ...fields }))
  }

  async function handleSave() {
    if (!form.agent_id) {
      setSaveError('Select an agent')
      return
    }
    setSaving(true)
    setSaveError('')
    try {
      await api.patch(`/deployments/${id}`, {
        agent_id: Number(form.agent_id),
        name: form.name.trim() || null,
        widget_title: form.widget_title.trim() || null,
        widget_primary_color: form.widget_primary_color.trim() || null,
        welcome_message: form.welcome_message.trim() || null,
        enabled: form.enabled,
        allowed_domains: domains
          .map((domain) => domain.trim().toLowerCase())
          .filter(Boolean),
      })
      setSaved(true)
      reload()
    } catch (err) {
      setSaveError(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  function addDomain() {
    const value = domainInput.trim().toLowerCase()
    if (!value || domains.includes(value)) return
    setDirty(true)
    setDomains([...domains, value])
    setDomainInput('')
  }

  function removeDomain(domain) {
    setDirty(true)
    setDomains(domains.filter((item) => item !== domain))
  }

  const snippet = `<script
  src="${WIDGET_BASE}/widget.js"
  data-agent="${deployment.public_identifier}"
></script>`

  async function copySnippet() {
    try {
      await navigator.clipboard.writeText(snippet)
    } catch {
      window.prompt('Copy the snippet manually:', snippet)
    }
    setCopied(true)
    clearTimeout(copyTimer.current)
    copyTimer.current = setTimeout(() => setCopied(false), 2000)
  }

  const color = form.widget_primary_color || '#4f46e5'

  return (
    <div>
      <p>
        <a href="#/deployments" onClick={() => navigate('/deployments')}>
          ← Deployments
        </a>
      </p>
      <div className="page-head">
        <h1>{deployment.name || deployment.widget_title || 'Deployment'}</h1>
        <div className="page-actions">
          <Badge variant={deployment.enabled ? 'success' : ''}>
            {deployment.enabled ? 'enabled' : 'disabled'}
          </Badge>
          <button className="btn primary" onClick={handleSave} disabled={saving || !dirty}>
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        </div>
      </div>

      {saveError && <div className="alert error">{saveError}</div>}
      {saved && <div className="alert">Changes saved.</div>}

      <div className="grid two">
        <Card title="General">
          <div className="form-grid">
            <Field label="Agent">
              <select
                className="input"
                value={form.agent_id}
                onChange={(event) => patchForm({ agent_id: event.target.value })}
              >
                {agentsFetch.loading && <option>Loading agents…</option>}
                {(agentsFetch.data || []).map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Display name">
              <input
                className="input"
                value={form.name}
                onChange={(event) => patchForm({ name: event.target.value })}
                placeholder="Main site"
              />
            </Field>
            <Field label="Public ID">
              <input className="input mono" value={deployment.public_identifier} readOnly />
            </Field>
            <Field label="Channel">
              <input className="input" value={deployment.channel} readOnly />
            </Field>
            <label className="check-row">
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(event) => patchForm({ enabled: event.target.checked })}
              />
              Enabled (visitors can chat)
            </label>
          </div>
        </Card>

        <Card title="Preview">
          <p className="muted snippet-hint">
            Branding preview only — it uses the same widget design and reflects title, color and
            welcome message.
          </p>
          <div className="widget-canvas">
            <div className="widget-preview" style={{ '--preview-primary': color }}>
              <button type="button" className="w-btn" aria-label="Chat">
                &#128172;
              </button>
              <div className="w-panel">
                <div className="w-head">
                  <span>{form.widget_title || deployment.agent_name || 'Chat with us'}</span>
                  <span className="w-close">&times;</span>
                </div>
                {form.welcome_message ? (
                  <div className="w-bubble assistant">{form.welcome_message}</div>
                ) : (
                  <div className="w-bubble assistant">Your welcome message will appear here.</div>
                )}
              </div>
            </div>
          </div>
        </Card>
      </div>

      <Card title="Branding">
        <div className="form-grid">
          <Field label="Widget title">
            <input
              className="input"
              value={form.widget_title}
              onChange={(event) => patchForm({ widget_title: event.target.value })}
              placeholder="Acme Support"
            />
          </Field>
          <Field label="Primary color">
            <div className="color-row">
              <input
                type="color"
                className="color-well"
                value={color}
                onChange={(event) => patchForm({ widget_primary_color: event.target.value })}
              />
              <input
                className="input"
                value={form.widget_primary_color}
                onChange={(event) => patchForm({ widget_primary_color: event.target.value })}
                placeholder="#4f46e5"
              />
            </div>
          </Field>
          <Field label="Welcome message">
            <textarea
              className="input"
              rows={4}
              value={form.welcome_message}
              onChange={(event) => patchForm({ welcome_message: event.target.value })}
              placeholder="Hi! Ask me about appointments."
            />
          </Field>
        </div>
      </Card>

      <Card title="Allowed domains">
        <p className="muted snippet-hint">
          Leave empty to allow any origin. When set, the widget only runs and chats from these
          exact hosts.
        </p>
        <div className="domain-editor">
          {domains.length === 0 ? (
            <span className="muted">No domain restrictions (all origins allowed).</span>
          ) : (
            domains.map((domain) => (
              <span className="domain-tag" key={domain}>
                {domain}
                <button
                  type="button"
                  className="domain-remove"
                  aria-label={`Remove ${domain}`}
                  onClick={() => removeDomain(domain)}
                >
                  &times;
                </button>
              </span>
            ))
          )}
        </div>
        <div className="form-row">
          <input
            className="input domain-input"
            value={domainInput}
            onChange={(event) => setDomainInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                addDomain()
              }
            }}
            placeholder="acme.com"
          />
          <button className="btn" type="button" onClick={addDomain}>
            Add domain
          </button>
        </div>
      </Card>

      <Card title="Installation">
        <p className="snippet-hint">
          Paste this code before the closing <code>&lt;/body&gt;</code> tag on your website. The
          chat button will appear bottom-right.
        </p>
        <div className="snippet-wrap">
          <pre className="snippet">
            <code>{snippet}</code>
          </pre>
          <button className={`btn primary small ${copied ? 'copied' : ''}`} onClick={copySnippet}>
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </Card>
    </div>
  )
}