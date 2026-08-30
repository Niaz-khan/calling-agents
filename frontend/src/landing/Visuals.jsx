/* Pure-markup product visuals for the landing page. No API calls. */

import {
  PhoneIcon,
  CheckIcon,
  CalendarIcon,
  UsersIcon,
  ChartIcon,
  AgentIcon,
  SparkIcon,
} from '../components/icons'

function Wave() {
  return (
    <span className="l-wave" aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
      <i />
      <i />
    </span>
  )
}

export function HeroVisual() {
  return (
    <div className="l-hero-visual">
      <div className="l-visual-glow" aria-hidden="true" />
      <div className="l-window">
        <div className="l-window-bar">
          <span className="l-dot" />
          <span className="l-dot" />
          <span className="l-dot" />
          <span className="l-window-title">AI Call Agent</span>
          <span className="l-window-right">
            <span className="l-live-pill">Live</span>
          </span>
        </div>
        <div className="l-dash">
          <div className="l-dash-panel">
            <div className="l-panel-title">Agents · Front desk</div>
            <div className="l-call-row">
              <span className="l-call-ico">
                <PhoneIcon width={16} height={16} />
              </span>
              <span className="l-call-meta">
                <span className="l-call-name">Incoming call · +1 415 …2041</span>
                <span className="l-call-sub">AI agent answering</span>
              </span>
              <Wave />
            </div>
            <div className="l-chat">
              <span className="l-bubble user">Hi — I need a cleaning appointment tomorrow.</span>
              <span className="l-bubble ai">Of course. Let me check availability for you.</span>
              <span className="l-bubble tool">check_appointment_availability → available</span>
              <span className="l-bubble ai">Tomorrow at 3 PM is open. Want me to book it?</span>
              <span className="l-bubble user">Yes please.</span>
              <span className="l-bubble tool">book_appointment → confirmed</span>
            </div>
          </div>
          <div className="l-dash-panel">
            <div className="l-panel-title">Customer</div>
            <div className="l-customer">
              <div className="l-field">
                <span>Name</span>
                <strong>Amina R.</strong>
              </div>
              <div className="l-field">
                <span>Phone</span>
                <strong>+1 415 555 2041</strong>
              </div>
              <div className="l-field">
                <span>Returning</span>
                <strong>Yes · 3 visits</strong>
              </div>
              <div className="l-field">
                <span>Last visit</span>
                <strong>Jun 12</strong>
              </div>
              <div className="l-booked">
                <CheckIcon width={15} height={15} />
                Appointment booked · Tue 3:00 PM
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function WebsiteEmbedVisual() {
  return (
    <div style={{ display: 'grid', gap: 14 }}>
      <div className="l-mock-site">
        <div className="l-ms-top">
          <strong style={{ fontSize: 13 }}>Clearwater Dental</strong>
          <div className="l-ms-nav">
            <span>Services</span>
            <span>Team</span>
            <span>Contact</span>
          </div>
        </div>
        <div className="l-ms-hero">
          <h3 style={{ fontSize: 22, margin: '0 0 8px' }}>
            Gentle, modern dental care
          </h3>
          <p style={{ fontSize: 13.5, lineHeight: 1.5 }}>
            Same-day emergencies welcome. Book visits online or talk to our team.
          </p>
          <p style={{ fontSize: 12, opacity: 0.8 }}>Mon–Fri · 8:00–18:00</p>
          <div className="l-widget-float">
            <div className="l-widget-head">
              <span>Welcome to Clearwater 👋</span>
            </div>
            <div className="l-widget-bubble">Hi! I can book an appointment or answer questions. What can I help with?</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function SnippetCard() {
  return (
    <div className="l-snippet-card">
      <div className="l-code">
        <div>
          <span className="ln">{'<script'}</span>
          <span className="kw">{' src='}</span>
          <span className="st">{'"https://calls.yourdomain.com/widget.js"'}</span>
          <span className="ln">{'></script>'}</span>
        </div>
        <div>
          <span className="kw">{'window.AICallAgent'}</span>
          <span className="ln">{' = '}</span>
          <span className="st">{'`'}</span>
          <span className="ln">{'init('}</span>
          <span className="st">{'pub_…'}</span>
          <span className="ln">{')'}</span>
        </div>
      </div>
    </div>
  )
}

export function PhoneWave() {
  return (
    <span className="l-phone-wave" aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
      <i />
    </span>
  )
}

export function PhoneVisual({ status = 'Booking your appointment', name = '+1 415 555 2041' }) {
  return (
    <div className="l-phone">
      <div className="l-phone-notch" />
      <div className="l-phone-screen">
        <span className="l-phone-avatar">
          <PhoneIcon width={26} height={26} />
        </span>
        <div className="l-phone-name">{name}</div>
        <div className="l-phone-status">{status}</div>
        <PhoneWave />
        <span className="l-phone-tag">Transferred to Monica</span>
      </div>
    </div>
  )
}

export function ShowcaseVisual() {
  const cards = [
    {
      title: 'Calls',
      icon: <PhoneIcon width={14} height={14} />,
      rows: [
        { label: 'Today', num: '18' },
        { label: 'Completed', num: '81%' },
        { label: 'Transfers', num: '4' },
      ],
      bar: 78,
    },
    {
      title: 'Customers',
      icon: <UsersIcon width={14} height={14} />,
      rows: [
        { label: 'Total', num: '342' },
        { label: 'New this week', num: '26' },
        { label: 'Returning', num: '44%' },
      ],
      bar: 62,
    },
    {
      title: 'Appointments',
      icon: <CalendarIcon width={14} height={14} />,
      rows: [
        { label: 'Scheduled', num: '57' },
        { label: 'Booked by AI', num: '39' },
        { label: 'No-show', num: '6%' },
      ],
      bar: 55,
    },
    {
      title: 'Agent',
      icon: <AgentIcon width={14} height={14} />,
      rows: [
        { label: 'Active', num: '2' },
        { label: 'Deployments', num: '3' },
        { label: 'Knowledge', num: '5 docs' },
      ],
      bar: 40,
    },
    {
      title: 'Analytics',
      icon: <ChartIcon width={14} height={14} />,
      rows: [
        { label: 'Avg duration', num: '3m 12s' },
        { label: 'Tool calls', num: '412' },
        { label: 'Outcomes', num: '8' },
      ],
      bar: 88,
    },
  ]
  return (
    <div className="l-showcase">
      {cards.map((card) => (
        <div className="l-showcase-card" key={card.title}>
          <div className="l-panel-title">
            <span>{card.title}</span>
            {card.icon}
          </div>
          {card.rows.map((row) => (
            <div className="l-sc-row" key={row.label}>
              <span>{row.label}</span>
              <span className="num">{row.num}</span>
            </div>
          ))}
          <div className="l-sc-bar">
            <i style={{ width: `${card.bar}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

export function AnalyticsVisual() {
  const bars = [34, 48, 40, 62, 55, 74, 68, 82, 76, 92, 86, 96]
  return (
    <div className="l-ana-chart">
      <div className="l-panel-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span>Conversations · last 12 weeks</span>
        <span style={{ color: '#34d399' }}>+28%</span>
      </div>
      <div className="l-ana-bars">
        {bars.map((h, i) => (
          <i key={i} style={{ height: `${h}%` }} />
        ))}
      </div>
      <div className="l-ana-legend">
        <span>Apr</span>
        <span>May</span>
        <span>Jun</span>
        <span>Jul</span>
      </div>
    </div>
  )
}

export function MiniBarVisual() {
  return (
    <div className="l-mini">
      <div className="l-mini-header">
        <span>Calls this week</span>
        <span style={{ color: '#34d399' }}>+24%</span>
      </div>
      <div className="l-mini-bars">
        <i style={{ height: '45%' }} />
        <i style={{ height: '60%' }} />
        <i style={{ height: '38%' }} />
        <i style={{ height: '72%' }} />
        <i style={{ height: '55%' }} />
        <i style={{ height: '88%' }} />
        <i style={{ height: '66%' }} />
      </div>
    </div>
  )
}

const featureMini = {
  phone: <MiniBarVisual />,
  analytics: <MiniBarVisual />,
  calendar: (
    <div className="l-mini">
      <div className="l-mini-header">
        <span>Tomorrow</span>
        <SparkIcon width={14} height={14} />
      </div>
      <div className="l-booked" style={{ marginTop: 8 }}>
        <CheckIcon width={14} height={14} /> 3:00 PM · booked by agent
      </div>
    </div>
  ),
}

export function FeatureVisual({ icon }) {
  return featureMini[icon] || null
}