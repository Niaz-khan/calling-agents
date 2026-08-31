import { useEffect, useRef, useState } from 'react'
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
  const [leavingFor, setLeavingFor] = useState(null)
  const prevIsLogin = useRef(isLogin)
  const reducedMotion =
    typeof window !== 'undefined' &&
    !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

  useEffect(() => {
    if (isLogin === prevIsLogin.current) return
    const outgoing = prevIsLogin.current
    prevIsLogin.current = isLogin
    if (reducedMotion) {
      setLeavingFor(null)
      return
    }
    document.documentElement.classList.add('auth-transitioning')
    setLeavingFor(outgoing)
    const t = window.setTimeout(() => {
      setLeavingFor(null)
      document.documentElement.classList.remove('auth-transitioning')
    }, 820)
    return () => window.clearTimeout(t)
  }, [isLogin, reducedMotion])

  if (user) return <Navigate to={signedInPath(user)} replace />

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
      const account = await login(email, password)
      navigate(signedInPath(account))
    } catch (err) {
      fail(err)
    }
  }

  async function handleRegister(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const account = await register({ full_name: fullName, email, password })
      navigate(signedInPath(account))
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

  const dirClass = leavingFor === true ? 'from-login' : leavingFor === false ? 'from-register' : ''
  const maybeTransition = reducedMotion ? '' : ' may-transition'

  const signedInPath = (account) => {
    const organizations = (account && account.organizations) || []
    const isPlatform = (account && (account.is_superuser || account.platform_role)) || false
    return isPlatform && organizations.length === 0 ? '/admin' : '/app'
  }

  return (
    <div
      className={`auth-shell${isLogin ? ' is-login' : ' is-register'}${dirClass ? ` auth-${dirClass}` : ''}`}
      style={theme}
    >
      <div className="auth-frame">
        {/* ONE persistent branding panel. It carries the logo, AI visual and
            messaging and physically travels across the shared canvas — from the
            LEFT in login mode to the RIGHT in register mode — as a single
            continuous element that never unmounts. */}
        <div className="auth-zone auth-brand-zone" aria-hidden={false}>
          <AuthBrandPanel brand={brand} />
        </div>

        {/* The form region is part of the same composition. It travels to the
            opposite side (RIGHT in login mode, LEFT in register mode) while its
            internal content crossfades from the LoginForm to the SignupForm. */}
        <div className="auth-zone auth-form-zone">
          <div className="auth-form-stack">
            <div
              className={`auth-form-slot${isLogin ? ' active' : ''}${maybeTransition}`}
              aria-hidden={!isLogin}
            >
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
            </div>
            <div
              className={`auth-form-slot${!isLogin ? ' active' : ''}${maybeTransition}`}
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
            </div>
          </div>
        </div>
      </div>
      <Outlet />
    </div>
  )
}