import { useState } from 'react'
import { api, getToken } from '../api'
import {
  Card,
  Empty,
  ErrorBox,
  Field,
  formatDate,
  PageTitle,
  useFetch,
} from '../components/Ui'

const emptyForm = { agent_id: '', name: '', description: '' }

export default function Knowledge() {
  const fetchBases = () => api.get('/knowledge/bases')
  const { data, error, loading, reload } = useFetch(fetchBases, [])
  const bases = data || []

  const fetchAgents = () => api.get('/agents')
  const agentsResult = useFetch(fetchAgents, [])
  const agents = agentsResult.data || []

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [expanded, setExpanded] = useState(null)
  const [documents, setDocuments] = useState({})
  const [search, setSearch] = useState('')
  const [searchAgent, setSearchAgent] = useState('')
  const [searchResult, setSearchResult] = useState(null)
  const [searching, setSearching] = useState(false)

  function startCreate() {
    setForm(emptyForm)
    setFormError('')
    setShowForm(true)
  }

  function cancel() {
    setShowForm(false)
    setForm(emptyForm)
    setFormError('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setSaving(true)
    setFormError('')
    try {
      await api.post('/knowledge/bases', {
        agent_id: Number(form.agent_id),
        name: form.name,
        description: form.description || null,
      })
      cancel()
      reload()
    } catch (err) {
      setFormError(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function removeBase(base) {
    if (!window.confirm(`Delete knowledge base "${base.name}"?`)) return
    try {
      await api.delete(`/knowledge/bases/${base.id}`)
      setDocuments((previous) => {
        const next = { ...previous }
        delete next[base.id]
        return next
      })
      if (expanded === base.id) setExpanded(null)
      reload()
    } catch (err) {
      window.alert(err.message || 'Delete failed')
    }
  }

  async function toggleDocuments(base) {
    if (expanded === base.id) {
      setExpanded(null)
      return
    }
    setExpanded(base.id)
    try {
      const docs = await api.get(`/knowledge/bases/${base.id}/documents`)
      setDocuments((previous) => ({ ...previous, [base.id]: docs }))
    } catch (_err) {
      void 0
    }
  }

  async function uploadDocument(base, file) {
    if (!file) return
    const body = new FormData()
    body.append('file', file)

    const response = await fetch(`/knowledge/bases/${base.id}/documents`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body,
    })

    if (!response.ok) {
      let message = `Upload failed (${response.status})`
      try {
        const data = await response.json()
        if (data && data.detail) message = typeof data.detail === 'string' ? data.detail : message
      } catch (_err) {
        void 0
      }
      window.alert(message)
      return
    }

    toggleDocuments({ id: base.id })
  }

  async function removeDocument(baseId, documentId) {
    if (!window.confirm('Delete this document?')) return
    try {
      await api.delete(`/knowledge/documents/${documentId}`)
      const docs = await api.get(`/knowledge/bases/${baseId}/documents`)
      setDocuments((previous) => ({ ...previous, [baseId]: docs }))
    } catch (err) {
      window.alert(err.message || 'Delete failed')
    }
  }

  async function runSearch(event) {
    event.preventDefault()
    if (!searchAgent) return
    setSearching(true)
    setSearchResult(null)
    try {
      const result = await api.post('/knowledge/search', {
        agent_id: Number(searchAgent),
        query: search,
      })
      setSearchResult(result)
    } catch (err) {
      window.alert(err.message || 'Search failed')
    } finally {
      setSearching(false)
    }
  }

  function agentName(agentId) {
    const agent = agents.find((item) => item.id === agentId)
    return agent ? agent.name : agentId
  }

  return (
    <div>
      <PageTitle
        title="Knowledge Base"
        actions={
          !showForm && (
            <button className="btn primary" onClick={startCreate}>
              New knowledge base
            </button>
          )
        }
      />

      {showForm && (
        <Card title="New knowledge base">
          {formError && <div className="alert error">{formError}</div>}
          <form className="form-grid" onSubmit={handleSubmit}>
            <Field label="Agent">
              <select
                className="input"
                value={form.agent_id}
                onChange={(event) => setForm({ ...form, agent_id: event.target.value })}
                required
              >
                <option value="">Select agent</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Name">
              <input
                className="input"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                required
              />
            </Field>
            <Field label="Description">
              <textarea
                className="input"
                rows={3}
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
              />
            </Field>
            <div className="form-actions">
              <button className="btn primary" disabled={saving}>
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button className="btn" type="button" onClick={cancel}>
                Cancel
              </button>
            </div>
          </form>
        </Card>
      )}

      <Card title="Search knowledge base">
        <form className="form-row" onSubmit={runSearch}>
          <Field label="Agent">
            <select
              className="input"
              value={searchAgent}
              onChange={(event) => setSearchAgent(event.target.value)}
              required
            >
              <option value="">Select agent</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Query">
            <input
              className="input"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              required
            />
          </Field>
          <button className="btn primary" disabled={searching}>
            {searching ? 'Searching…' : 'Search'}
          </button>
        </form>
        {searchResult && (
          <div className="search-results">
            {searchResult.found ? (
              <ul className="breakdown">
                {searchResult.results.map((item) => (
                  <li key={item.chunk_id}>
                    <span>
                      {item.document_filename} (chunk {item.chunk_index + 1})
                    </span>
                    <strong>{(item.score * 100).toFixed(0)}%</strong>
                    <p className="muted">{item.content}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>No relevant content found.</Empty>
            )}
          </div>
        )}
      </Card>

      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : loading ? (
        <Empty>Loading…</Empty>
      ) : bases.length === 0 ? (
        <Empty>No knowledge bases yet.</Empty>
      ) : (
        bases.map((base) => {
          const docs = documents[base.id] || []
          return (
            <Card key={base.id} title={base.name}>
              <div className="kb-meta">
                <span className="muted">Agent: {agentName(base.agent_id)}</span>
                <span className="muted">Created: {formatDate(base.created_at)}</span>
                {base.description && <p className="muted">{base.description}</p>}
              </div>
              <div className="actions">
                <button className="btn small" onClick={() => toggleDocuments(base)}>
                  {expanded === base.id ? 'Hide documents' : 'Show documents'}
                </button>
                <label className="btn small">
                  Upload document
                  <input
                    type="file"
                    style={{ display: 'none' }}
                    onChange={(event) => uploadDocument(base, event.target.files[0])}
                  />
                </label>
                <button className="btn small danger" onClick={() => removeBase(base)}>
                  Delete base
                </button>
              </div>
              {expanded === base.id && (
                <div className="doc-list">
                  {docs.length === 0 ? (
                    <Empty>No documents yet.</Empty>
                  ) : (
                    docs.map((document) => (
                      <div className="doc-row" key={document.id}>
                        <div>
                          <div>{document.filename}</div>
                          <div className="muted">
                            {document.status}
                            {document.title ? ` · ${document.title}` : ''}
                          </div>
                          {document.error && (
                            <div className="alert error compact">{document.error}</div>
                          )}
                        </div>
                        <button
                          className="btn small danger"
                          onClick={() => removeDocument(base.id, document.id)}
                        >
                          Delete
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}
            </Card>
          )
        })
      )}
    </div>
  )
}