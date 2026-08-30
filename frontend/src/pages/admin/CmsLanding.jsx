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
  Textarea,
  toast,
} from '../../components/Ui'
import { defaultLanding } from '../../lib/landingDefaults'

const JSON_LINE_FIELDS = ['value_strip_items', 'problem_items']

function normalizeLanding(result) {
  const base = { ...defaultLanding, ...result }
  const back = { ...base }
  for (const key of JSON_LINE_FIELDS) {
    back[key] = Array.isArray(base[key]) ? base[key] : []
  }
  back.how_works_steps_text = (base.how_works_steps || [])
    .map((step) => `${step.num || ''} | ${step.title || ''} | ${step.text || ''}`)
    .join('\n')
  return back
}

function LandingText({ value, onChange, label, hint, area }) {
  return (
    <Field label={label} hint={hint}>
      {area ? (
        <Textarea rows={3} value={value ?? ''} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <Input value={value ?? ''} onChange={(event) => onChange(event.target.value)} />
      )}
    </Field>
  )
}

export default function CmsLanding() {
  const [data, setData] = useState(null)
  const [form, setForm] = useState(null)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api
      .get('/platform/cms/landing')
      .then((result) => {
        setData(result)
        setForm(normalizeLanding(result))
      })
      .catch((err) => setError(err))
  }, [])

  function set(key, value) {
    setForm((previous) => ({ ...previous, [key]: value }))
  }

  function textField(key, label, opts) {
    return <LandingText label={label} value={form[key]} onChange={(value) => set(key, value)} {...opts} />
  }

  async function save(event) {
    event.preventDefault()
    setSaving(true)
    try {
      const payload = { ...form }
      delete payload.how_works_steps_text
      payload.how_works_steps = (form.how_works_steps_text || '')
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
          const [num, title, ...rest] = line.split('|').map((part) => part.trim())
          return { num: num || '', title: title || '', text: rest.join('|').trim() || '' }
        })
      for (const key of JSON_LINE_FIELDS) {
        payload[key] = (Array.isArray(form[key]) ? form[key].join('\n') : form[key] || '')
          .split('\n')
          .map((line) => line.trim())
          .filter(Boolean)
      }
      payload.sections = (data.sections || []).map((section) => ({
        key: section.key,
        enabled: section.enabled,
      }))
      await api.put('/platform/cms/landing', payload)
      toast('Landing page saved')
    } catch (err) {
      window.alert(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (error) {
    return (
      <div>
        <PageTitle title="Landing copy" />
        <ErrorBox message={error} />
      </div>
    )
  }

  if (!form) {
    return (
      <div>
        <PageTitle title="Landing copy" />
        <Empty>Loading…</Empty>
      </div>
    )
  }

  return (
    <div>
      <PageTitle
        title="Landing copy"
        subtitle="All editorial copy for the public landing page."
        actions={
          <Button className="primary" onClick={save} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </Button>
        }
      />
      <form id="landing-form" onSubmit={save}>
        <Card
          title="Hero"
          actions={
            <label>
              Enabled{' '}
              <input
                type="checkbox"
                checked={form.hero_enabled}
                onChange={(e) => set('hero_enabled', e.target.checked)}
              />
            </label>
          }
        >
          <div className="form-grid">
            {textField('hero_badge', 'Badge')}
            {textField('hero_title', 'Title', { area: true })}
            {textField('hero_subtitle', 'Subtitle', { area: true })}
            {textField('hero_primary_cta', 'Primary CTA')}
            {textField('hero_secondary_cta', 'Secondary CTA')}
          </div>
        </Card>

        <Card title="Value strip">
          <div className="form-grid">
            {textField('value_strip_title', 'Title')}
            {textField('value_strip_items', 'Items (one per line)', {
              area: true,
              hint: 'e.g. PHONE, WEBSITE, APPOINTMENTS',
            })}
          </div>
        </Card>

        <Card title="Problem / solution">
          <div className="form-grid">
            {textField('problem_title', 'Problem title', { area: true })}
            {textField('problem_items', 'Problem items (one per line)', { area: true })}
            {textField('solution_title', 'Solution title', { area: true })}
            {textField('solution_text', 'Solution text', { area: true })}
          </div>
        </Card>

        <Card title="Features & showcase">
          <div className="form-grid">
            {textField('features_title', 'Features title')}
            {textField('features_subtitle', 'Features subtitle', { area: true })}
            {textField('showcase_title', 'Showcase title')}
            {textField('showcase_subtitle', 'Showcase subtitle', { area: true })}
          </div>
        </Card>

        <Card title="How it works">
          <div className="form-grid">
            {textField('how_works_title', 'Title')}
            {textField('how_works_steps_text', 'Steps (num | title | text, one per line)', {
              area: true,
              hint: 'e.g. "01 | Create your agent | Define how your AI should speak."',
            })}
          </div>
        </Card>

        <Card title="Website & phone">
          <div className="form-grid">
            {textField('website_section_title', 'Website title')}
            {textField('website_section_text', 'Website text', { area: true })}
            {textField('website_section_cta', 'Website CTA')}
            {textField('phone_section_title', 'Phone title')}
            {textField('phone_section_text', 'Phone text', { area: true })}
            {textField('phone_section_cta', 'Phone CTA')}
          </div>
        </Card>

        <Card title="Use cases, analytics, pricing, FAQ">
          <div className="form-grid">
            {textField('use_cases_title', 'Use cases title')}
            {textField('use_cases_subtitle', 'Use cases subtitle', { area: true })}
            {textField('analytics_title', 'Analytics title')}
            {textField('analytics_subtitle', 'Analytics subtitle', { area: true })}
            {textField('pricing_title', 'Pricing title')}
            {textField('pricing_subtitle', 'Pricing subtitle', { area: true })}
            {textField('pricing_disclaimer', 'Pricing disclaimer', { area: true })}
            {textField('faq_title', 'FAQ title')}
            {textField('faq_subtitle', 'FAQ subtitle', { area: true })}
          </div>
        </Card>

        <Card title="Final CTA">
          <div className="form-grid">
            {textField('cta_title', 'Title')}
            {textField('cta_subtitle', 'Subtitle', { area: true })}
            {textField('cta_primary', 'Primary CTA')}
            {textField('cta_secondary', 'Secondary CTA')}
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