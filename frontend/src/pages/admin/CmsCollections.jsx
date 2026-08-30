import { useState } from 'react'
import { api } from '../../api'
import {
  Badge,
  Button,
  Card,
  Empty,
  ErrorBox,
  Field,
  Input,
  Modal,
  PageTitle,
  Select,
  Textarea,
  toast,
  useFetch,
} from '../../components/Ui'

/* Reusable builder for ordered CMS collections (features, use-cases, etc.). */

export function buildCollectionEditor(config) {
  const {
    title,
    subtitle,
    endpoint,
    headers,
    valueFor,
    fields,
  } = config

  return function CollectionEditor() {
    const { data, error, loading, reload } = useFetch(() => api.get(endpoint), [])
    const rows = data || []

    const [open, setOpen] = useState(false)
    const [editing, setEditing] = useState(null)
    const [form, setForm] = useState(config.empty())
    const [formError, setFormError] = useState('')
    const [saving, setSaving] = useState(false)

    function startCreate() {
      setEditing(null)
      setForm(config.empty())
      setFormError('')
      setOpen(true)
    }

    function startEdit(row) {
      setEditing(row)
      setForm(config.fromRow(row))
      setFormError('')
      setOpen(true)
    }

    function cancel() {
      setOpen(false)
      setFormError('')
    }

    async function handleSubmit(event) {
      event.preventDefault()
      setSaving(true)
      setFormError('')
      try {
        const payload = config.toPayload(form)
        if (editing) {
          await api.patch(`${endpoint}/${editing.id}`, payload)
          toast('Saved')
        } else {
          await api.post(endpoint, { ...payload, order: rows.length })
          toast('Created')
        }
        cancel()
        reload()
      } catch (err) {
        setFormError(err.message || 'Save failed')
      } finally {
        setSaving(false)
      }
    }

    async function toggle(row) {
      try {
        await api.patch(`${endpoint}/${row.id}`, { enabled: !row.enabled })
        reload()
      } catch (err) {
        window.alert(err.message || 'Update failed')
      }
    }

    async function remove(row) {
      if (!window.confirm('Delete this item?')) return
      try {
        await api.delete(`${endpoint}/${row.id}`)
        reload()
      } catch (err) {
        window.alert(err.message || 'Delete failed')
      }
    }

    return (
      <div>
        <PageTitle
          title={title}
          subtitle={subtitle}
          actions={
            <Button className="primary" onClick={startCreate}>
              New {title}
            </Button>
          }
        />

        {error ? (
          <ErrorBox message={error} />
        ) : loading ? (
          <Empty>Loading…</Empty>
        ) : rows.length === 0 ? (
          <Empty>No {title.toLowerCase()} yet.</Empty>
        ) : (
          <Card>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    {headers.map((header) => (
                      <th key={header}>{header}</th>
                    ))}
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.id}>
                      {headers.map((header, index) => (
                        <td key={header}>{valueFor(header, row, index)}</td>
                      ))}
                      <td>
                        <Badge variant={row.enabled ? 'success' : ''}>
                          {row.enabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                      </td>
                      <td className="actions">
                        <button className="btn small" onClick={() => toggle(row)}>
                          {row.enabled ? 'Disable' : 'Enable'}
                        </button>
                        <button className="btn small" onClick={() => startEdit(row)}>
                          Edit
                        </button>
                        <button className="btn small danger" onClick={() => remove(row)}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        <Modal open={open} onClose={cancel} title={editing ? `Edit ${title}` : `New ${title}`}>
          {formError && <div className="alert error">{formError}</div>}
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              {fields.map((field) => {
                const value = form[field.key]
                if (field.type === 'textarea' || field.type === 'json') {
                  return (
                    <Field key={field.key} label={field.label} hint={field.hint}>
                      <Textarea
                        rows={field.rows || 3}
                        placeholder={field.placeholder}
                        value={Array.isArray(value) ? value.join('\n') : value}
                        onChange={(event) =>
                          setForm({ ...form, [field.key]: event.target.value })
                        }
                        style={{ gridColumn: '1 / -1' }}
                      />
                    </Field>
                  )
                }
                if (field.type === 'toggle') {
                  return (
                    <Field key={field.key} label={field.label}>
                      <label className="switch">
                        <input
                          type="checkbox"
                          checked={Boolean(value)}
                          onChange={(event) =>
                            setForm({ ...form, [field.key]: event.target.checked })
                          }
                        />
                        <span />
                      </label>
                    </Field>
                  )
                }
                if (field.type === 'select') {
                  return (
                    <Field key={field.key} label={field.label}>
                      <Select
                        value={value}
                        onChange={(event) => setForm({ ...form, [field.key]: event.target.value })}
                      >
                        {field.options.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </Select>
                    </Field>
                  )
                }
                return (
                  <Field key={field.key} label={field.label} hint={field.hint}>
                    <Input
                      value={value}
                      placeholder={field.placeholder}
                      onChange={(event) => setForm({ ...form, [field.key]: event.target.value })}
                    />
                  </Field>
                )
              })}
            </div>
            <div className="form-actions">
              <button className="btn primary" disabled={saving}>
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button className="btn" type="button" onClick={cancel}>
                Cancel
              </button>
            </div>
          </form>
        </Modal>
      </div>
    )
  }
}

const ICON_OPTIONS = [
  'phone',
  'website',
  'calendar',
  'knowledge',
  'customers',
  'transfer',
  'analytics',
  'outbound',
  'health',
  'briefcase',
  'home',
  'scissors',
  'wrench',
  'restaurant',
  'store',
]

/* Features / use-cases share title+description+icon. */
function textIconEditor(title, subtitle, endpoint) {
  return buildCollectionEditor({
    title,
    subtitle,
    endpoint,
    headers: ['Title', 'Icon'],
    valueFor: (header, row) => (header === 'Title' ? row.title : row.icon || '—'),
    empty: () => ({ title: '', description: '', icon: 'phone', enabled: true }),
    fromRow: (row) => ({
      title: row.title,
      description: row.description || '',
      icon: row.icon || 'phone',
      enabled: row.enabled,
    }),
    toPayload: (form) => ({
      title: form.title,
      description: form.description,
      icon: form.icon,
      enabled: form.enabled,
    }),
    fields: [
      { key: 'title', label: 'Title' },
      { key: 'description', label: 'Description', type: 'textarea' },
      { key: 'icon', label: 'Icon', type: 'select', options: ICON_OPTIONS },
      { key: 'enabled', label: 'Enabled', type: 'toggle' },
    ],
  })
}

export const FeatureEditor = textIconEditor('Features', 'Feature cards shown on the landing page.', '/platform/cms/features')

export const UseCaseEditor = textIconEditor('Use cases', 'Industry solutions with a description.', '/platform/cms/use-cases')

export const TestimonialEditor = buildCollectionEditor({
  title: 'Testimonials',
  subtitle: 'Customer quotes. Leave disabled until you have real reviews.',
  endpoint: '/platform/cms/testimonials',
  headers: ['Name', 'Company', 'Quote'],
  valueFor: (header, row) =>
    header === 'Name' ? row.name : header === 'Company' ? row.company || '—' : (row.quote || '').slice(0, 80),
  empty: () => ({ name: '', company: '', role: '', quote: '', avatar: '', enabled: true }),
  fromRow: (row) => ({
    name: row.name,
    company: row.company || '',
    role: row.role || '',
    quote: row.quote || '',
    avatar: row.avatar || '',
    enabled: row.enabled,
  }),
  toPayload: (form) => ({
    name: form.name,
    company: form.company,
    role: form.role,
    quote: form.quote,
    avatar: form.avatar || null,
    enabled: form.enabled,
  }),
  fields: [
    { key: 'name', label: 'Name' },
    { key: 'company', label: 'Company' },
    { key: 'role', label: 'Role' },
    { key: 'quote', label: 'Quote', type: 'textarea' },
    { key: 'avatar', label: 'Avatar URL' },
    { key: 'enabled', label: 'Enabled', type: 'toggle' },
  ],
})

const jsonLines = (value) =>
  (value || '').split('\n').map((line) => line.trim()).filter(Boolean)
const linkLines = (value) =>
  (value || []).map((link) => `${link.label} = ${link.url}`).join('\n')
const linesToLinks = (text) =>
  (text || '').split('\n').map((line) => line.trim()).filter(Boolean).map((line) => {
    const separator = line.indexOf('=')
    if (separator < 0) return { label: line, url: '#' }
    return { label: line.slice(0, separator).trim(), url: line.slice(separator + 1).trim() }
  })

export const PricingEditor = buildCollectionEditor({
  title: 'Pricing plans',
  subtitle: 'Plans are informational; pricing is still on the roadmap.',
  endpoint: '/platform/cms/pricing',
  headers: ['Name', 'Price'],
  valueFor: (header, row) => (header === 'Name' ? row.name : `${row.price}${row.billing_period ? `/${row.billing_period}` : ''}`),
  empty: () => ({ name: '', description: '', price: 'Coming soon', billing_period: '', features: [], cta_text: 'Get started', highlighted: false, enabled: true }),
  fromRow: (row) => ({
    name: row.name,
    description: row.description || '',
    price: row.price || 'Coming soon',
    billing_period: row.billing_period || '',
    features: Array.isArray(row.features) ? row.features : [],
    cta_text: row.cta_text || 'Get started',
    highlighted: row.highlighted,
    enabled: row.enabled,
  }),
  toPayload: (form) => ({
    name: form.name,
    description: form.description,
    price: form.price,
    billing_period: form.billing_period,
    features: jsonLines(typeof form.features === 'string' ? form.features : form.features.join('\n')),
    cta_text: form.cta_text,
    highlighted: form.highlighted,
    enabled: form.enabled,
  }),
  fields: [
    { key: 'name', label: 'Name' },
    { key: 'description', label: 'Description' },
    { key: 'price', label: 'Price' },
    { key: 'billing_period', label: 'Billing period', hint: 'e.g. month, year' },
    { key: 'features', label: 'Features (one per line)', type: 'json' },
    { key: 'cta_text', label: 'Button text' },
    { key: 'highlighted', label: 'Highlighted', type: 'toggle' },
    { key: 'enabled', label: 'Enabled', type: 'toggle' },
  ],
})

export const FaqEditor = buildCollectionEditor({
  title: 'FAQs',
  subtitle: 'Questions and answers shown on the landing page.',
  endpoint: '/platform/cms/faqs',
  headers: ['Question'],
  valueFor: (header, row) => row.question,
  empty: () => ({ question: '', answer: '', enabled: true }),
  fromRow: (row) => ({ question: row.question, answer: row.answer || '', enabled: row.enabled }),
  toPayload: (form) => ({ question: form.question, answer: form.answer, enabled: form.enabled }),
  fields: [
    { key: 'question', label: 'Question' },
    { key: 'answer', label: 'Answer', type: 'textarea' },
    { key: 'enabled', label: 'Enabled', type: 'toggle' },
  ],
})

export const NavigationEditor = buildCollectionEditor({
  title: 'Navigation',
  subtitle: 'Links in the landing page nav bar.',
  endpoint: '/platform/cms/navigation',
  headers: ['Label', 'URL'],
  valueFor: (header, row) => (header === 'Label' ? row.label : row.url),
  empty: () => ({ label: '', url: '#' }),
  fromRow: (row) => ({ label: row.label, url: row.url, enabled: row.enabled !== false }),
  toPayload: (form) => ({ label: form.label, url: form.url, enabled: form.enabled !== false }),
  fields: [
    { key: 'label', label: 'Label' },
    { key: 'url', label: 'URL', hint: 'Use #features, #use-cases, #how-it-works…' },
    { key: 'enabled', label: 'Enabled', type: 'toggle' },
  ],
})

export const FooterEditor = buildCollectionEditor({
  title: 'Footer columns',
  subtitle: 'Footer link columns. Links use the "Label = URL" format, one per line.',
  endpoint: '/platform/cms/footer',
  headers: ['Title'],
  valueFor: (header, row) => row.title,
  empty: () => ({ title: '', links: [], enabled: true }),
  fromRow: (row) => ({ title: row.title, links: Array.isArray(row.links) ? row.links : [], enabled: row.enabled }),
  toPayload: (form) => ({
    title: form.title,
    links: linesToLinks(typeof form.links === 'string' ? form.links : linkLines(form.links)),
    enabled: form.enabled,
  }),
  fields: [
    { key: 'title', label: 'Column title' },
    { key: 'links', label: 'Links (Label = URL, one per line)', type: 'textarea', rows: 5 },
    { key: 'enabled', label: 'Enabled', type: 'toggle' },
  ],
})