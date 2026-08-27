import { Component } from 'react'
import { HashRouter, Route, Routes, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth'
import { Loading } from './components/Ui'
import { setToken } from './api'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import Calls from './pages/Calls'
import CallDetail from './pages/CallDetail'
import Customers from './pages/Customers'
import Appointments from './pages/Appointments'
import PhoneNumbers from './pages/PhoneNumbers'
import Knowledge from './pages/Knowledge'

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

function Protected() {
  const { user, loading } = useAuth()

  if (loading) return <Loading />
  if (!user) return <Navigate to="/login" replace />

  return (
    <Layout>
      <Outlet />
    </Layout>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <HashRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route element={<Protected />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/agents" element={<Agents />} />
              <Route path="/calls" element={<Calls />} />
              <Route path="/calls/:callId" element={<CallDetail />} />
              <Route path="/customers" element={<Customers />} />
              <Route path="/appointments" element={<Appointments />} />
              <Route path="/phone-numbers" element={<PhoneNumbers />} />
              <Route path="/knowledge" element={<Knowledge />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </HashRouter>
      </AuthProvider>
    </ErrorBoundary>
  )
}