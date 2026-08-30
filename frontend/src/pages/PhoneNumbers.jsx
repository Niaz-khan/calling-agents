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

const emptyForm = {
  phone_number: '',
  provider: 'twilio',
  provider_number_id: '',
  agent_id: '',
  country: '',
  capabilities: ['voice'],
  inbound_enabled: true,
  outbound_enabled: true,
}

function capabilityOptions() {
  return [
    { value: 'voice', label: 'Voice' },
    { value: 'sms', label: 'SMS' },
  ]
}

export default function PhoneNumbers() {
  const fetchNumbers = () => api.get('/phone-numbers')
  const { data, error, loading, reload } = useFetch(fetchNumbers, [])
  const numbers = data || []

  const fetchAgents = () => api.get('/agents')
  const agentsResult = useFetch(fetchAgents, [])
  const agents = agentsResult.data || []

  const fetchStatus = () => api.get('/telephony/status')
  const statusResult = useFetch(fetchStatus, null)
  const [testing, setTesting] = useState(false)

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

  function toggleCapability(value) {
    const present = form.capabilities.includes(value)
    setForm({
      ...form,
      capabilities: present
        ? form.capabilities.filter((item) => item !== value)
        : [...form.capabilities, value],
    })
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
        country: form.country || null,
        capabilities: form.capabilities,
        inbound_enabled: form.inbound_enabled,
        outbound_enabled: form.outbound_enabled,
      })
      cancel()
      reload()
    } catch (err) {
      setFormError(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function testConnection() {
    setTesting(true)
    try {
      await statusResult.reload()
    } finally {
      setTesting(false)
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

  async function toggleFlag(number, field) {
    try {
      await api.patch(`/phone-numbers/${number.id}`, { [field]: !number[field] })
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

  const status = statusResult.data

  return (
    <div>
      <PageTitle
        title="Phone Numbers"
        actions={
          !showForm && (
            <button className="btn primary" onClick={startCreate}>
              Connect a number
            </button>
          )
        }
      />

      <Card title="Provider connection">
        {statusResult.error ? (
          <ErrorBox message={statusResult.error} onRetry={statusResult.reload} />
        ) : status === null ? (
          <Empty>Checking connection…</Empty>
        ) : (
          <div className="status-row">
            <div>
              Provider: <b>{status.provider}</b>
              <span className="muted"> ({status.connected ? 'connected' : status.configured ? 'configured' : 'not configured'})</span>
            </div>
            <div>
              <Badge variant={status.connected ? 'success' : ''}>
                {status.connected ? 'Connected' : status.configured ? 'Configured' : 'Not configured'}
              </Badge>
              {status.error && <span className="muted"> {status.error}</span>}
            </div>
            <button className="btn small" onClick={testConnection} disabled={testing}>
              {testing ? 'Testing…' : 'Test connection'}
            </button>
          </div>
        )}
      </Card>

      {showForm && (
        <Card title="Connect a phone number">
          {formError && <div className="alert error">{formError}</div>}
          <form className="form-grid" onSubmit={handleSubmit}>
            <Field label="Phone number (E.164, e.g. +15125550000)">
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
            <Field label="Country code (ISO, e.g. US)">
              <input
                className="input"
                maxLength="10"
                value={form.country}
                onChange={(event) => setForm({ ...form, country: event.target.value })}
              />
            </Field>
            <Field label="Capabilities">
              <div className="cap-row">
                {capabilityOptions().map((option) => (
                  <label className="toggle" key={option.value}>
                    <input
                      type="checkbox"
                      checked={form.capabilities.includes(option.value)}
                      onChange={() => toggleCapability(option.value)}
                    />
                    <span>{option.label}</span>
                  </label>
                ))}
              </div>
            </Field>
            <label className="toggle">
              <input
                type="checkbox"
                checked={form.inbound_enabled}
                onChange={(event) => setForm({ ...form, inbound_enabled: event.target.checked })}
              />
              <span>Accept inbound calls</span>
            </label>
            <label className="toggle">
              <input
                type="checkbox"
                checked={form.outbound_enabled}
                onChange={(event) => setForm({ ...form, outbound_enabled: event.target.checked })}
              />
              <span>Allow outbound calls</span>
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
                <th>Country</th>
                <th>Capabilities</th>
                <th>Inbound</th>
                <th>Outbound</th>
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
                    <td>{number.country || '—'}</td>
                    <td>
                      {(number.capabilities || []).map((cap) => (
                        <span className="stripe" key={cap}>
                          {cap}
                        </span>
                      )) || '—'}
                    </td>
                    <td>
                      <button
                        className="btn small"
                        onClick={() => toggleFlag(number, 'inbound_enabled')}
                      >
                        {number.inbound_enabled ? 'Enabled' : 'Disabled'}
                      </button>
                    </td>
                    <td>
                      <button
                        className="btn small"
                        onClick={() => toggleFlag(number, 'outbound_enabled')}
                      >
                        {number.outbound_enabled ? 'Enabled' : 'Disabled'}
                      </button>
                    </td>
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