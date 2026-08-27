import { useState } from 'react'
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

const emptyForm = { name: '', description: '', system_prompt: '' }

export default function Agents() {
  const fetchAgents = () => api.get('/agents')
  const { data, error, loading, reload } = useFetch(fetchAgents, [])
  const agents = data || []

  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  function startCreate() {
    setEditing(null)
    setForm(emptyForm)
    setFormError('')
    setShowForm(true)
  }

  function startEdit(agent) {
    setEditing(agent)
    setForm({
      name: agent.name,
      description: agent.description || '',
      system_prompt: agent.system_prompt,
    })
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
      const payload = { ...form, description: form.description || null }
      if (editing) {
        await api.patch(`/agents/${editing.id}`, payload)
      } else {
        await api.post('/agents', payload)
      }
      cancel()
      reload()
    } catch (err) {
      setFormError(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(agent) {
    try {
      await api.patch(`/agents/${agent.id}`, { is_active: !agent.is_active })
      reload()
    } catch (_err) {
      void 0
    }
  }

  async function removeAgent(agent) {
    if (!window.confirm(`Delete agent "${agent.name}"?`)) return
    try {
      await api.delete(`/agents/${agent.id}`)
      reload()
    } catch (err) {
      window.alert(err.message || 'Delete failed')
    }
  }

  return (
    <div>
      <PageTitle
        title="Agents"
        actions={
          !showForm && (
            <button className="btn primary" onClick={startCreate}>
              New agent
            </button>
          )
        }
      />

      {showForm && (
        <Card title={editing ? `Edit: ${editing.name}` : 'New agent'}>
          {formError && <div className="alert error">{formError}</div>}
          <form className="form-grid" onSubmit={handleSubmit}>
            <Field label="Name">
              <input
                className="input"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                required
              />
            </Field>
            <Field label="Description">
              <input
                className="input"
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
              />
            </Field>
            <Field label="System prompt">
              <textarea
                className="input"
                rows={6}
                value={form.system_prompt}
                onChange={(event) => setForm({ ...form, system_prompt: event.target.value })}
                required
              />
            </Field>
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

      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : loading ? (
        <Empty>Loading…</Empty>
      ) : agents.length === 0 ? (
        <Empty>No agents yet. Create your first one.</Empty>
      ) : (
        <Card>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Status</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.id}>
                  <td>{agent.name}</td>
                  <td className="muted">{agent.description || '—'}</td>
                  <td>
                    <Badge variant={agent.is_active ? 'success' : ''}>
                      {agent.is_active ? 'active' : 'inactive'}
                    </Badge>
                  </td>
                  <td>{formatDate(agent.updated_at)}</td>
                  <td className="actions">
                    <button className="btn small" onClick={() => startEdit(agent)}>
                      Edit
                    </button>
                    <button className="btn small" onClick={() => toggleActive(agent)}>
                      {agent.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button className="btn small danger" onClick={() => removeAgent(agent)}>
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