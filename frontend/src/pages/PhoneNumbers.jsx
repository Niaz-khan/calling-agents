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

const emptyForm = { phone_number: '', provider: 'twilio', provider_number_id: '', agent_id: '' }

export default function PhoneNumbers() {
  const fetchNumbers = () => api.get('/phone-numbers')
  const { data, error, loading, reload } = useFetch(fetchNumbers, [])
  const numbers = data || []

  const fetchAgents = () => api.get('/agents')
  const agentsResult = useFetch(fetchAgents, [])
  const agents = agentsResult.data || []

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  function startCreate() {
    setForm(emptyForm)
    setFormError('')
    setShowForm(true)
  }

  function cancel() {
    setShowForm(false)
    setForm(emptyForm)
    setFormError('')
  }

  function agentFor(number) {
    return agents.find((agent) => agent.id === number.agent_id)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSaving(true)
    setFormError('')
    try {
      await api.post('/phone-numbers', {
        phone_number: form.phone_number,
        provider: form.provider,
        provider_number_id: form.provider_number_id || null,
        agent_id: Number(form.agent_id),
      })
      cancel()
      reload()
    } catch (err) {
      setFormError(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(number) {
    try {
      await api.patch(`/phone-numbers/${number.id}`, { is_active: !number.is_active })
      reload()
    } catch (err) {
      window.alert(err.message || 'Update failed')
    }
  }

  async function removeNumber(number) {
    if (!window.confirm(`Delete ${number.phone_number}?`)) return
    try {
      await api.delete(`/phone-numbers/${number.id}`)
      reload()
    } catch (err) {
      window.alert(err.message || 'Delete failed')
    }
  }

  return (
    <div>
      <PageTitle
        title="Phone Numbers"
        actions={
          !showForm && (
            <button className="btn primary" onClick={startCreate}>
              Add number
            </button>
          )
        }
      />

      {showForm && (
        <Card title="New phone number">
          {formError && <div className="alert error">{formError}</div>}
          <form className="form-grid" onSubmit={handleSubmit}>
            <Field label="Phone number">
              <input
                className="input"
                value={form.phone_number}
                onChange={(event) => setForm({ ...form, phone_number: event.target.value })}
                required
              />
            </Field>
            <Field label="Agent">
              <select
                className="input"
                value={form.agent_id}
                onChange={(event) => setForm({ ...form, agent_id: event.target.value })}
                required
              >
                <option value="">Select agent</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Provider">
              <select
                className="input"
                value={form.provider}
                onChange={(event) => setForm({ ...form, provider: event.target.value })}
              >
                <option value="twilio">Twilio</option>
                <option value="telnyx">Telnyx</option>
                <option value="other">Other</option>
              </select>
            </Field>
            <Field label="Provider number ID">
              <input
                className="input"
                value={form.provider_number_id}
                onChange={(event) =>
                  setForm({ ...form, provider_number_id: event.target.value })
                }
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
      ) : numbers.length === 0 ? (
        <Empty>No phone numbers yet.</Empty>
      ) : (
        <Card>
          <table className="table">
            <thead>
              <tr>
                <th>Number</th>
                <th>Agent</th>
                <th>Provider</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {numbers.map((number) => {
                const agent = agentFor(number)
                return (
                  <tr key={number.id}>
                    <td>{number.phone_number}</td>
                    <td>{agent ? agent.name : number.agent_id}</td>
                    <td>{number.provider}</td>
                    <td>
                      <Badge variant={number.is_active ? 'success' : ''}>
                        {number.is_active ? 'active' : 'inactive'}
                      </Badge>
                    </td>
                    <td>{formatDate(number.created_at)}</td>
                    <td className="actions">
                      <button className="btn small" onClick={() => toggleActive(number)}>
                        {number.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                      <button
                        className="btn small danger"
                        onClick={() => removeNumber(number)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}