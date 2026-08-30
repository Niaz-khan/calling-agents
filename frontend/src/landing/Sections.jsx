import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  PhoneIcon,
  WebsiteIcon,
  CalendarIcon,
  KnowledgeIcon,
  UsersIcon,
  TransferIcon,
  ChartIcon,
  CheckIcon,
  ArrowRightIcon,
  MenuIcon,
  CloseIcon,
  SparkIcon,
} from '../components/icons'
import {
  HeroVisual,
  WebsiteEmbedVisual,
  SnippetCard,
  PhoneVisual,
  ShowcaseVisual,
  AnalyticsVisual,
  ApiVisual,
} from './Visuals'

export function scrollToId(id) {
  if (!id || id === 'top') {
    window.scrollTo({ top: 0, behavior: 'smooth' })
    return
  }
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

export function useReveal(ready = true) {
  useEffect(() => {
    if (!ready) return undefined
    const els = Array.from(document.querySelectorAll('.landing .l-reveal'))
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible')
            io.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.12 }
    )
    els.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [ready])
}

function NavLink({ to = 'top', children, className = '' }) {
  return (
    <a
      href={to === 'top' ? '#' : `#${to}`}
      onClick={(e) => {
        e.preventDefault()
        scrollToId(to)
      }}
      className={className}
    >
      {children}
    </a>
  )
}

export function LandingNav({ site, nav, scrolled, open, setOpen }) {
  return (
    <header className={`l-nav${scrolled ? ' scrolled' : ''}`}>
      <div className="l-container">
        <div className="l-nav-inner">
          <NavLink to="top" className="l-logo">
            <span className="l-logo-mark">A</span>
            {site.site_name}
          </NavLink>
          <nav className="l-nav-links">
            {nav.map((item) => (
              <NavLink key={item.id || item.label} to={item.url?.replace(/^#/, '') || 'top'}>
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="l-nav-actions">
            <Link className="l-btn ghost" to="/login">
              Log in
            </Link>
            <Link className="l-btn lg" to="/register">
              Get started
            </Link>
            <button
              className="l-hamburger"
              aria-label="Toggle menu"
              onClick={() => setOpen(!open)}
            >
              {open ? <CloseIcon width={18} height={18} /> : <MenuIcon width={18} height={18} />}
            </button>
          </div>
        </div>
        <div className={`l-mobile-menu${open ? ' open' : ''}`}>
          {nav.map((item) => (
            <NavLink key={item.id || item.label} to={item.url?.replace(/^#/, '') || 'top'}>
              {item.label}
            </NavLink>
          ))}
          <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
            <Link className="l-btn" to="/login" style={{ flex: 1 }}>
              Log in
            </Link>
            <Link className="l-btn primary" to="/register" style={{ flex: 1 }}>
              Get started
            </Link>
          </div>
        </div>
      </div>
    </header>
  )
}

export function AnnouncementBar({ site }) {
  if (!site.announcement_enabled || !site.announcement_text) return null
  return (
    <div className="l-announce">
      <div className="l-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8 }}>
        <span>{site.announcement_text}</span>
      </div>
    </div>
  )
}

export function LandingHero({ landing, accentColor }) {
  return (
    <section className="l-hero" id="top">
      <div className="l-container">
        <span className="l-eyebrow" style={accentColor}>{landing.hero_badge}</span>
        <h1 className="l-heading accent">{landing.hero_title}</h1>
        <p className="l-sub">{landing.hero_subtitle}</p>
        <div className="l-hero-ctas">
          <Link className="l-btn primary lg" to="/register">
            {landing.hero_primary_cta}
            <ArrowRightIcon width={16} height={16} className="l-btn-arrow" />
          </Link>
          <NavLink to="features" className="l-btn lg">
            {landing.hero_secondary_cta}
          </NavLink>
        </div>
        <div className="l-trust">
          <span className="check">
            <CheckIcon width={11} height={11} />
          </span>
          No credit card required
          <span className="check">
            <CheckIcon width={11} height={11} />
          </span>
          Setup in minutes
          <span className="check">
            <CheckIcon width={11} height={11} />
          </span>
          Works while you sleep
        </div>
        <div className="l-reveal">
          <HeroVisual />
        </div>
      </div>
    </section>
  )
}

export function ValueStrip({ landing }) {
  return (
    <section className="l-strip">
      <div className="l-container">
        <div className="l-strip-label">{landing.value_strip_title}</div>
        <div className="l-strip-row">
          {landing.value_strip_items.map((item, i) => (
            <span className="l-strip-item" key={i}>
              <PhoneIcon width={14} height={14} />
              {item}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}

export function ProblemSection({ landing }) {
  return (
    <section className="l-section">
      <div className="l-container">
        <div className="l-center l-reveal">
          <h2 className="l-heading">{landing.problem_title}</h2>
        </div>
        <div className="l-problems-grid">
          {landing.problem_items.map((item, i) => (
            <div className="l-problem l-reveal" key={i}>
              <span className="l-problem-ico">
                <CloseIcon width={18} height={18} />
              </span>
              <div>
                <h3>{item}</h3>
                <p>Time your team could spend growing the business instead.</p>
              </div>
            </div>
          ))}
        </div>
        <div className="l-pivot l-reveal">
          <h2>{landing.solution_title}</h2>
          <p className="l-sub" style={{ margin: '14px auto 0', maxWidth: 640 }}>
            {landing.solution_text}
          </p>
        </div>
      </div>
    </section>
  )
}

const featureIcons = {
  phone: PhoneIcon,
  website: WebsiteIcon,
  calendar: CalendarIcon,
  knowledge: KnowledgeIcon,
  customers: UsersIcon,
  transfer: TransferIcon,
  analytics: ChartIcon,
  outbound: PhoneIcon,
}

export function FeaturesSection({ collections, landing }) {
  const features = collections.features
  const wide = features[0]
  const rest = features.slice(1)
  const FirstIcon = featureIcons[wide.icon] || SparkIcon
  const layout = ['span6', 'span6', 'span4', 'span4', 'span4', 'wide']
  return (
    <section className="l-section alt" id="features">
      <div className="l-container">
        <div className="l-center l-reveal">
          <span className="l-eyebrow">Capabilities</span>
          <h2 className="l-heading">{landing.features_title}</h2>
          <p className="l-sub">{landing.features_subtitle}</p>
        </div>
        <div className="l-feature-grid">
          <div className={`l-feature wide l-reveal`}>
            <div>
              <span className="l-feature-tag">
                <FirstIcon width={13} height={13} />
                Flagship
              </span>
              <div className="l-feature-ico">
                <FirstIcon width={22} height={22} />
              </div>
              <h3>{wide.title}</h3>
              <p>{wide.description}</p>
            </div>
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
          </div>
          {rest.slice(0, 6).map((f, i) => {
            const Icon = featureIcons[f.icon] || SparkIcon
            return (
              <div className={`l-feature ${layout[i] || 'span4'} l-reveal`} key={f.id}>
                <div className="l-feature-ico">
                  <Icon width={22} height={22} />
                </div>
                <h3>{f.title}</h3>
                <p>{f.description}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

export function ShowcaseSection({ landing }) {
  return (
    <section className="l-section">
      <div className="l-container">
        <div className="l-center l-reveal">
          <span className="l-eyebrow">Workspace</span>
          <h2 className="l-heading">{landing.showcase_title}</h2>
          <p className="l-sub">{landing.showcase_subtitle}</p>
        </div>
        <div className="l-reveal">
          <ShowcaseVisual />
        </div>
      </div>
    </section>
  )
}

export function HowItWorksSection({ landing }) {
  return (
    <section className="l-section alt" id="how-it-works">
      <div className="l-container">
        <div className="l-center l-reveal">
          <span className="l-eyebrow">Setup</span>
          <h2 className="l-heading">{landing.how_works_title}</h2>
        </div>
        <div className="l-steps">
          {landing.how_works_steps.map((step, i) => (
            <div className="l-step l-reveal" key={i}>
              <div className="l-step-num">{step.num || String(i + 1).padStart(2, '0')}</div>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export function WebsiteSection({ landing }) {
  return (
    <section className="l-section" id="website">
      <div className="l-container">
        <div className="l-split">
          <div className="l-split-body l-reveal">
            <span className="l-eyebrow">Website</span>
            <h2>{landing.website_section_title}</h2>
            <p>{landing.website_section_text}</p>
            <div className="l-reveal">
              <SnippetCard />
            </div>
          </div>
          <div className="l-reveal">
            <WebsiteEmbedVisual />
          </div>
        </div>
      </div>
    </section>
  )
}

export function PhoneSection({ landing }) {
  return (
    <section className="l-section alt" id="phone">
      <div className="l-container">
        <div className="l-split">
          <div className="l-reveal">
            <PhoneVisual />
          </div>
          <div className="l-split-body l-reveal">
            <span className="l-eyebrow">Phone</span>
            <h2>{landing.phone_section_title}</h2>
            <p>{landing.phone_section_text}</p>
            <div className="l-field">
              <span>Answering</span>
              <strong>24 / 7 · after-hours too</strong>
            </div>
            <div className="l-field">
              <span>Appointments</span>
              <strong>Booked in the calendar</strong>
            </div>
            <div className="l-field">
              <span>Transfer</span>
              <strong>To your team when it matters</strong>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export function ApiSection({ landing }) {
  return (
    <section className="l-section" id="api">
      <div className="l-container">
        <div className="l-split">
          <div className="l-split-body l-reveal">
            <span className="l-eyebrow">API</span>
            <h2>{landing.api_section_title}</h2>
            <p>{landing.api_section_text}</p>
            <div className="l-field">
              <span>Conversation</span>
              <strong>Starts from any app you build</strong>
            </div>
            <div className="l-field">
              <span>Events</span>
              <strong>Streamed back to your stack</strong>
            </div>
            <div className="l-field">
              <span>Scoped</span>
              <strong>Private to your organization</strong>
            </div>
            <NavLink to="features" className="l-btn">
              {landing.api_section_cta}
            </NavLink>
          </div>
          <div className="l-reveal">
            <ApiVisual />
          </div>
        </div>
      </div>
    </section>
  )
}

const caseHighlights = [
  'Answers FAQs day or night',
  'Books appointments in the calendar',
  'Captures contact details',
  'Transfers to your team when needed',
]

export function UseCasesSection({ landing, useCases, activeCase, setActiveCase }) {
  const active = useCases.find((u) => u.id === activeCase) || useCases[0]
  return (
    <section className="l-section" id="use-cases">
      <div className="l-container">
        <div className="l-center l-reveal">
          <span className="l-eyebrow">Solutions</span>
          <h2 className="l-heading">{landing.use_cases_title}</h2>
          <p className="l-sub">{landing.use_cases_subtitle}</p>
        </div>
        <div className="l-tabs" role="tablist">
          {useCases.map((u) => (
            <button
              key={u.id}
              className={`l-tab${u.id === active.id ? ' active' : ''}`}
              onClick={() => setActiveCase(u.id)}
            >
              {u.title}
            </button>
          ))}
        </div>
        <div className="l-cases-card l-reveal">
          <h3>{active.title}</h3>
          <p>{active.description}</p>
          <div className="l-cases-list">
            {caseHighlights.map((h, i) => (
              <div className="l-case-item" key={i}>
                <CheckIcon width={15} height={15} className="tick" />
                {h}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

export function AnalyticsSection({ landing }) {
  const kpis = [
    { val: '4,120', lab: 'Conversations this month' },
    { val: '87%', lab: 'Handled end-to-end by AI' },
    { val: '932', lab: 'Appointments booked' },
    { val: '3m 12s', lab: 'Average call duration' },
  ]
  return (
    <section className="l-section alt" id="analytics">
      <div className="l-container">
        <div className="l-analytics">
          <div className="l-split-body l-reveal">
            <span className="l-eyebrow">Analytics</span>
            <h2>{landing.analytics_title}</h2>
            <p>{landing.analytics_subtitle}</p>
            <div className="l-kpi-grid">
              {kpis.map((k, i) => (
                <div className="l-kpi l-reveal" key={i}>
                  <div className="val">{k.val}</div>
                  <div className="lab">{k.lab}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="l-reveal">
            <AnalyticsVisual />
          </div>
        </div>
      </div>
    </section>
  )
}

export function PricingSection({ landing, pricing }) {
  return (
    <section className="l-section" id="pricing">
      <div className="l-container">
        <div className="l-center l-reveal">
          <span className="l-eyebrow">Pricing</span>
          <h2 className="l-heading">{landing.pricing_title}</h2>
          <p className="l-sub">{landing.pricing_subtitle}</p>
          {landing.pricing_disclaimer ? <p className="l-sub" style={{ marginTop: 8 }}>{landing.pricing_disclaimer}</p> : null}
        </div>
        <div className="l-pricing">
          {pricing.map((plan, i) => (
            <div className={`l-price-card${plan.highlighted ? ' featured' : ''} l-reveal`} key={i}>
              {plan.highlighted ? <span className="l-price-badge">Most popular</span> : null}
              <div className="l-price-name">{plan.name}</div>
              <div className="l-price-desc">{plan.description}</div>
              <div className="l-price-amount">
                {plan.price}
                {plan.billing_period ? <small>/{plan.billing_period}</small> : null}
              </div>
              <ul className="l-price-features">
                {plan.features.map((feature, j) => (
                  <li key={j}>{feature}</li>
                ))}
              </ul>
              <button className="l-btn primary">{plan.cta_text || 'Get started'}</button>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export function FaqSection({ landing, faqs, openFaq, setOpenFaq }) {
  return (
    <section className="l-section alt" id="faq">
      <div className="l-container">
        <div className="l-center l-reveal">
          <span className="l-eyebrow">FAQ</span>
          <h2 className="l-heading">{landing.faq_title}</h2>
        </div>
        <div className="l-faq">
          {faqs.map((faq, i) => (
            <div className={`l-faq-item${openFaq === i ? ' open' : ''} l-reveal`} key={i}>
              <button className="l-faq-q" onClick={() => setOpenFaq(openFaq === i ? -1 : i)}>
                {faq.question}
                <span className="sign">+</span>
              </button>
              <div className="l-faq-a">{faq.answer}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export function FinalCta({ landing }) {
  return (
    <section className="l-final">
      <div className="l-container">
        <h2>{landing.cta_title}</h2>
        <p>{landing.cta_subtitle}</p>
        <div className="l-hero-ctas">
          <Link className="l-btn primary lg" to="/register">
            {landing.cta_primary}
            <ArrowRightIcon width={16} height={16} className="l-btn-arrow" />
          </Link>
          <Link className="l-btn lg" to="/login">
            {landing.cta_secondary}
          </Link>
        </div>
      </div>
    </section>
  )
}

export function LandingFooter({ site, footer }) {
  return (
    <footer className="l-footer">
      <div className="l-container">
        <div className="l-footer-grid">
          <div className="l-footer-col l-footer-brand">
            <span className="l-logo" style={{ fontSize: 15 }}>
              <span className="l-logo-mark">A</span>
              {site.site_name}
            </span>
            <p>{site.meta_description}</p>
          </div>
          {footer.map((col) => (
            <div className="l-footer-col" key={col.title}>
              <h4>{col.title}</h4>
              {col.links.map((link) => (
                <NavLink key={link.label} to={link.url?.replace(/^#/, '') || 'top'}>
                  {link.label}
                </NavLink>
              ))}
            </div>
          ))}
        </div>
        <div className="l-footer-bottom">
          <span>© {new Date().getFullYear()} {site.site_name}. All rights reserved.</span>
          <span>Built with privacy in mind — data owned by your organization.</span>
        </div>
      </div>
    </footer>
  )
}