import { Field } from '../Ui'
import PasswordField from './PasswordField'

export default function LoginForm({
  email,
  password,
  error,
  submitting,
  onEmail,
  onPassword,
  onSubmit,
  onSwitch,
}) {
  return (
    <form className="auth-form" onSubmit={onSubmit}>
      <header className="auth-form-head">
        <h2>Sign in</h2>
        <p>Welcome back to your dashboard</p>
      </header>

      {error && (
        <div className="alert error" role="alert">
          {error}
        </div>
      )}

      <Field label="Email">
        <input
          className="input"
          type="email"
          value={email}
          onChange={(event) => onEmail(event.target.value)}
          autoComplete="email"
          autoFocus
          required
        />
      </Field>

      <PasswordField
        id="login-password"
        label="Password"
        value={password}
        onChange={onPassword}
        autoComplete="current-password"
      />

      <button className="btn primary block auth-submit" type="submit" disabled={submitting}>
        {submitting ? 'Logging in…' : 'Log in'}
      </button>

      <p className="auth-alt">
        Don&apos;t have an account?{' '}
        <button type="button" className="linkish" onClick={onSwitch}>
          Sign up
        </button>
      </p>
    </form>
  )
}