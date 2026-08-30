import { useState } from 'react'
import { NavLink, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import {
  DashboardIcon,
  OrganizationIcon,
  UsersIcon,
  AgentIcon,
  DeployIcon,
  CallIcon,
  CalendarIcon,
  ChartIcon,
  WebsiteIcon,
  PhoneIcon,
  KnowledgeIcon,
  ServiceIcon,
  SettingsIcon,
  ChevronDownIcon,
  MenuIcon,
  LogoutIcon,
  ShieldIcon,
} from './icons'
import { initials } from './Ui'

const groups = [
  {
    label: 'Platform',
    items: [
      { to: '/admin', label: 'Overview', icon: DashboardIcon, end: true },
      { to: '/admin/settings', label: 'Settings', icon: SettingsIcon },
    ],
  },
  {
    label: 'Organizations',
    items: [{ to: '/admin/organizations', label: 'Organizations', icon: OrganizationIcon }],
  },
  {
    label: 'Operations',
    items: [
      { to: '/admin/users', label: 'Users', icon: UsersIcon },
      { to: '/admin/agents', label: 'Agents', icon: AgentIcon },
      { to: '/admin/deployments', label: 'Deployments', icon: DeployIcon },
      { to: '/admin/phone-numbers', label: 'Phone numbers', icon: PhoneIcon },
      { to: '/admin/calls', label: 'Calls', icon: CallIcon },
      { to: '/admin/customers', label: 'Customers', icon: UsersIcon },
      { to: '/admin/appointments', label: 'Appointments', icon: CalendarIcon },
      { to: '/admin/knowledge', label: 'Knowledge', icon: KnowledgeIcon },
      { to: '/admin/services', label: 'Services', icon: ServiceIcon },
    ],
  },
  {
    label: 'Insights',
    items: [{ to: '/admin/analytics', label: 'Analytics', icon: ChartIcon }],
  },
  {
    label: 'Content',
    items: [
      {
        to: '/admin/cms',
        label: 'Website CMS',
        icon: WebsiteIcon,
        children: [
          { to: '/admin/cms', label: 'Overview' },
          { to: '/admin/cms/landing', label: 'Landing page' },
          { to: '/admin/cms/features', label: 'Features' },
          { to: '/admin/cms/use-cases', label: 'Use cases' },
          { to: '/admin/cms/testimonials', label: 'Testimonials' },
          { to: '/admin/cms/pricing', label: 'Pricing' },
          { to: '/admin/cms/faqs', label: 'FAQ' },
          { to: '/admin/cms/navigation', label: 'Navigation' },
          { to: '/admin/cms/footer', label: 'Footer' },
          { to: '/admin/cms/site', label: 'SEO & Branding' },
          { to: '/admin/cms/versions', label: 'Versions' },
          { to: '/admin/cms/preview', label: 'Live preview' },
        ],
      },
    ],
  },
]

export default function AdminLayout({ children }) {
  const { user, logout, platformRole } = useAuth()
  const [open, setOpen] = useState(false)
  const location = useLocation()

  const current =
    groups
      .flatMap((group) => group.items)
      .flatMap((item) => item.children || [item])
      .filter((item) =>
        item.end ? location.pathname === item.to : location.pathname.startsWith(item.to)
      )
      .sort((a, b) => b.to.length - a.to.length)[0] || groups[0].items[0]

  const cmsOpen = location.pathname.startsWith('/admin/cms')

  const roleLabel =
    { SUPER_ADMIN: 'Super admin', PLATFORM_ADMIN: 'Platform admin', CONTENT_ADMIN: 'Content', SUPPORT_ADMIN: 'Support' }[
      platformRole
    ] || (user?.is_superuser ? 'Super admin' : 'Platform')

  return (
    <div className="shell">
      {open && <div className="backdrop" onClick={() => setOpen(false)} />}
      <aside className={`sidebar${open ? ' open' : ''}`}>
        <div className="brand">
          <span className="brand-mark">
            <ShieldIcon width={15} height={15} />
          </span>
          <span>Platform admin</span>
        </div>
        <nav className="nav">
          {groups.map((group) => (
            <div key={group.label}>
              <div className="nav-group">{group.label}</div>
              {group.items.map((item) => {
                const Icon = item.icon
                const withChildren = Boolean(item.children && item.children.length)
                return (
                  <div key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.end}
                      className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                      onClick={() => setOpen(false)}
                    >
                      <span className="nav-icon">
                        <Icon width={17} height={17} />
                      </span>
                      {item.label}
                      {withChildren && (
                        <ChevronDownIcon
                          width={14}
                          height={14}
                          className={`nav-caret${cmsOpen ? ' open' : ''}`}
                        />
                      )}
                    </NavLink>
                    {withChildren && cmsOpen && (
                      <div className="nav-sub">
                        {item.children.map((child) => (
                          <NavLink
                            key={child.to}
                            to={child.to}
                            end={child.to === '/admin/cms'}
                            className={({ isActive }) => (isActive ? 'nav-link sub active' : 'nav-link sub')}
                            onClick={() => setOpen(false)}
                          >
                            {child.label}
                          </NavLink>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          <Link to="/app" className="nav-link">
            <span className="nav-icon">
              <DashboardIcon width={17} height={17} />
            </span>
            Business app
          </Link>
          <button
            className="nav-link"
            onClick={logout}
            style={{ border: 0, background: 'none', cursor: 'pointer', width: '100%', textAlign: 'left' }}
          >
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
            <span className="brand-mark">
              <ShieldIcon width={15} height={15} />
            </span>
            <span>Platform admin</span>
          </div>
        </div>
        <header className="topbar">
          <div className="topbar-title">{current.label}</div>
          <div className="topbar-spacer" />
          <div className="topbar-actions">
            <div className="user-menu" title={user.full_name || user.email}>
              <span className="avatar">{initials(user.full_name || user.email)}</span>
              <span className="um-name">{roleLabel}</span>
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