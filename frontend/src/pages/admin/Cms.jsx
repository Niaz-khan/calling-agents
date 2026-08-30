import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import {
  Badge,
  Button,
  Card,
  Empty,
  ErrorBox,
  Modal,
  PageTitle,
  formatDate,
  toast,
} from '../../components/Ui'

const SECTION_LINKS = {
  hero: '/admin/cms/landing',
  value_strip: '/admin/cms/landing',
  problem: '/admin/cms/landing',
  features: '/admin/cms/features',
  showcase: '/admin/cms/landing',
  how_works: '/admin/cms/landing',
  website: '/admin/cms/landing',
  phone: '/admin/cms/landing',
  use_cases: '/admin/cms/use-cases',
  analytics: '/admin/cms/landing',
  pricing: '/admin/cms/pricing',
  faq: '/admin/cms/faqs',
  cta: '/admin/cms/landing',
}

const editorLinks = [
  ['Landing copy', '/admin/cms/landing', 'Hero, value strip, problem, how-it-works, website, phone, analytics, CTA copy'],
  ['Branding & SEO', '/admin/cms/site', 'Site name, colors, logo, meta tags, social links'],
  ['Features', '/admin/cms/features', 'Feature cards'],
  ['Use cases', '/admin/cms/use-cases', 'Industry solutions'],
  ['Testimonials', '/admin/cms/testimonials', 'Customer quotes'],
  ['Pricing', '/admin/cms/pricing', 'Pricing plans'],
  ['FAQs', '/admin/cms/faqs', 'Frequently asked questions'],
  ['Navigation', '/admin/cms/navigation', 'Nav bar links'],
  ['Footer', '/admin/cms/footer', 'Footer columns'],
]

function fetchAll() {
  return Promise.all([
    api.get('/platform/cms/landing').catch(() => null),
    api.get('/platform/cms/site-settings').catch(() => null),
    api.get('/platform/cms/versions').catch(() => []),
    api.get('/platform/cms/activity').catch(() => []),
    api.get('/platform/cms/features').catch(() => []),
    api.get('/platform/cms/faqs').catch(() => []),
    api.get('/platform/cms/pricing').catch(() => []),
  ]).then(([landing, site, versions, activity, features, faqs, pricing]) => ({
    landing,
    site,
    versions,
    activity,
    features,
    faqs,
    pricing,
  }))
}

export default function CmsOverview() {
  const { user, platformRole } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [pubOpen, setPubOpen] = useState(false)
  const [preview, setPreview] = useState(null)
  const [publishing, setPublishing] = useState(false)
  const [confirm, setConfirm] = useState(null)
  const [busy, setBusy] = useState(false)

  const canPublish = Boolean(
    user?.is_superuser || platformRole === 'SUPER_ADMIN' || platformRole === 'PLATFORM_ADMIN'
  )

  const reload = () => {
    setError(null)
    setData(null)
    fetchAll().then(setData).catch((err) => setError(err))
  }

  useEffect(() => {
    reload()
  }, [])

  async function toggleSection(index) {
    const current = data.landing
    const next = current.sections.map((section, i) =>
      i === index ? { ...section, enabled: !section.enabled } : section
    )
    setData({ ...data, landing: { ...current, sections: next } })
    try {
      await api.put('/platform/cms/landing', {
        ...current,
        sections: next.map((section) => ({ key: section.key, enabled: section.enabled })),
      })
      toast('Section updated (draft)')
    } catch (err) {
      reload()
      window.alert(err.message || 'Update failed')
    }
  }

  async function openPublishModal() {
    setPubOpen(true)
    setPreview(null)
    try {
      const result = await api.get('/platform/cms/publish/preview')
      setPreview(result.summary || [])
    } catch {
      setPreview([])
    }
  }

  async function confirmPublish() {
    setPublishing(true)
    try {
      const result = await api.post('/platform/cms/publish')
      setPubOpen(false)
      toast(`Published as version ${result.version}`)
      reload()
    } catch (err) {
      window.alert(err.message || 'Publish failed')
    } finally {
      setPublishing(false)
    }
  }

  async function confirmUnpublish() {
    setBusy(true)
    try {
      await api.post('/platform/cms/unpublish')
      setConfirm(null)
      toast('Landing page unpublished')
      reload()
    } catch (err) {
      window.alert(err.message || 'Unpublish failed')
    } finally {
      setBusy(false)
    }
  }

  if (error) {
    return (
      <div>
        <PageTitle title="Website CMS" />
        <ErrorBox message={error} onRetry={reload} />
      </div>
    )
  }

  if (!data) {
    return (
      <div>
        <PageTitle title="Website CMS" />
        <Empty>Loading…</Empty>
      </div>
    )
  }

  const { landing, versions, activity } = data
  const published = landing.is_published
  const current = versions.find((version) => version.is_current)
  const enabledCount = Array.isArray(landing.sections)
    ? landing.sections.filter((section) => section.enabled !== false).length
    : 0

  return (
    <div>
      <PageTitle
        title="Website CMS"
        subtitle="Edit drafts, preview, then publish — the public site only ever shows published content."
        actions={
          <>
            <Link className="btn" to="/admin/cms/preview">
              Preview draft
            </Link>
            <Link className="btn" to="/admin/cms/versions">
              Versions
            </Link>
            {canPublish ? (
              <Button className="primary" onClick={openPublishModal}>
                Publish
              </Button>
            ) : null}
          </>
        }
      />

      <div className="grid three stat-grid">
        <div className="meta-stat">
          <div className="val">
            <Badge variant={published ? 'success' : 'warn'}>{published ? 'Published' : 'Unpublished'}</Badge>
          </div>
          <div className="lab">
            {published && current
              ? `Live since v${current.number} — ${formatDate(current.published_at)}`
              : 'The public site is hidden until you publish'}
          </div>
        </div>
        <div className="meta-stat">
          <div className="val">
            {current ? `v${current.number}` : '—'}
            <div className="lab muted">{current && current.published_by ? `by ${current.published_by}` : 'No version published'}</div>
          </div>
          <div className="lab">Latest version</div>
        </div>
        <div className="meta-stat">
          <div className="val">
            {enabledCount}
            <span className="muted"> / {landing.sections.length}</span>
          </div>
          <div className="lab">Sections enabled</div>
        </div>
        <div className="meta-stat">
          <div className="val">{data.features.length}</div>
          <div className="lab">Features</div>
        </div>
        <div className="meta-stat">
          <div className="val">{data.faqs.length}</div>
          <div className="lab">FAQs</div>
        </div>
        <div className="meta-stat">
          <div className="val">{data.pricing.length}</div>
          <div className="lab">Pricing plans</div>
        </div>
      </div>

      <Card title="Publishing" actions={<Badge variant={published ? 'success' : 'warn'}>{published ? 'Published' : 'Unpublished'}</Badge>}>
        <p className="muted">
          Saving always edits the <strong>draft</strong>. Use <strong>Preview draft</strong> to see
          it, then <strong>Publish</strong> to promote it atomically and create a new version.
          Restore any earlier version from the Versions page.
        </p>
        {canPublish && (
          <div className="form-actions">
            <Button className="primary" onClick={openPublishModal}>
              Publish changes
            </Button>
            <Button onClick={() => setConfirm({ message: 'Take the public website down? Published history is kept and can be restored.' })}>
              Unpublish
            </Button>
          </div>
        )}
      </Card>

      <Card title="Sections">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Section</th>
                <th>Content</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {landing.sections.map((section, index) => (
                <tr key={section.key}>
                  <td>
                    <strong>{section.label}</strong>
                  </td>
                  <td>
                    <Link to={SECTION_LINKS[section.key]}>Edit content</Link>
                  </td>
                  <td>
                    <label className="switch">
                      <input
                        type="checkbox"
                        checked={section.enabled !== false}
                        onChange={() => toggleSection(index)}
                      />
                      <span />
                    </label>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Editors">
        <div className="grid two">
          {editorLinks.map(([label, to, hint]) => (
            <div className="meta-stat" key={to} style={{ cursor: 'pointer' }}>
              <Link to={to} style={{ textDecoration: 'none' }}>
                <div className="val small">{label}</div>
                <div className="lab">{hint}</div>
              </Link>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Recent activity" actions={<Link className="btn" to="/admin/cms/versions">Versions</Link>}>
        {activity.length === 0 ? (
          <Empty>Nothing logged yet.</Empty>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <tbody>
                {activity.slice(0, 10).map((entry) => (
                  <tr key={entry.id}>
                    <td>
                      <Badge variant={entry.action === 'Published' ? 'success' : ''}>{entry.action}</Badge>
                    </td>
                    <td>{entry.resource}</td>
                    <td>{entry.actor || '—'}</td>
                    <td className="muted">{formatDate(entry.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal open={pubOpen} onClose={() => setPubOpen(false)} title="Publish changes">
        <p className="muted">
          You are about to publish the current draft. This creates a new version snapshot and
          atomically replaces what the public site serves.
        </p>
        {preview === null ? (
          <Empty>Computing summary…</Empty>
        ) : (
          <div style={{ margin: '12px 0' }}>
            <strong>Summary</strong>
            <ul className="breakdown">
              {(preview.length ? preview : ['No draft changes']).map((line) => (
                <li key={line}>
                  <span>{line}</span>
                  <strong />
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="form-actions">
          <Button onClick={() => setPubOpen(false)}>Cancel</Button>
          <Button className="primary" onClick={confirmPublish} disabled={publishing} loading={publishing}>
            {publishing ? 'Publishing…' : 'Publish now'}
          </Button>
        </div>
      </Modal>

      <Modal open={Boolean(confirm)} onClose={() => setConfirm(null)} title="Confirm action">
        <p>{confirm?.message}</p>
        <div className="form-actions">
          <Button onClick={() => setConfirm(null)}>Cancel</Button>
          <Button className="danger" onClick={confirmUnpublish} disabled={busy} loading={busy}>
            Continue
          </Button>
        </div>
      </Modal>
    </div>
  )
}