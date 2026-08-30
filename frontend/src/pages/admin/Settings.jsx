import { Card, PageTitle } from '../../components/Ui'
import CmsSite from './CmsSite'

const ROLE_MATRIX = [
  {
    role: 'SUPER_ADMIN',
    label: 'Super admin',
    capabilities: [
      'Everything a platform admin can do',
      'Grant and revoke platform roles',
      'Activate / deactivate users',
      'Manage the platform itself',
    ],
  },
  {
    role: 'PLATFORM_ADMIN',
    label: 'Platform admin',
    capabilities: [
      'Organizations and users',
      'Agents, deployments, phone numbers',
      'Calls, customers, appointments',
      'Knowledge bases and services',
      'Platform analytics',
      'CMS and site settings',
    ],
  },
  {
    role: 'CONTENT_ADMIN',
    label: 'Content admin',
    capabilities: [
      'Landing page copy',
      'Features, use cases, testimonials, pricing',
      'FAQ, navigation, footer',
      'SEO metadata and site branding',
    ],
  },
  {
    role: 'SUPPORT_ADMIN',
    label: 'Support admin (prepared)',
    capabilities: ['Future back-office support access'],
  },
]

const links = [
  ['Landing page copy', '/admin/cms/landing', 'Hero, value strip, problem, how-it-works, website, phone, CTA'],
  ['Feature cards', '/admin/cms/features', 'Features shown on the landing page'],
  ['Use cases', '/admin/cms/use-cases', 'Industry solutions'],
  ['Testimonials', '/admin/cms/testimonials', 'Customer quotes'],
  ['Pricing', '/admin/cms/pricing', 'Pricing plans'],
  ['Live preview', '/admin/cms/preview', 'View the landing page using current, unpublished CMS content'],
]

export default function AdminSettings() {
  return (
    <div>
      <PageTitle
        title="Platform settings"
        subtitle="Functional site settings, plus the platform role model."
      />

      <Card title="Site & SEO">
        <p className="muted">
          Edit below, then publish from the CMS dashboard — the public site only updates when you
          publish.
        </p>
        <CmsSite />
      </Card>

      <Card title="Platform roles">
        <p className="muted">
          Platform roles are granted by a super admin from Users. Business (organization) users
          are never granted platform access — their dashboard stays scoped to their own
          organization. Django <code>is_superuser</code> always bypasses role checks.
        </p>
        <div className="grid two">
          {ROLE_MATRIX.map((entry) => (
            <div className="meta-stat" key={entry.role}>
              <div className="val small">{entry.label}</div>
              <ul className="breakdown" style={{ marginTop: 10 }}>
                {entry.capabilities.map((cap) => (
                  <li key={cap}>
                    <span>{cap}</span>
                    <strong />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Configuration">
        <div className="grid two">
          {links.map(([label, to, hint]) => (
            <div className="meta-stat" key={to} style={{ cursor: 'pointer' }}>
              <a href={`#${to}`} style={{ textDecoration: 'none' }}>
                <div className="val small">{label}</div>
                <div className="lab">{hint}</div>
              </a>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}