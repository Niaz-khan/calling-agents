import { Link } from 'react-router-dom'

export default function AuthFormPanel({ mode, onSwitch, children }) {
  const isLogin = mode === 'login'
  return (
    <div className="auth-form-panel">
      <div className="auth-form-box">
        <div
          className={`auth-seg${isLogin ? '' : ' is-reg'}`}
          role="tablist"
          aria-label="Authentication mode"
        >
          <span className="auth-seg-pill" aria-hidden="true" />
          <button
            type="button"
            role="tab"
            aria-selected={isLogin}
            className={isLogin ? 'active' : ''}
            onClick={() => onSwitch('login')}
          >
            Sign in
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={!isLogin}
            className={!isLogin ? 'active' : ''}
            onClick={() => onSwitch('register')}
          >
            Create account
          </button>
        </div>

        {children}

        <p className="auth-form-foot">
          <Link to="/" className="auth-back">
            ← Back to website
          </Link>
        </p>
      </div>
    </div>
  )
}