import { useEffect, useState } from 'react'
import { loadPublicSite } from '../lib/cms'
import { defaultCollections } from '../lib/landingDefaults'
import {
  LandingNav,
  AnnouncementBar,
  LandingHero,
  ValueStrip,
  ProblemSection,
  FeaturesSection,
  ShowcaseSection,
  HowItWorksSection,
  WebsiteSection,
  PhoneSection,
  ApiSection,
  UseCasesSection,
  AnalyticsSection,
  PricingSection,
  FaqSection,
  FinalCta,
  LandingFooter,
  useReveal,
} from '../landing/Sections'
import { Loading } from '../components/Ui'

function shade(hex, percent) {
  const value = hex?.replace('#', '') || '2E7CF6'
  const num = parseInt(value.length === 3 ? value.split('').map((c) => c + c).join('') : value, 16)
  let r = (num >> 16) & 255
  let g = (num >> 8) & 255
  let b = num & 255
  r = Math.max(0, Math.min(255, Math.round(r * (1 - percent))))
  g = Math.max(0, Math.min(255, Math.round(g * (1 - percent))))
  b = Math.max(0, Math.min(255, Math.round(b * (1 - percent))))
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`
}

export function LandingView({ content }) {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [activeCase, setActiveCase] = useState(defaultCollections.useCases[0].id)
  const [openFaq, setOpenFaq] = useState(0)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useReveal(true)

  const { site, landing } = content
  const sections = landing.sections || []
  const theme = {
    '--l-primary': site.primary_color || '#2E7CF6',
    '--l-primary-dark': shade(site.primary_color, 0.28),
    '--l-secondary': site.secondary_color || '#14B8A6',
    '--l-font': `'${site.font_family || 'Inter'}', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`,
  }

  return (
    <div className="landing" style={theme}>
      <AnnouncementBar site={site} />
      <LandingNav
        site={site}
        nav={content.nav}
        scrolled={scrolled}
        open={menuOpen}
        setOpen={setMenuOpen}
      />
      <main className="landing-bg">
        {sections.map((section) => {
          if (section.enabled === false) return null
          switch (section.key) {
            case 'hero':
              return landing.hero_enabled === false ? null : (
                <LandingHero key={section.key} landing={landing} />
              )
            case 'value_strip':
              return <ValueStrip key={section.key} landing={landing} />
            case 'problem':
              return <ProblemSection key={section.key} landing={landing} />
            case 'features':
              return <FeaturesSection key={section.key} landing={landing} collections={content} />
            case 'showcase':
              return <ShowcaseSection key={section.key} landing={landing} />
            case 'how_works':
              return <HowItWorksSection key={section.key} landing={landing} />
            case 'website':
              return <WebsiteSection key={section.key} landing={landing} />
            case 'phone':
              return <PhoneSection key={section.key} landing={landing} />
            case 'api':
              return <ApiSection key={section.key} landing={landing} />
            case 'use_cases':
              return (
                <UseCasesSection
                  key={section.key}
                  landing={landing}
                  useCases={content.useCases}
                  activeCase={activeCase}
                  setActiveCase={setActiveCase}
                />
              )
            case 'analytics':
              return <AnalyticsSection key={section.key} landing={landing} />
            case 'pricing':
              return (
                <PricingSection key={section.key} landing={landing} pricing={content.pricing} />
              )
            case 'faq':
              return (
                <FaqSection
                  key={section.key}
                  landing={landing}
                  faqs={content.faqs}
                  openFaq={openFaq}
                  setOpenFaq={setOpenFaq}
                />
              )
            case 'cta':
              return <FinalCta key={section.key} landing={landing} />
            default:
              return null
          }
        })}
      </main>
      <LandingFooter site={site} footer={content.footer} />
    </div>
  )
}

export default function Landing() {
  const [content, setContent] = useState(null)

  useEffect(() => {
    let mounted = true
    loadPublicSite().then((data) => {
      if (!mounted) return
      setContent(data)
    })
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    if (!content) return
    const { site } = content
    const title = site.meta_title ? site.meta_title : `${site.site_name} — AI Call Agent`
    document.title = title
    const description = site.meta_description || ''
    const origin = window.location.origin
    const ogImage = site.logo || ''
    const created = []

    const upsert = (selector, attribute, value) => {
      let el = document.head.querySelector(selector)
      if (!el) {
        el = document.createElement('meta')
        el.setAttribute(attribute, value)
        document.head.appendChild(el)
        created.push(el)
      } else {
        el.setAttribute(attribute, value)
      }
    }

    upsert('meta[name="description"]', 'content', description)
    upsert('meta[property="og:title"]', 'content', title)
    upsert('meta[property="og:description"]', 'content', description)
    upsert('meta[property="og:type"]', 'content', 'website')
    upsert('meta[property="og:url"]', 'content', `${origin}/`)
    upsert('meta[name="twitter:card"]', 'content', 'summary')
    upsert('meta[name="twitter:title"]', 'content', title)
    upsert('meta[name="twitter:description"]', 'content', description)
    upsert('meta[name="robots"]', 'content', 'index, follow')
    if (ogImage) upsert('meta[property="og:image"]', 'content', ogImage)

    let canonical = document.head.querySelector('link[rel="canonical"]')
    if (!canonical) {
      canonical = document.createElement('link')
      canonical.setAttribute('rel', 'canonical')
      document.head.appendChild(canonical)
      created.push(canonical)
    }
    canonical.setAttribute('href', `${origin}/`)

    return () => created.forEach((el) => el.remove())
  }, [content])

  if (!content) {
    return (
      <div className="landing" style={{ minHeight: '100vh' }}>
        <Loading />
      </div>
    )
  }

  return <LandingView content={content} />
}