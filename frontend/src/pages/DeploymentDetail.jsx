import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { Badge, Card, Empty, ErrorBox, Field, Loading, useFetch } from '../components/Ui'

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

const DAYS = [
  { iso: 1, label: 'Monday' },
  { iso: 2, label: 'Tuesday' },
  { iso: 3, label: 'Wednesday' },
  { iso: 4, label: 'Thursday' },
  { iso: 5, label: 'Friday' },
  { iso: 6, label: 'Saturday' },
  { iso: 7, label: 'Sunday' },
]

const COMMON_TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Toronto',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Dubai',
  'Asia/Karachi',
  'Asia/Kolkata',
  'Asia/Singapore',
  'Asia/Tokyo',
  'Australia/Sydney',
]

function Stat({ label, value }) {
  return (
    <Card className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label muted">{label}</div>
    </Card>
  )
}

function AnalyticsSection({ deployment, analytics, days, setDays }) {
  if (!analytics) return null
  const maxCount = Math.max(
    1,
    ...analytics.conversations_by_day.map((entry) => entry.count)
  )
  return (
    <>
      <div className="stats-grid">
        <Stat label="Conversations" value={analytics.total_conversations} />
        <Stat label="Unique visitors" value={analytics.unique_visitors} />
        <Stat label="Messages" value={analytics.total_messages} />
        <Stat label="Appointments booked" value={analytics.appointments_booked} />
      </div>

      <Card
        title={`Conversations — last ${days} days`}
        className="analytics-chart"
      >
        <div className="card-toolbar">
          <div className="seg">
            <button
              type="button"
              className={days === 7 ? 'active' : ''}
              onClick={() => setDays(7)}
            >
              7 days
            </button>
            <button
              type="button"
              className={days === 30 ? 'active' : ''}
              onClick={() => setDays(30)}
            >
              30 days
            </button>
          </div>
        </div>
        {analytics.conversations_by_day.length === 0 ||
        analytics.conversations_by_day.every((entry) => entry.count === 0) ? (
          <Empty>No conversations in this period yet.</Empty>
        ) : (
          <div className="bars">
            {analytics.conversations_by_day.map((entry) => (
              <div
                className="bar-col"
                key={entry.day}
                title={`${entry.day}: ${entry.count}`}
              >
                <div className="bar-track">
                  <div
                    className="bar"
                    style={{
                      height: `${
                        entry.count === 0
                          ? 2
                          : Math.max(8, (entry.count / maxCount) * 100)
                      }%`,
                    }}
                  />
                </div>
                <span className="bar-day">{entry.day.slice(5)}</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="grid two">
        <Card title="Started recently">
          <ul className="breakdown">
            <li>
              <span>Today</span>
              <strong>{analytics.conversations_started.today}</strong>
            </li>
            <li>
              <span>This week</span>
              <strong>{analytics.conversations_started.this_week}</strong>
            </li>
            <li>
              <span>This month</span>
              <strong>{analytics.conversations_started.this_month}</strong>
            </li>
            <li>
              <span>Avg messages per conversation</span>
              <strong>{analytics.average_messages_per_conversation}</strong>
            </li>
          </ul>
        </Card>
        <Card title="Agent activity">
          <ul className="breakdown">
            <li>
              <span>Tool calls</span>
              <strong>{analytics.tool_calls}</strong>
            </li>
            <li>
              <span>Transfers to human</span>
              <strong>{analytics.transfers}</strong>
            </li>
            <li>
              <span>Timezone</span>
              <strong className="mono">{analytics.timezone}</strong>
            </li>
            <li>
              <span>Business name</span>
              <strong>{analytics.business_name}</strong>
            </li>
          </ul>
        </Card>
      </div>
      <p className="muted snippet-hint">
        Conversations across <strong>{deployment.channel}</strong> deployments are
        counted separately. Website visitors are de-duplicated by their visitor id.
      </p>
    </>
  )
}

function timesFromHours(hours) {
  const rows = {}
  for (const { iso } of DAYS) {
    const entry = hours ? hours[String(iso)] : undefined
    rows[iso] = {
      start: entry && entry.start ? entry.start : '',
      end: entry && entry.end ? entry.end : '',
      open: Boolean(entry && entry.start && entry.end),
    }
  }
  return rows
}

function BusinessHoursSection({ fetch }) {
  const { data, error, loading, reload } = fetch
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState('')

  useEffect(() => {
    if (!data) return
    setForm({
      business_name: data.business_name || '',
      timezone: data.timezone || 'UTC',
      contact_phone: data.contact_phone || '',
      website_url: data.website_url || '',
      address: data.address || '',
      days: timesFromHours(data.business_hours || {}),
    })
    setStatus('')
  }, [data])

  if (loading || !form) return <Loading />
  if (error) return <ErrorBox message={error} onRetry={reload} />

  function patchDay(iso, fields) {
    setForm((previous) => ({
      ...previous,
      days: { ...previous.days, [iso]: { ...previous.days[iso], ...fields } },
    }))
  }

  async function handleSave(event) {
    event.preventDefault()
    setSaving(true)
    setStatus('')
    const business_hours = {}
    for (const { iso } of DAYS) {
      const day = form.days[iso]
      if (day.open) {
        business_hours[String(iso)] = {
          start: day.start || '09:00',
          end: day.end || '17:00',
        }
      }
    }
    try {
      await api.patch('/business-config', {
        business_name: form.business_name.trim() || null,
        timezone: form.timezone.trim() || 'UTC',
        contact_phone: form.contact_phone.trim() || null,
        website_url: form.website_url.trim() || null,
        address: form.address.trim() || null,
        business_hours,
      })
      setStatus('Business settings saved. The online/offline status has been updated.')
      reload()
    } catch (err) {
      setStatus(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card title="Business & hours">
      <form onSubmit={handleSave}>
        <div className="form-grid">
          <Field label="Business name">
            <input
              className="input"
              value={form.business_name}
              onChange={(event) =>
                setForm({ ...form, business_name: event.target.value })
              }
              placeholder="Acme Dental"
            />
          </Field>
          <Field label="Timezone">
            <input
              className="input"
              list="timezone-options"
              value={form.timezone}
              onChange={(event) => setForm({ ...form, timezone: event.target.value })}
            />
            <datalist id="timezone-options">
              {COMMON_TIMEZONES.map((tz) => (
                <option key={tz} value={tz} />
              ))}
            </datalist>
          </Field>
          <Field label="Contact phone">
            <input
              className="input"
              value={form.contact_phone}
              onChange={(event) =>
                setForm({ ...form, contact_phone: event.target.value })
              }
              placeholder="+15551234567"
            />
          </Field>
          <Field label="Website URL">
            <input
              className="input"
              value={form.website_url}
              onChange={(event) =>
                setForm({ ...form, website_url: event.target.value })
              }
              placeholder="https://acme.example.com"
            />
          </Field>
          <Field label="Address">
            <input
              className="input"
              value={form.address}
              onChange={(event) => setForm({ ...form, address: event.target.value })}
              placeholder="123 Main St, Sydney"
            />
          </Field>
        </div>

        <h3 className="section-sub">Weekly business hours</h3>
        <p className="muted snippet-hint">
          These drive the online/offline badge shown to visitors. Empty days are
          closed; leaving every day empty means the business is always open.
        </p>
        <div className="hours-list">
          {DAYS.map(({ iso, label }) => {
            const day = form.days[iso]
            const disabled = !day.open
            return (
              <div className="hours-row" key={iso}>
                <span className="hours-day">{label}</span>
                <div className="hours-times">
                  <input
                    type="time"
                    className="input"
                    value={day.start}
                    disabled={disabled}
                    onChange={(event) =>
                      patchDay(iso, { start: event.target.value })
                    }
                  />
                  <span className="muted">to</span>
                  <input
                    type="time"
                    className="input"
                    value={day.end}
                    disabled={disabled}
                    onChange={(event) => patchDay(iso, { end: event.target.value })}
                  />
                </div>
                <label className="check-row hours-closed">
                  <input
                    type="checkbox"
                    checked={!day.open}
                    onChange={(event) => patchDay(iso, { open: !event.target.checked })}
                  />
                  Closed
                </label>
              </div>
            )
          })}
        </div>

        {status && (
          <div className={`alert ${status.includes('failed') || status.includes('error') ? 'error' : 'compact'}`}>
            {status}
          </div>
        )}
        <button className="btn primary" type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save business settings'}
        </button>
      </form>
    </Card>
  )
}

const EMPTY_SERVICE = () => ({
  id: null,
  name: '',
  description: '',
  duration_minutes: 30,
  price: '',
  currency: 'USD',
})

function ServicesSection({ fetch }) {
  const { data, error, loading, reload } = fetch
  const [serviceForm, setServiceForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState('')

  const form = serviceForm ? { ...EMPTY_SERVICE(), ...serviceForm } : EMPTY_SERVICE()

  if (loading) return <Loading />
  if (error) return <ErrorBox message={error} onRetry={reload} />

  function startEdit(service) {
    setServiceForm({
      id: service.id,
      name: service.name,
      description: service.description || '',
      duration_minutes: service.duration_minutes,
      price: service.price != null ? String(service.price) : '',
      currency: service.currency || 'USD',
    })
    setStatus('')
  }

  async function handleSave(event) {
    event.preventDefault()
    if (!form.name.trim() || !Number(form.duration_minutes)) {
      setStatus('Name and duration are required.')
      return
    }
    setSaving(true)
    setStatus('')
    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      duration_minutes: Number(form.duration_minutes),
      price: form.price.trim() ? String(form.price.trim()) : null,
      currency: form.currency.trim().toUpperCase() || 'USD',
    }
    try {
      if (form.id) {
        await api.patch(`/services/${form.id}`, payload)
        setStatus('Service updated.')
      } else {
        await api.post('/services', payload)
        setStatus('Service created.')
      }
      setServiceForm(null)
      reload()
    } catch (err) {
      setStatus(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(service) {
    setStatus('')
    try {
      await api.patch(`/services/${service.id}`, { active: !service.active })
      reload()
    } catch (err) {
      setStatus(err.message || 'Update failed')
    }
  }

  async function removeService(service) {
    setStatus('')
    if (!window.confirm(`Delete service "${service.name}"?`)) return
    try {
      await api.delete(`/services/${service.id}`)
      reload()
    } catch (err) {
      setStatus(err.message || 'Delete failed')
    }
  }

  const services = data || []

  return (
    <Card title="Services">
      <p className="muted snippet-hint">
        The AI agent lists these services to customers and uses each one&apos;s
        duration for availability checks and bookings. Prices are shown as set —
        the agent never invents them.
      </p>

      <form className="service-editor" onSubmit={handleSave}>
        <Field label="Name">
          <input
            className="input"
            value={form.name}
            onChange={(event) => setServiceForm({ ...form, name: event.target.value })}
            placeholder="Consultation"
          />
        </Field>
        <Field label="Duration (min)">
          <input
            className="input"
            type="number"
            min="1"
            value={form.duration_minutes}
            onChange={(event) =>
              setServiceForm({ ...form, duration_minutes: event.target.value })
            }
          />
        </Field>
        <Field label="Price">
          <input
            className="input"
            value={form.price}
            onChange={(event) => setServiceForm({ ...form, price: event.target.value })}
            placeholder="50.00"
          />
        </Field>
        <Field label="Currency">
          <input
            className="input"
            maxLength={3}
            value={form.currency}
            onChange={(event) => setServiceForm({ ...form, currency: event.target.value })}
          />
        </Field>
        <Field label="Description">
          <input
            className="input"
            value={form.description}
            onChange={(event) =>
              setServiceForm({ ...form, description: event.target.value })
            }
            placeholder="Dental consultation"
          />
        </Field>
        <div className="service-actions">
          <button className="btn primary" type="submit" disabled={saving}>
            {form.id ? 'Save changes' : 'Add service'}
          </button>
          {form.id && (
            <button
              className="btn"
              type="button"
              onClick={() => {
                setServiceForm(null)
                setStatus('')
              }}
            >
              Cancel
            </button>
          )}
        </div>
      </form>

      {services.length === 0 ? (
        <Empty>No services yet. Add one above.</Empty>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Dur.</th>
              <th>Price</th>
              <th>Active</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {services.map((service) => (
              <tr key={service.id}>
                <td>
                  {service.name}
                  {service.description && (
                    <div className="muted small">{service.description}</div>
                  )}
                </td>
                <td>{service.duration_minutes} min</td>
                <td>
                  {service.price != null
                    ? `${service.currency} ${service.price}`
                    : '—'}
                </td>
                <td>
                  <button
                    type="button"
                    className="btn small"
                    onClick={() => toggleActive(service)}
                  >
                    {service.active ? 'Active' : 'Disabled'}
                  </button>
                </td>
                <td>
                  <div className="actions">
                    <button className="btn small" type="button" onClick={() => startEdit(service)}>
                      Edit
                    </button>
                    <button
                      className="btn small danger"
                      type="button"
                      onClick={() => removeService(service)}
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {status && (
        <div className={`alert compact ${status.includes('failed') || status.includes('error') ? 'error' : ''}`}>
          {status}
        </div>
      )}
    </Card>
  )
}

export default function DeploymentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data, error, loading, reload } = useFetch(() => api.get(`/deployments/${id}`), [id])
  const agentsFetch = useFetch(() => api.get('/agents'), [])
  const [days, setDays] = useState(7)
  const analyticsFetch = useFetch(
    () => api.get(`/deployments/${id}/analytics?days=${days}`),
    [id, days]
  )
  const businessFetch = useFetch(() => api.get('/business-config'), [])
  const servicesFetch = useFetch(() => api.get('/services'), [])

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
      analyticsFetch.reload()
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
          {!analyticsFetch.loading && analyticsFetch.data && (
            <Badge variant={analyticsFetch.data.online ? 'success' : 'danger'}>
              {analyticsFetch.data.online ? (
                <span className="presence">
                  <span className="presence-dot" /> online
                </span>
              ) : (
                'offline'
              )}
            </Badge>
          )}
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

      <AnalyticsSection
        deployment={deployment}
        analytics={analyticsFetch.data}
        days={days}
        setDays={setDays}
      />

      <BusinessHoursSection fetch={businessFetch} />

      <ServicesSection fetch={servicesFetch} />

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