import { Component, lazy, Suspense } from 'react'
import { HashRouter, Route, Routes, Navigate, Outlet, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth'
import { Loading, Empty } from './components/Ui'
import { OrganizationIcon } from './components/icons'
import { setToken } from './api'
import Layout from './components/Layout'
import AdminLayout from './components/AdminLayout'
import Landing from './pages/Landing'
import AuthLayout from './components/auth/AuthLayout'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Agents = lazy(() => import('./pages/Agents'))
const Deployments = lazy(() => import('./pages/Deployments'))
const DeploymentDetail = lazy(() => import('./pages/DeploymentDetail'))
const Calls = lazy(() => import('./pages/Calls'))
const CallDetail = lazy(() => import('./pages/CallDetail'))
const Customers = lazy(() => import('./pages/Customers'))
const Appointments = lazy(() => import('./pages/Appointments'))
const PhoneNumbers = lazy(() => import('./pages/PhoneNumbers'))
const Knowledge = lazy(() => import('./pages/Knowledge'))
const Services = lazy(() => import('./pages/Services'))
const Analytics = lazy(() => import('./pages/Analytics'))

const AdminOverview = lazy(() => import('./pages/admin/Overview'))
const AdminOrganizations = lazy(() => import('./pages/admin/Organizations'))
const AdminOrganizationDetail = lazy(() => import('./pages/admin/OrganizationDetail'))
const AdminUsers = lazy(() => import('./pages/admin/Users'))
const AdminAnalytics = lazy(() => import('./pages/admin/Analytics'))
const AdminSettings = lazy(() => import('./pages/admin/Settings'))
const CmsOverview = lazy(() => import('./pages/admin/Cms'))
const CmsVersions = lazy(() => import('./pages/admin/CmsVersions'))
const CmsLanding = lazy(() => import('./pages/admin/CmsLanding'))
const CmsSite = lazy(() => import('./pages/admin/CmsSite'))
const CmsPreview = lazy(() => import('./pages/admin/CmsPreview'))
const AdminAgents = lazy(() => import('./pages/admin/resources').then((m) => ({ default: m.AdminAgents })))
const AdminDeployments = lazy(() => import('./pages/admin/resources').then((m) => ({ default: m.AdminDeployments })))
const AdminCalls = lazy(() => import('./pages/admin/resources').then((m) => ({ default: m.AdminCalls })))
const AdminCustomers = lazy(() => import('./pages/admin/resources').then((m) => ({ default: m.AdminCustomers })))
const AdminAppointments = lazy(() => import('./pages/admin/resources').then((m) => ({ default: m.AdminAppointments })))
const AdminPhoneNumbers = lazy(() => import('./pages/admin/resources').then((m) => ({ default: m.AdminPhoneNumbers })))
const AdminKnowledge = lazy(() => import('./pages/admin/resources').then((m) => ({ default: m.AdminKnowledge })))
const AdminServices = lazy(() => import('./pages/admin/resources').then((m) => ({ default: m.AdminServices })))
const FeatureEditor = lazy(() => import('./pages/admin/CmsCollections').then((m) => ({ default: m.FeatureEditor })))
const UseCaseEditor = lazy(() => import('./pages/admin/CmsCollections').then((m) => ({ default: m.UseCaseEditor })))
const TestimonialEditor = lazy(() => import('./pages/admin/CmsCollections').then((m) => ({ default: m.TestimonialEditor })))
const PricingEditor = lazy(() => import('./pages/admin/CmsCollections').then((m) => ({ default: m.PricingEditor })))
const FaqEditor = lazy(() => import('./pages/admin/CmsCollections').then((m) => ({ default: m.FaqEditor })))
const NavigationEditor = lazy(() => import('./pages/admin/CmsCollections').then((m) => ({ default: m.NavigationEditor })))
const FooterEditor = lazy(() => import('./pages/admin/CmsCollections').then((m) => ({ default: m.FooterEditor })))

function PageLoader() {
  return (
    <div className="content">
      <Loading />
    </div>
  )
}

function NoOrganization({ user, logout }) {
  return (
    <div className="no-org-panel">
      <Empty
        icon={<OrganizationIcon width={22} height={22} />}
        title="You don't have an organization yet"
      >
        Your account <strong>{user.full_name || user.email}</strong> isn't linked to an
        organization, so there's no business workspace to show yet.
      </Empty>
      <div className="no-org-steps">
        <p>To get started, an administrator needs to add you to an organization. If you
        signed up yourself, your workspace should exist — try re-registering, or contact
        your account administrator for help.</p>
      </div>
      <div className="no-org-actions">
        <button className="btn" onClick={logout}>
          Log out
        </button>
      </div>
    </div>
  )
}

function Protected() {
  const { user, loading, logout, isPlatformUser } = useAuth()
  if (loading) return <Loading />
  if (!user) return <Navigate to="/login" replace />

  const organizations = user.organizations || []
  const isPlatform = isPlatformUser

  // Platform admins without an organization belong in the /admin console, not the
  // business workspace — send them there instead of the broken org-scoped pages.
  if (isPlatform && organizations.length === 0) return <Navigate to="/admin" replace />

  return (
    <Layout>
      <Suspense fallback={<PageLoader />}>
        {organizations.length === 0 ? (
          <NoOrganization user={user} logout={logout} />
        ) : (
          <Outlet />
        )}
      </Suspense>
    </Layout>
  )
}

function RequireAdmin() {
  const { user, loading, isPlatformUser } = useAuth()
  if (loading) return <Loading />
  if (!user) return <Navigate to="/login" replace />
  if (!isPlatformUser) return <Navigate to="/app" replace />
  return (
    <AdminLayout>
      <Suspense fallback={<PageLoader />}>
        <Outlet />
      </Suspense>
    </AdminLayout>
  )
}

const LEGACY_PREFIXES = ['/agents', '/deployments', '/calls', '/customers', '/appointments', '/phone-numbers', '/knowledge']

function LegacyRedirect() {
  const location = useLocation()
  if (LEGACY_PREFIXES.some((prefix) => location.pathname.startsWith(prefix))) {
    return <Navigate to={`/app${location.pathname}${location.search}`} replace />
  }
  return <Navigate to="/" replace />
}

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error: String((error && error.message) || error) }
  }

  handleLogout = () => {
    setToken(null)
    window.location.reload()
  }

  render() {
    if (!this.state.error) return this.props.children

    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1>Something went wrong</h1>
          <p className="muted">{this.state.error}</p>
          <button className="btn block" onClick={() => window.location.reload()}>
            Reload
          </button>
          <button className="btn block" onClick={this.handleLogout}>
            Log out
          </button>
        </div>
      </div>
    )
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <HashRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route element={<AuthLayout />}>
              <Route path="/login" element={null} />
              <Route path="/register" element={null} />
            </Route>

            <Route element={<Protected />}>
              <Route path="/app" element={<Dashboard />} />
              <Route path="/app/agents" element={<Agents />} />
              <Route path="/app/deployments" element={<Deployments />} />
              <Route path="/app/deployments/:id" element={<DeploymentDetail />} />
              <Route path="/app/calls" element={<Calls />} />
              <Route path="/app/calls/:callId" element={<CallDetail />} />
              <Route path="/app/customers" element={<Customers />} />
              <Route path="/app/appointments" element={<Appointments />} />
              <Route path="/app/phone-numbers" element={<PhoneNumbers />} />
              <Route path="/app/knowledge" element={<Knowledge />} />
              <Route path="/app/services" element={<Services />} />
              <Route path="/app/analytics" element={<Analytics />} />
            </Route>

            <Route element={<RequireAdmin />}>
              <Route path="/admin" element={<AdminOverview />} />
              <Route path="/admin/settings" element={<AdminSettings />} />
              <Route path="/admin/organizations" element={<AdminOrganizations />} />
              <Route path="/admin/organizations/:id" element={<AdminOrganizationDetail />} />
              <Route path="/admin/users" element={<AdminUsers />} />
              <Route path="/admin/agents" element={<AdminAgents />} />
              <Route path="/admin/deployments" element={<AdminDeployments />} />
              <Route path="/admin/calls" element={<AdminCalls />} />
              <Route path="/admin/customers" element={<AdminCustomers />} />
              <Route path="/admin/appointments" element={<AdminAppointments />} />
              <Route path="/admin/phone-numbers" element={<AdminPhoneNumbers />} />
              <Route path="/admin/knowledge" element={<AdminKnowledge />} />
              <Route path="/admin/services" element={<AdminServices />} />
              <Route path="/admin/analytics" element={<AdminAnalytics />} />
              <Route path="/admin/cms" element={<CmsOverview />} />
              <Route path="/admin/cms/versions" element={<CmsVersions />} />
              <Route path="/admin/cms/preview" element={<CmsPreview />} />
              <Route path="/admin/cms/landing" element={<CmsLanding />} />
              <Route path="/admin/cms/site" element={<CmsSite />} />
              <Route path="/admin/cms/features" element={<FeatureEditor />} />
              <Route path="/admin/cms/use-cases" element={<UseCaseEditor />} />
              <Route path="/admin/cms/testimonials" element={<TestimonialEditor />} />
              <Route path="/admin/cms/pricing" element={<PricingEditor />} />
              <Route path="/admin/cms/faqs" element={<FaqEditor />} />
              <Route path="/admin/cms/navigation" element={<NavigationEditor />} />
              <Route path="/admin/cms/footer" element={<FooterEditor />} />
            </Route>

            <Route path="/agents/*" element={<LegacyRedirect />} />
            <Route path="/deployments/*" element={<LegacyRedirect />} />
            <Route path="/calls/*" element={<LegacyRedirect />} />
            <Route path="/customers/*" element={<LegacyRedirect />} />
            <Route path="/appointments/*" element={<LegacyRedirect />} />
            <Route path="/phone-numbers/*" element={<LegacyRedirect />} />
            <Route path="/knowledge/*" element={<LegacyRedirect />} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </HashRouter>
      </AuthProvider>
    </ErrorBoundary>
  )
}