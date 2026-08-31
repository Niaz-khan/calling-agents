import { useState } from 'react'
import { NavLink, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import {
  DashboardIcon,
  AgentIcon,
  DeployIcon,
  CallIcon,
  UsersIcon,
  CalendarIcon,
  PhoneIcon,
  KnowledgeIcon,
  ServiceIcon,
  ChartIcon,
  MenuIcon,
  LogoutIcon,
  ShieldIcon,
} from './icons'
import { initials } from './Ui'

const groups = [
  {
    label: 'Overview',
    items: [{ to: '/app', label: 'Dashboard', icon: DashboardIcon, end: true }],
  },
  {
    label: 'Engagement',
    items: [
      { to: '/app/agents', label: 'Agents', icon: AgentIcon },
      { to: '/app/deployments', label: 'Deployments', icon: DeployIcon },
      { to: '/app/calls', label: 'Calls', icon: CallIcon },
      { to: '/app/customers', label: 'Customers', icon: UsersIcon },
      { to: '/app/appointments', label: 'Appointments', icon: CalendarIcon },
    ],
  },
  {
    label: 'Channels',
    items: [{ to: '/app/phone-numbers', label: 'Phone Numbers', icon: PhoneIcon }],
  },
  {
    label: 'Knowledge & Insights',
    items: [
      { to: '/app/knowledge', label: 'Knowledge Base', icon: KnowledgeIcon },
      { to: '/app/services', label: 'Services', icon: ServiceIcon },
      { to: '/app/analytics', label: 'Analytics', icon: ChartIcon },
    ],
  },
]

export default function Layout({ children }) {
  const { user, logout, isPlatformUser } = useAuth()
  const [open, setOpen] = useState(false)
  const location = useLocation()

  const current =
    groups
      .flatMap((group) => group.items)
      .find((item) =>
        item.end ? location.pathname === item.to : location.pathname.startsWith(item.to)
      ) || groups[0].items[0]

  return (
    <div className="shell">
      {open && <div className="backdrop" onClick={() => setOpen(false)} />}
      <aside className={`sidebar${open ? ' open' : ''}`}>
        <div className="brand">
          <span className="brand-mark">A</span>
          <span>AI Call Agent</span>
        </div>
        <nav className="nav">
          {groups.map((group) => (
            <div key={group.label}>
              <div className="nav-group">{group.label}</div>
              {group.items.map((item) => {
                const Icon = item.icon
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                    onClick={() => setOpen(false)}
                  >
                    <span className="nav-icon">
                      <Icon width={17} height={17} />
                    </span>
                    {item.label}
                  </NavLink>
                )
              })}
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          {isPlatformUser ? (
            <NavLink
              to="/admin"
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
              onClick={() => setOpen(false)}
            >
              <span className="nav-icon">
                <ShieldIcon width={17} height={17} />
              </span>
              Platform admin
            </NavLink>
          ) : null}
          <button className="nav-link" onClick={logout} style={{ border: 0, background: 'none', cursor: 'pointer', width: '100%', textAlign: 'left' }}>
            <span className="nav-icon">
              <LogoutIcon width={17} height={17} />
            </span>
            Log out
          </button>
        </div>
      </aside>
      <div className="main">
        <div className="mobile-bar">
          <button className="icon-btn" onClick={() => setOpen(true)} aria-label="Open menu">
            <MenuIcon width={18} height={18} />
          </button>
          <div className="brand" style={{ padding: 0 }}>
            <span className="brand-mark">A</span>
            <span>AI Call Agent</span>
          </div>
        </div>
        <header className="topbar">
          <div className="topbar-title">{current.label}</div>
          <div className="topbar-spacer" />
          {isPlatformUser ? (
            <Link to="/admin" className="btn small" title="Platform admin">
              Platform
            </Link>
          ) : null}
          <div className="topbar-actions">
            <div className="user-menu" title={`${user.full_name || user.email}`}>
              <span className="avatar">{initials(user.full_name || user.email)}</span>
              <span className="um-name">
                {user.full_name || user.email}
              </span>
            </div>
            <button className="icon-btn" onClick={logout} title="Log out" aria-label="Log out">
              <LogoutIcon width={17} height={17} />
            </button>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  )
}