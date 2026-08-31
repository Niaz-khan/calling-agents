import { Field } from '../Ui'
import PasswordField from './PasswordField'

export default function RegisterForm({
  fullName,
  email,
  password,
  error,
  submitting,
  onFullName,
  onEmail,
  onPassword,
  onSubmit,
  onSwitch,
}) {
  return (
    <form className="auth-form" onSubmit={onSubmit}>
      <header className="auth-form-head">
        <h2>Create your account</h2>
        <p>Start building your AI workforce</p>
      </header>

      {error && (
        <div className="alert error" role="alert">
          {error}
        </div>
      )}

      <Field label="Full name">
        <input
          className="input"
          value={fullName}
          onChange={(event) => onFullName(event.target.value)}
          autoComplete="name"
          required
        />
      </Field>

      <Field label="Email">
        <input
          className="input"
          type="email"
          value={email}
          onChange={(event) => onEmail(event.target.value)}
          autoComplete="email"
          required
        />
      </Field>

      <PasswordField
        id="register-password"
        label="Password"
        value={password}
        onChange={onPassword}
        autoComplete="new-password"
        minLength={8}
      />

      <button className="btn primary block auth-submit" type="submit" disabled={submitting}>
        {submitting ? 'Creating account…' : 'Create account'}
      </button>

      <p className="auth-alt">
        Already have an account?{' '}
        <button type="button" className="linkish" onClick={onSwitch}>
          Log in
        </button>
      </p>
    </form>
  )
}