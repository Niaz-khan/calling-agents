import { useState } from 'react'
import { api } from '../api'
import {
  Card,
  Empty,
  ErrorBox,
  Field,
  formatDate,
  PageTitle,
  useFetch,
} from '../components/Ui'

const emptyForm = { name: '', phone_number: '', email: '', notes: '' }

export default function Customers() {
  const [query, setQuery] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const fetchCustomers = () => {
    const params = new URLSearchParams()
    if (query) params.set('q', query)
    const queryString = params.toString()
    return api.get(`/customers${queryString ? `?${queryString}` : ''}`)
  }
  const { data, error, loading, reload } = useFetch(fetchCustomers, [query])
  const customers = data || []

  function startCreate() {
    setEditing(null)
    setForm(emptyForm)
    setFormError('')
    setShowForm(true)
  }

  function startEdit(customer) {
    setEditing(customer)
    setForm({
      name: customer.name || '',
      phone_number: customer.phone_number,
      email: customer.email || '',
      notes: customer.notes || '',
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
      const payload = {
        ...form,
        name: form.name || null,
        email: form.email || null,
        notes: form.notes || null,
      }
      if (editing) {
        await api.patch(`/customers/${editing.id}`, payload)
      } else {
        await api.post('/customers', payload)
      }
      cancel()
      reload()
    } catch (err) {
      setFormError(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function removeCustomer(customer) {
    if (!window.confirm(`Delete customer ${customer.phone_number}?`)) return
    try {
      await api.delete(`/customers/${customer.id}`)
      reload()
    } catch (err) {
      window.alert(err.message || 'Delete failed')
    }
  }

  return (
    <div>
      <PageTitle
        title="Customers"
        actions={
          !showForm && (
            <button className="btn primary" onClick={startCreate}>
              New customer
            </button>
          )
        }
      />

      {showForm && (
        <Card title={editing ? `Edit: ${editing.phone_number}` : 'New customer'}>
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
            <Field label="Name">
              <input
                className="input"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
              />
            </Field>
            <Field label="Email">
              <input
                className="input"
                type="email"
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
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
          <Field label="Search">
            <input
              className="input"
              placeholder="Name, phone or email"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </Field>
        </div>
      </Card>

      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : loading ? (
        <Empty>Loading…</Empty>
      ) : customers.length === 0 ? (
        <Empty>No customers found.</Empty>
      ) : (
        <Card>
          <table className="table">
            <thead>
              <tr>
                <th>Phone</th>
                <th>Name</th>
                <th>Email</th>
                <th>Notes</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((customer) => (
                <tr key={customer.id}>
                  <td>{customer.phone_number}</td>
                  <td>{customer.name || '—'}</td>
                  <td>{customer.email || '—'}</td>
                  <td className="muted">{customer.notes || '—'}</td>
                  <td>{formatDate(customer.created_at)}</td>
                  <td className="actions">
                    <button className="btn small" onClick={() => startEdit(customer)}>
                      Edit
                    </button>
                    <button className="btn small danger" onClick={() => removeCustomer(customer)}>
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