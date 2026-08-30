import { useState } from 'react'
import { api } from '../../api'
import { useAuth } from '../../auth'
import {
  Badge,
  Card,
  Empty,
  ErrorBox,
  formatDay,
  PageTitle,
  Select,
  toast,
  useFetch,
} from '../../components/Ui'

const ROLES = [
  { value: '', label: 'Business user' },
  { value: 'SUPPORT_ADMIN', label: 'Support admin' },
  { value: 'CONTENT_ADMIN', label: 'Content admin' },
  { value: 'PLATFORM_ADMIN', label: 'Platform admin' },
  { value: 'SUPER_ADMIN', label: 'Super admin' },
]

export default function AdminUsers() {
  const { user: currentUser } = useAuth()
  const isSuperAdmin = Boolean(currentUser?.is_superuser)
  const [q, setQ] = useState('')
  const { data, error, loading, reload } = useFetch(
    () => api.get(`/platform/users${q ? `?q=${encodeURIComponent(q)}` : ''}`),
    [q]
  )
  const users = data || []

  async function changeRole(targetUser, platform_role) {
    try {
      await api.patch(`/platform/users/${targetUser.id}/role`, { platform_role })
      reload()
      toast(`Role updated for ${targetUser.email}`)
    } catch (err) {
      window.alert(err.message || 'Update failed')
    }
  }

  async function toggleActive(targetUser) {
    try {
      await api.patch(`/platform/users/${targetUser.id}/role`, { is_active: !targetUser.is_active })
      reload()
    } catch (err) {
      window.alert(err.message || 'Update failed')
    }
  }

  return (
    <div>
      <PageTitle
        title="Users"
        subtitle="Accounts across the platform. Role management requires super admin."
      />

      <form
        className="topbar-search"
        style={{ margin: '0 0 16px', width: '100%', maxWidth: 420 }}
        onSubmit={(event) => {
          event.preventDefault()
          setQ(q.trim())
        }}
      >
        <span className="search-ico">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4-4" />
          </svg>
        </span>
        <input
          placeholder="Search users by email or name…"
          value={q}
          onChange={(event) => setQ(event.target.value)}
        />
      </form>

      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : loading ? (
        <Empty>Loading…</Empty>
      ) : users.length === 0 ? (
        <Empty>No users found.</Empty>
      ) : (
        <Card>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>User</th>
                  <th>Email</th>
                  <th>Platform role</th>
                  <th>Organizations</th>
                  <th>Joined</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <Badge variant={user.is_active ? 'success' : 'danger'}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </td>
                    <td>
                      {user.full_name || '—'}
                      {user.is_superuser ? <Badge variant="info">superuser</Badge> : null}
                    </td>
                    <td>{user.email}</td>
                    <td>
                      {isSuperAdmin ? (
                        <Select
                          value={user.platform_role || ''}
                          onChange={(event) => changeRole(user, event.target.value)}
                          style={{ minWidth: 150 }}
                        >
                          {ROLES.map((role) => (
                            <option key={role.value} value={role.value}>
                              {role.label}
                            </option>
                          ))}
                        </Select>
                      ) : (
                        user.platform_role || 'Business user'
                      )}
                    </td>
                    <td>
                      {user.organizations.length === 0 ? (
                        <span className="muted">—</span>
                      ) : (
                        user.organizations.map((org) => (
                          <div key={org.id} className="small">
                            {org.name} <span className="muted">({org.role})</span>
                          </div>
                        ))
                      )}
                    </td>
                    <td>{formatDay(user.date_joined)}</td>
                    <td className="actions">
                      {isSuperAdmin && (
                        <button className="btn small" onClick={() => toggleActive(user)}>
                          {user.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      )}
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