import { useEffect, useState } from 'react'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { defaultSite } from '../../lib/landingDefaults'
import AuthBrandPanel from './AuthBrandPanel'
import AuthFormPanel from './AuthFormPanel'
import LoginForm from './LoginForm'
import RegisterForm from './RegisterForm'

function useBranding() {
  const [brand, setBrand] = useState(defaultSite)
  useEffect(() => {
    let mounted = true
    api
      .get('/public/site-config')
      .then((data) => {
        if (mounted && data) setBrand({ ...defaultSite, ...data })
      })
      .catch(() => {})
    return () => {
      mounted = false
    }
  }, [])
  return brand
}

export default function AuthLayout() {
  const { user, login, register } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const brand = useBranding()

  const isLogin = pathname.includes('/login')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to="/" replace />

  const switchMode = (next) => {
    if (submitting) return
    setError('')
    navigate(next === 'login' ? '/login' : '/register')
  }

  const fail = (err) => {
    setError(err?.message || 'Something went wrong')
    setSubmitting(false)
  }

  async function handleLogin(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      fail(err)
    }
  }

  async function handleRegister(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await register({ full_name: fullName, email, password })
      navigate('/')
    } catch (err) {
      fail(err)
    }
  }

  const theme = {
    '--l-primary': brand.primary_color || '#2E7CF6',
    '--primary': brand.primary_color || '#2E7CF6',
    '--secondary': brand.secondary_color || '#14B8A6',
    '--auth-font': `'${brand.font_family || 'Inter'}', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`,
  }

  return (
    <div className="auth-shell" style={theme}>
      <div className="auth-swap">
        <section
          className={`auth-screen login-side${isLogin ? ' active' : ''}`}
          aria-hidden={!isLogin}
        >
          <AuthBrandPanel brand={brand} mode="login" />
          <AuthFormPanel mode="login" onSwitch={switchMode}>
            <LoginForm
              email={email}
              password={password}
              error={error}
              submitting={submitting}
              onEmail={setEmail}
              onPassword={setPassword}
              onSubmit={handleLogin}
              onSwitch={() => switchMode('register')}
            />
          </AuthFormPanel>
        </section>

        <section
          className={`auth-screen register-side${!isLogin ? ' active' : ''}`}
          aria-hidden={isLogin}
        >
          <AuthFormPanel mode="register" onSwitch={switchMode}>
            <RegisterForm
              fullName={fullName}
              email={email}
              password={password}
              error={error}
              submitting={submitting}
              onFullName={setFullName}
              onEmail={setEmail}
              onPassword={setPassword}
              onSubmit={handleRegister}
              onSwitch={() => switchMode('login')}
            />
          </AuthFormPanel>
          <AuthBrandPanel brand={brand} mode="register" />
        </section>
      </div>
      <Outlet />
    </div>
  )
}