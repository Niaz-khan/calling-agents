import AuthLogo from './AuthLogo'
import { PhoneIcon, SparkIcon, CheckIcon } from '../icons'

const STEPS = [
  { icon: PhoneIcon, text: 'Customer reaches your business' },
  { icon: SparkIcon, text: 'Your AI agent picks up' },
  { icon: CheckIcon, text: 'Bookings, answers and leads' },
]

export default function AuthBrandPanel({ brand }) {
  return (
    <div className="auth-brand-panel">
      <span className="auth-brand-glow" aria-hidden="true" />
      <AuthLogo brand={brand} />

      <div className="auth-brand-copy">
        <p className="auth-brand-eyebrow">AI CALL AGENT</p>
        <h1>AI-powered conversations that work for your business.</h1>
        <p>
          Let your AI agent answer calls, handle conversations, and book
          appointments while your team focuses on the business.
        </p>
      </div>

      <ul className="auth-brand-steps" aria-hidden="true">
        {STEPS.map(({ icon: Icon, text }) => (
          <li key={text}>
            <span className="auth-step-ico">
              <Icon width={14} height={14} />
            </span>
            {text}
          </li>
        ))}
      </ul>
    </div>
  )
}