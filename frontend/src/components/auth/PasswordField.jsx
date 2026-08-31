import { useState } from 'react'
import { EyeIcon, EyeOffIcon } from '../icons'

export default function PasswordField({ id, label, value, onChange, autoComplete, minLength }) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="field">
      <label className="field-label" htmlFor={id}>
        {label}
      </label>
      <div className="auth-pass">
        <input
          id={id}
          className="input"
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete={autoComplete}
          minLength={minLength}
          required
        />
        <button
          type="button"
          className="auth-pass-toggle"
          aria-label={visible ? 'Hide password' : 'Show password'}
          aria-pressed={visible}
          onClick={() => setVisible((v) => !v)}
        >
          {visible ? <EyeOffIcon width={17} height={17} /> : <EyeIcon width={17} height={17} />}
        </button>
      </div>
    </div>
  )
}