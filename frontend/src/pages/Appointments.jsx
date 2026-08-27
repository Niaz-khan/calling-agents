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
  statusVariant,
  useFetch,
} from '../components/Ui'

const emptyForm = {
  agent_id: '',
  customer_name: '',
  customer_phone: '',
  start_time: '',
  end_time: '',
  notes: '',
}

export default function Appointments() {
  const [statusFilter, setStatusFilter] = useState('')

  const fetchAppointments = () => {
    const params = new URLSearchParams()
    if (statusFilter) params.set('status_filter', statusFilter)
    const queryString = params.toString()
    return api.get(`/appointments${queryString ? `?${queryString}` : ''}`)
  }
  const { data, error, loading, reload } = useFetch(fetchAppointments, [statusFilter])
  const appointments = data || []

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

  async function handleSubmit(event) {
    event.preventDefault()
    setSaving(true)
    setFormError('')
    try {
      await api.post('/appointments', {
        ...form,
        agent_id: Number(form.agent_id),
        start_time: new Date(form.start_time).toISOString(),
        end_time: new Date(form.end_time).toISOString(),
        notes: form.notes || null,
      })
      cancel()
      reload()
    } catch (err) {
      setFormError(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function setStatus(appointment, status) {
    try {
      await api.patch(`/appointments/${appointment.id}`, { status })
      reload()
    } catch (err) {
      window.alert(err.message || 'Update failed')
    }
  }

  async function removeAppointment(appointment) {
    if (!window.confirm(`Delete appointment for ${appointment.customer_name}?`)) return
    try {
      await api.delete(`/appointments/${appointment.id}`)
      reload()
    } catch (err) {
      window.alert(err.message || 'Delete failed')
    }
  }

  return (
    <div>
      <PageTitle
        title="Appointments"
        actions={
          !showForm && (
            <button className="btn primary" onClick={startCreate}>
              New appointment
            </button>
          )
        }
      />

      {showForm && (
        <Card title="New appointment">
          {formError && <div className="alert error">{formError}</div>}
          <form className="form-grid" onSubmit={handleSubmit}>
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
            <Field label="Customer name">
              <input
                className="input"
                value={form.customer_name}
                onChange={(event) => setForm({ ...form, customer_name: event.target.value })}
                required
              />
            </Field>
            <Field label="Customer phone">
              <input
                className="input"
                value={form.customer_phone}
                onChange={(event) => setForm({ ...form, customer_phone: event.target.value })}
                required
              />
            </Field>
            <Field label="Start">
              <input
                className="input"
                type="datetime-local"
                value={form.start_time}
                onChange={(event) => setForm({ ...form, start_time: event.target.value })}
                required
              />
            </Field>
            <Field label="End">
              <input
                className="input"
                type="datetime-local"
                value={form.end_time}
                onChange={(event) => setForm({ ...form, end_time: event.target.value })}
                required
              />
            </Field>
            <Field label="Notes">
              <textarea
                className="input"
                rows={3}
                value={form.notes}
                onChange={(event) => setForm({ ...form, notes: event.target.value })}
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

      <Card className="toolbar-card">
        <div className="toolbar">
          <Field label="Status">
            <select
              className="input"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="">All statuses</option>
              <option value="scheduled">Scheduled</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </Field>
        </div>
      </Card>

      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : loading ? (
        <Empty>Loading…</Empty>
      ) : appointments.length === 0 ? (
        <Empty>No appointments found.</Empty>
      ) : (
        <Card>
          <table className="table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Customer</th>
                <th>Phone</th>
                <th>Agent</th>
                <th>Start</th>
                <th>End</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {appointments.map((appointment) => {
                const agent = agents.find((item) => item.id === appointment.agent_id)
                return (
                  <tr key={appointment.id}>
                    <td>
                      <Badge variant={statusVariant(appointment.status)}>
                        {appointment.status}
                      </Badge>
                    </td>
                    <td>{appointment.customer_name}</td>
                    <td>{appointment.customer_phone}</td>
                    <td>{agent ? agent.name : appointment.agent_id}</td>
                    <td>{formatDate(appointment.start_time)}</td>
                    <td>{formatDate(appointment.end_time)}</td>
                    <td className="actions">
                      {appointment.status === 'scheduled' && (
                        <button
                          className="btn small"
                          onClick={() => setStatus(appointment, 'completed')}
                        >
                          Complete
                        </button>
                      )}
                      {appointment.status === 'scheduled' && (
                        <button
                          className="btn small"
                          onClick={() => setStatus(appointment, 'cancelled')}
                        >
                          Cancel
                        </button>
                      )}
                      <button
                        className="btn small danger"
                        onClick={() => removeAppointment(appointment)}
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