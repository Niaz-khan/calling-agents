import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import {
  Badge,
  Card,
  Empty,
  ErrorBox,
  Field,
  formatDate,
  PageTitle,
  useFetch,
} from '../components/Ui'

const CHANNEL_LABELS = { website: 'Website', api: 'API', phone: 'Phone', sms: 'SMS', whatsapp: 'WhatsApp' }

const emptyForm = {
  agent_id: '',
  channel: 'website',
  name: '',
  allowed_domains: '',
  widget_title: '',
  widget_primary_color: '#4f46e5',
  welcome_message: '',
  enabled: true,
}

function splitDomains(value) {
  return value
    .split(',')
    .map((part) => part.trim().toLowerCase())
    .filter(Boolean)
}

function toForm(deployment) {
  return {
    agent_id: String(deployment.agent_id),
    channel: deployment.channel,
    name: deployment.name || '',
    allowed_domains: (deployment.allowed_domains || []).join(', '),
    widget_title: deployment.widget_title || '',
    widget_primary_color: deployment.widget_primary_color || '#4f46e5',
    welcome_message: deployment.welcome_message || '',
    enabled: deployment.enabled,
  }
}

function fromForm(form, agents) {
  const agent = agents.find((item) => String(item.id) === String(form.agent_id))
  return {
    agent_id: agent ? agent.id : null,
    channel: form.channel,
    name: form.name.trim() || null,
    allowed_domains: splitDomains(form.allowed_domains),
    widget_title: form.widget_title.trim() || null,
    widget_primary_color: form.widget_primary_color.trim() || null,
    welcome_message: form.welcome_message.trim() || null,
    enabled: form.enabled,
  }
}

export default function Deployments() {
  const navigate = useNavigate()
  const { data, error, loading, reload } = useFetch(() => api.get('/deployments'), [])
  const agentsFetch = useFetch(() => api.get('/agents'), [])
  const deployments = data || []
  const agents = agentsFetch.data || []

  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState('')

  function startCreate() {
    setSaved('')
    setEditing(null)
    setForm(emptyForm)
    setFormError('')
    setShowForm(true)
  }

  function startEdit(deployment) {
    setSaved('')
    setEditing(deployment)
    setForm(toForm(deployment))
    setFormError('')
    setShowForm(true)
  }

  function cancel() {
    setShowForm(false)
    setEditing(null)
    setForm(emptyForm)
    setFormError('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSaving(true)
    setFormError('')
    try {
      const payload = fromForm(form, agents)
      if (!payload.agent_id) throw new Error('Select an agent')
      if (editing) {
        await api.patch(`/deployments/${editing.id}`, payload)
      } else {
        await api.post('/deployments', payload)
      }
      cancel()
      reload()
    } catch (err) {
      setFormError(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function toggleEnabled(deployment) {
    try {
      await api.patch(`/deployments/${deployment.id}`, {
        enabled: !deployment.enabled,
      })
      reload()
    } catch (err) {
      window.alert(err.message || 'Update failed')
    }
  }

  async function removeDeployment(deployment) {
    const label = deployment.name || CHANNEL_LABELS[deployment.channel]
    if (!window.confirm(`Delete ${label} deployment? This cannot be undone.`)) return
    try {
      await api.delete(`/deployments/${deployment.id}`)
      reload()
    } catch (err) {
      window.alert(err.message || 'Delete failed')
    }
  }

  const siteIsConfigurable = (deployment) =>
    deployment.channel === 'website' || deployment.channel === 'api'

  return (
    <div>
      <PageTitle
        title="Deployments"
        actions={
          !showForm && (
            <button className="btn primary" onClick={startCreate}>
              New deployment
            </button>
          )
        }
      />

      {showForm && (
        <Card title={editing ? `Edit: ${editing.name || CHANNEL_LABELS[editing.channel]}` : 'New deployment'}>
          {formError && <div className="alert error">{formError}</div>}
          <form className="form-grid" onSubmit={handleSubmit}>
            <Field label="Agent">
              <select
                className="input"
                value={form.agent_id}
                onChange={(event) => setForm({ ...form, agent_id: event.target.value })}
                required
              >
                <option value="">Select an agent…</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Channel">
              <select
                className="input"
                value={form.channel}
                onChange={(event) => setForm({ ...form, channel: event.target.value })}
              >
                <option value="website">Website</option>
                <option value="api">API</option>
              </select>
            </Field>
            <Field label="Display name (optional)">
              <input
                className="input"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                placeholder="Main site"
              />
            </Field>
            <Field label="Widget title">
              <input
                className="input"
                value={form.widget_title}
                onChange={(event) => setForm({ ...form, widget_title: event.target.value })}
                placeholder="Acme Support"
              />
            </Field>
            <Field label="Primary color">
              <div className="color-row">
                <input
                  type="color"
                  className="color-well"
                  value={form.widget_primary_color}
                  onChange={(event) => setForm({ ...form, widget_primary_color: event.target.value })}
                />
                <input
                  className="input"
                  value={form.widget_primary_color}
                  onChange={(event) => setForm({ ...form, widget_primary_color: event.target.value })}
                  placeholder="#4f46e5"
                />
              </div>
            </Field>
            <Field label="Allowed domains (comma separated, blank = all)">
              <input
                className="input"
                value={form.allowed_domains}
                onChange={(event) => setForm({ ...form, allowed_domains: event.target.value })}
                placeholder="acme.com, www.acme.com"
              />
            </Field>
            <Field label="Welcome message">
              <textarea
                className="input"
                rows={3}
                value={form.welcome_message}
                onChange={(event) => setForm({ ...form, welcome_message: event.target.value })}
                placeholder="Hi! Ask me about appointments."
              />
            </Field>
            <label className="check-row">
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(event) => setForm({ ...form, enabled: event.target.checked })}
              />
              Enabled (visitors can chat)
            </label>
            <div className="form-actions">
              <button className="btn primary" disabled={saving}>
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button className="btn" type="button" onClick={cancel}>
                Cancel
              </button>
            </div>
          </form>
        </Card>
      )}

      {saved && <div className="alert">{saved}</div>}

      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : loading ? (
        <Empty>Loading…</Empty>
      ) : deployments.length === 0 ? (
        <Empty>
          No deployments yet. Add a Website deployment to put an agent on your site.
        </Empty>
      ) : (
        <Card>
          <table className="table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Channel</th>
                <th>Status</th>
                <th>Public ID</th>
                <th>Allowed domains</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {deployments.map((deployment) => (
                <tr key={deployment.id}>
                  <td>{deployment.agent_name || '—'}</td>
                  <td>
                    <Badge variant="info">{CHANNEL_LABELS[deployment.channel] || deployment.channel}</Badge>
                  </td>
                  <td>
                    <Badge variant={deployment.enabled ? 'success' : ''}>
                      {deployment.enabled ? 'enabled' : 'disabled'}
                    </Badge>
                  </td>
                  <td className="mono muted" title={deployment.public_identifier}>
                    {deployment.public_identifier}
                  </td>
                  <td className="muted">
                    {deployment.allowed_domains && deployment.allowed_domains.length > 0 ? (
                      <span className="domain-list">
                        {deployment.allowed_domains.slice(0, 2).join(', ')}
                        {deployment.allowed_domains.length > 2 ? '…' : ''}
                      </span>
                    ) : (
                      'All'
                    )}
                  </td>
                  <td>{formatDate(deployment.created_at)}</td>
                  <td className="actions">
                    {siteIsConfigurable(deployment) && (
                      <button
                        className="btn small primary"
                        onClick={() => navigate(`/deployments/${deployment.id}`)}
                      >
                        Configure
                      </button>
                    )}
                    <button className="btn small" onClick={() => startEdit(deployment)}>
                      Edit
                    </button>
                    <button className="btn small" onClick={() => toggleEnabled(deployment)}>
                      {deployment.enabled ? 'Disable' : 'Enable'}
                    </button>
                    <button className="btn small danger" onClick={() => removeDeployment(deployment)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}