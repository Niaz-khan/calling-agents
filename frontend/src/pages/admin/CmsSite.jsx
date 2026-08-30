import { useEffect, useState } from 'react'
import { api } from '../../api'
import {
  Button,
  Card,
  Empty,
  ErrorBox,
  Field,
  Input,
  PageTitle,
  Select,
  Textarea,
  toast,
} from '../../components/Ui'
import { defaultSite } from '../../lib/landingDefaults'

const LINK_LINES = ['social_links']

export default function CmsSite() {
  const [form, setForm] = useState(null)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api
      .get('/platform/cms/site-settings')
      .then((result) => {
        const base = { ...defaultSite, ...result }
        const next = { ...base }
        for (const key of LINK_LINES) {
          next[key] = (base[key] || []).map((link) => `${link.label} = ${link.url}`).join('\n')
        }
        setForm(next)
      })
      .catch((err) => setError(err))
  }, [])

  function set(key, value) {
    setForm((previous) => ({ ...previous, [key]: value }))
  }

  async function save(event) {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = { ...form }
      for (const key of LINK_LINES) {
        payload[key] = (form[key] || '')
          .split('\n')
          .map((line) => line.trim())
          .filter(Boolean)
          .map((line) => {
            const separator = line.indexOf('=')
            if (separator < 0) return { label: line, url: '#' }
            return { label: line.slice(0, separator).trim(), url: line.slice(separator + 1).trim() }
          })
      }
      await api.put('/platform/cms/site-settings', payload)
      toast('Site settings saved')
    } catch (err) {
      window.alert(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (error) {
    return (
      <div>
        <PageTitle title="Branding & SEO" />
        <ErrorBox message={error} />
      </div>
    )
  }

  if (!form) {
    return (
      <div>
        <PageTitle title="Branding & SEO" />
        <Empty>Loading…</Empty>
      </div>
    )
  }

  return (
    <div>
      <PageTitle
        title="Branding & SEO"
        subtitle="Site identity, colors and search metadata."
        actions={
          <Button className="primary" onClick={save} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </Button>
        }
      />
      <form id="site-form" onSubmit={save}>
        <Card title="Identity">
          <div className="form-grid">
            <Field label="Site name">
              <Input value={form.site_name} onChange={(e) => set('site_name', e.target.value)} />
            </Field>
            <Field label="Website URL">
              <Input value={form.website_url} onChange={(e) => set('website_url', e.target.value)} placeholder="https://example.com" />
            </Field>
            <Field label="Font family">
              <Select value={form.font_family} onChange={(e) => set('font_family', e.target.value)}>
                <option value="Inter">Inter</option>
                <option value="System">System default</option>
              </Select>
            </Field>
            <Field label="Primary color">
              <Input type="color" value={form.primary_color} onChange={(e) => set('primary_color', e.target.value)} />
            </Field>
            <Field label="Secondary color">
              <Input type="color" value={form.secondary_color} onChange={(e) => set('secondary_color', e.target.value)} />
            </Field>
            <Field label="Logo URL">
              <Input value={form.logo} onChange={(e) => set('logo', e.target.value)} placeholder="Optional" />
            </Field>
            <Field label="Favicon URL">
              <Input value={form.favicon} onChange={(e) => set('favicon', e.target.value)} placeholder="Optional" />
            </Field>
            <Field label="Contact email">
              <Input type="email" value={form.contact_email} onChange={(e) => set('contact_email', e.target.value)} />
            </Field>
            <Field label="Support email">
              <Input type="email" value={form.support_email} onChange={(e) => set('support_email', e.target.value)} />
            </Field>
            <Field label="Social links (Label = URL, one per line)">
              <Textarea
                rows={3}
                value={form.social_links}
                onChange={(e) => set('social_links', e.target.value)}
                placeholder={'Twitter = https://twitter.com/example\nLinkedIn = https://linkedin.com'}
              />
            </Field>
          </div>
        </Card>

        <Card title="Announcement bar">
          <div className="form-grid">
            <Field label="Show announcement">
              <label className="switch">
                <input
                  type="checkbox"
                  checked={Boolean(form.announcement_enabled)}
                  onChange={(e) => set('announcement_enabled', e.target.checked)}
                />
                <span />
              </label>
            </Field>
            <Field label="Announcement text">
              <Input value={form.announcement_text} onChange={(e) => set('announcement_text', e.target.value)} />
            </Field>
          </div>
        </Card>

        <Card title="Search & social">
          <div className="form-grid">
            <Field label="Meta title">
              <Input value={form.meta_title} onChange={(e) => set('meta_title', e.target.value)} />
            </Field>
            <Field label="Meta description">
              <Textarea rows={3} value={form.meta_description} onChange={(e) => set('meta_description', e.target.value)} />
            </Field>
            <Field label="OG title">
              <Input value={form.og_title} onChange={(e) => set('og_title', e.target.value)} />
            </Field>
            <Field label="OG description">
              <Textarea rows={2} value={form.og_description} onChange={(e) => set('og_description', e.target.value)} />
            </Field>
            <Field label="OG image">
              <Input value={form.og_image} onChange={(e) => set('og_image', e.target.value)} />
            </Field>
            <Field label="Canonical URL">
              <Input value={form.canonical_url} onChange={(e) => set('canonical_url', e.target.value)} />
            </Field>
            <Field label="Robots">
              <Input value={form.robots} onChange={(e) => set('robots', e.target.value)} />
            </Field>
          </div>
        </Card>

        <div className="form-actions">
          <Button className="primary" type="submit" disabled={saving}>
            {saving ? 'Saving…' : 'Save all'}
          </Button>
        </div>
      </form>
    </div>
  )
}