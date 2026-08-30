import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { mergeCms } from '../../lib/landingDefaults'
import { LandingView } from '../Landing'
import { Empty, ErrorBox } from '../../components/Ui'

function enabledOnly(rows) {
  return Array.isArray(rows) ? rows.filter((row) => row.enabled !== false) : []
}

const ENDPOINTS = [
  ['site', '/platform/cms/site-settings'],
  ['landing', '/platform/cms/landing'],
  ['features', '/platform/cms/features'],
  ['useCases', '/platform/cms/use-cases'],
  ['testimonials', '/platform/cms/testimonials'],
  ['pricing', '/platform/cms/pricing'],
  ['faqs', '/platform/cms/faqs'],
  ['nav', '/platform/cms/navigation'],
  ['footer', '/platform/cms/footer'],
]

export default function CmsPreview() {
  const [content, setContent] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let mounted = true
    Promise.all(ENDPOINTS.map(([, url]) => api.get(url).catch(() => null)))
      .then((results) => {
        if (!mounted) return
        const data = {}
        ENDPOINTS.forEach(([key], index) => {
          data[key] = results[index]
        })
        const merged = mergeCms(data.site, data.landing, {
          features: enabledOnly(data.features),
          useCases: enabledOnly(data.useCases),
          testimonials: enabledOnly(data.testimonials),
          pricing: enabledOnly(data.pricing),
          faqs: enabledOnly(data.faqs),
          nav: enabledOnly(data.nav),
          footer: enabledOnly(data.footer),
        })
        setContent(merged)
      })
      .catch((err) => mounted && setError(err))
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    if (!content) return undefined
    document.title = `${content.site.site_name} — Preview`
    return () => {
      document.title = 'Platform admin'
    }
  }, [content])

  if (error) {
    return (
      <div className="content">
        <ErrorBox message={error} />
      </div>
    )
  }

  if (!content) {
    return (
      <div className="content">
        <Empty>Loading preview…</Empty>
      </div>
    )
  }

  return (
    <div>
      <div
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 60,
          display: 'flex',
          gap: 12,
          alignItems: 'center',
          padding: '10px 16px',
          background: '#0b1020',
          borderBottom: '1px solid #20293c',
          color: '#cdd5e1',
          fontSize: 13,
        }}
      >
        <span>
          <strong>Draft preview</strong> — edited CMS content. Not visible publicly until the
          landing page is published.
        </span>
        <Link className="btn small" to="/admin/cms/landing">
          Edit copy
        </Link>
        <Link className="btn small primary" to="/admin/cms">
          Back to CMS
        </Link>
      </div>
      <LandingView content={content} />
    </div>
  )
}