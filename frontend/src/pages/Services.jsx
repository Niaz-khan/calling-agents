import { useState } from 'react'
import { api } from '../api'
import {
  Badge,
  Card,
  Empty,
  ErrorBox,
  Field,
  PageTitle,
  useFetch,
} from '../components/Ui'

const emptyForm = {
  name: '',
  description: '',
  duration_minutes: '30',
  price: '',
  currency: 'USD',
  active: true,
}

export default function Services() {
  const { data, error, loading, reload } = useFetch(() => api.get('/services'), [])
  const services = data || []

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
      await api.post('/services', {
        ...form,
        duration_minutes: Number(form.duration_minutes),
        price: form.price === '' ? null : Number(form.price),
        active: Boolean(form.active),
        description: form.description || null,
      })
      cancel()
      reload()
    } catch (err) {
      setFormError(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(service) {
    try {
      await api.patch(`/services/${service.id}`, { active: !service.active })
      reload()
    } catch (err) {
      window.alert(err.message || 'Update failed')
    }
  }

  async function removeService(service) {
    if (!window.confirm(`Delete service "${service.name}"?`)) return
    try {
      await api.delete(`/services/${service.id}`)
      reload()
    } catch (err) {
      window.alert(err.message || 'Delete failed')
    }
  }

  function priceLabel(service) {
    if (service.price == null) return '—'
    return `${service.price} ${service.currency}`
  }

  return (
    <div>
      <PageTitle
        title="Services"
        subtitle="Appointment types your AI agents can book."
        actions={
          !showForm && (
            <button className="btn primary" onClick={startCreate}>
              New service
            </button>
          )
        }
      />

      {showForm && (
        <Card title="New service">
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
            <Field label="Duration (minutes)">
              <input
                className="input"
                type="number"
                min="1"
                value={form.duration_minutes}
                onChange={(event) => setForm({ ...form, duration_minutes: event.target.value })}
                required
              />
            </Field>
            <Field label="Price">
              <input
                className="input"
                type="number"
                min="0"
                step="0.01"
                placeholder="Optional"
                value={form.price}
                onChange={(event) => setForm({ ...form, price: event.target.value })}
              />
            </Field>
            <Field label="Currency">
              <input
                className="input"
                maxLength="3"
                placeholder="USD"
                value={form.currency}
                onChange={(event) => setForm({ ...form, currency: event.target.value.toUpperCase() })}
                required
              />
            </Field>
            <Field label="Description">
              <textarea
                className="input"
                rows={3}
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
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
      ) : services.length === 0 ? (
        <Empty>No services yet. Add one so agents can book appointments.</Empty>
      ) : (
        <Card>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Name</th>
                  <th>Duration</th>
                  <th>Price</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {services.map((service) => (
                  <tr key={service.id}>
                    <td>
                      <Badge variant={service.active ? 'success' : ''}>
                        {service.active ? 'Active' : 'Inactive'}
                      </Badge>
                    </td>
                    <td>
                      <div>{service.name}</div>
                      {service.description && (
                        <div className="muted small">{service.description}</div>
                      )}
                    </td>
                    <td>{service.duration_minutes} min</td>
                    <td>{priceLabel(service)}</td>
                    <td className="actions">
                      <button
                        className="btn small"
                        onClick={() => toggleActive(service)}
                      >
                        {service.active ? 'Deactivate' : 'Activate'}
                      </button>
                      <button
                        className="btn small danger"
                        onClick={() => removeService(service)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}