import { NavLink } from 'react-router-dom'
import { useAuth } from '../auth'

const navItems = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/agents', label: 'Agents' },
  { to: '/calls', label: 'Calls' },
  { to: '/customers', label: 'Customers' },
  { to: '/appointments', label: 'Appointments' },
  { to: '/phone-numbers', label: 'Phone Numbers' },
  { to: '/knowledge', label: 'Knowledge Base' },
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">AI Call Agent</div>
        <nav className="nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="topbar-user">
            {user ? user.full_name || user.email : ''}
          </div>
          <button className="btn small" onClick={logout}>
            Log out
          </button>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  )
}