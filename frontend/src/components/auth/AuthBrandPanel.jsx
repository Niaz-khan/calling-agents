import AuthLogo from './AuthLogo'
import { PhoneIcon, SparkIcon, CheckIcon } from '../icons'

const COPY = {
  login: {
    eyebrow: 'Welcome back',
    headline: 'Your AI employee for every customer conversation.',
    support:
      'Sign in to manage your agents, calls, customers, and appointments — everything from one place.',
  },
  register: {
    eyebrow: 'Get started',
    headline: 'Build your AI workforce',
    support:
      'Let AI handle calls, conversations, appointments, and customer questions while your team focuses on the business.',
  },
}

const STEPS = [
  { icon: PhoneIcon, text: 'Customer reaches your business' },
  { icon: SparkIcon, text: 'Your AI agent picks up' },
  { icon: CheckIcon, text: 'Bookings, answers and leads' },
]

export default function AuthBrandPanel({ brand, mode }) {
  const copy = COPY[mode]
  return (
    <div className="auth-brand-panel">
      <AuthLogo brand={brand} />

      <div className="auth-brand-copy">
        <p className="auth-brand-eyebrow">{copy.eyebrow}</p>
        <h1>{copy.headline}</h1>
        <p>{copy.support}</p>
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