import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import {
  Badge,
  Card,
  Empty,
  ErrorBox,
  Field,
  formatDay,
  Input,
  PageTitle,
  toast,
  useFetch,
} from '../../components/Ui'

export default function AdminOrganizations() {
  const [q, setQ] = useState('')
  const [query, setQuery] = useState('')
  const { data, error, loading, reload } = useFetch(
    () => api.get(`/platform/organizations${query ? `?q=${encodeURIComponent(query)}` : ''}`),
    [query]
  )
  const organizations = data || []

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', business_name: '', timezone: 'UTC' })
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setSaving(true)
    setFormError('')
    try {
      const created = await api.post('/platform/organizations', {
        name: form.name,
        business_name: form.business_name || null,
        timezone: form.timezone || 'UTC',
      })
      setShowForm(false)
      setForm({ name: '', business_name: '', timezone: 'UTC' })
      reload()
      toast(`Organization "${created.name}" created`)
    } catch (err) {
      setFormError(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function toggleActive(org) {
    try {
      await api.patch(`/platform/organizations/${org.id}`, { is_active: !org.is_active })
      reload()
    } catch (err) {
      window.alert(err.message || 'Update failed')
    }
  }

  return (
    <div>
      <PageTitle
        title="Organizations"
        subtitle="Every tenant on the platform."
        actions={
          !showForm && (
            <button className="btn primary" onClick={() => setShowForm(true)}>
              New organization
            </button>
          )
        }
      />

      {showForm && (
        <Card title="New organization">
          {formError && <div className="alert error">{formError}</div>}
          <form className="form-grid" onSubmit={handleSubmit}>
            <Field label="Name">
              <Input
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                required
                placeholder="Acme Cleaning Co."
              />
            </Field>
            <Field label="Business name">
              <Input
                value={form.business_name}
                onChange={(event) => setForm({ ...form, business_name: event.target.value })}
                placeholder="Optional"
              />
            </Field>
            <Field label="Timezone">
              <Input
                value={form.timezone}
                onChange={(event) => setForm({ ...form, timezone: event.target.value })}
                placeholder="UTC"
              />
            </Field>
            <div className="form-actions">
              <button className="btn primary" disabled={saving}>
                {saving ? 'Creating…' : 'Create'}
              </button>
              <button
                className="btn"
                type="button"
                onClick={() => {
                  setShowForm(false)
                  setFormError('')
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </Card>
      )}

      <form
        className="topbar-search"
        style={{ margin: '16px 0', width: '100%', maxWidth: 420 }}
        onSubmit={(event) => {
          event.preventDefault()
          setQuery(q.trim())
        }}
      >
        <span className="search-ico">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4-4" />
          </svg>
        </span>
        <input
          placeholder="Search organizations by name…"
          value={q}
          onChange={(event) => setQ(event.target.value)}
        />
      </form>

      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : loading ? (
        <Empty>Loading…</Empty>
      ) : organizations.length === 0 ? (
        <Empty>No organizations found.</Empty>
      ) : (
        <Card>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Organization</th>
                  <th>Timezone</th>
                  <th>Members</th>
                  <th>Agents</th>
                  <th>Deployments</th>
                  <th>Calls</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {organizations.map((org) => (
                  <tr key={org.id}>
                    <td>
                      <Badge variant={org.is_active ? 'success' : ''}>
                        {org.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </td>
                    <td>
                      <Link to={`/admin/organizations/${org.id}`}>
                        {org.business_name || org.name}
                      </Link>
                      {org.business_name && org.business_name !== org.name ? (
                        <div className="muted small">{org.name}</div>
                      ) : null}
                    </td>
                    <td>{org.timezone}</td>
                    <td>{org.members_count}</td>
                    <td>{org.agents_count}</td>
                    <td>{org.deployments_count}</td>
                    <td>{org.calls_count}</td>
                    <td>{formatDay(org.created_at)}</td>
                    <td className="actions">
                      <button className="btn small" onClick={() => toggleActive(org)}>
                        {org.is_active ? 'Deactivate' : 'Activate'}
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