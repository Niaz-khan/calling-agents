import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import {
  Badge,
  Card,
  Empty,
  ErrorBox,
  Field,
  formatDate,
  formatDuration,
  PageTitle,
  statusVariant,
  useFetch,
} from '../components/Ui'

function outcomeVariant(outcome) {
  if (!outcome) return ''
  const label = outcome.toLowerCase()
  if (label.includes('booked')) return 'success'
  if (label.includes('transferred')) return 'warn'
  if (label.includes('unknown') || label.includes('no_resolution')) return ''
  return 'info'
}

export default function Calls() {
  const [agentId, setAgentId] = useState('')
  const [direction, setDirection] = useState('')

  const fetchCalls = () => {
    const params = new URLSearchParams()
    if (agentId) params.set('agent_id', agentId)
    const query = params.toString()
    return api.get(`/calls${query ? `?${query}` : ''}`)
  }
  const { data, error, loading, reload } = useFetch(fetchCalls, [agentId, direction])
  const calls = data || []

  const fetchAgents = () => api.get('/agents')
  const agentsResult = useFetch(fetchAgents, [])
  const agents = agentsResult.data || []

  const fetchNumbers = () => api.get('/phone-numbers')
  const numbersResult = useFetch(fetchNumbers, [])
  const numbers = (numbersResult.data || []).filter((number) => number.outbound_enabled)

  const [showOutbound, setShowOutbound] = useState(false)
  const [outbound, setOutbound] = useState({ agent_id: '', from_number_id: '', to: '' })
  const [calling, setCalling] = useState(false)
  const [callError, setCallError] = useState('')

  async function placeOutbound(event) {
    event.preventDefault()
    setCalling(true)
    setCallError('')
    try {
      const created = await api.post('/calls/outbound', {
        agent_id: Number(outbound.agent_id),
        from_number_id: Number(outbound.from_number_id),
        to: outbound.to,
      })
      setShowOutbound(false)
      setOutbound({ agent_id: '', from_number_id: '', to: '' })
      reload()
      if (created && created.id) {
        window.location.hash = `#/calls/${created.id}`
      }
    } catch (err) {
      setCallError(err.message || 'Call failed')
    } finally {
      setCalling(false)
    }
  }

  const visibleCalls = direction ? calls.filter((call) => call.direction === direction) : calls

  return (
    <div>
      <PageTitle
        title="Calls"
        actions={
          !showOutbound && (
            <button className="btn primary" onClick={() => setShowOutbound(true)}>
              New outbound call
            </button>
          )
        }
      />
      <Card>
        <div className="toolbar">
          <Field label="Filter by agent">
            <select
              className="input"
              value={agentId}
              onChange={(event) => setAgentId(event.target.value)}
            >
              <option value="">All agents</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Direction">
            <select
              className="input"
              value={direction}
              onChange={(event) => setDirection(event.target.value)}
            >
              <option value="">All</option>
              <option value="inbound">Inbound</option>
              <option value="outbound">Outbound</option>
            </select>
          </Field>
        </div>
      </Card>

      {showOutbound && (
        <Card title="Place an outbound call">
          {callError && <div className="alert error">{callError}</div>}
          <form className="form-grid" onSubmit={placeOutbound}>
            <Field label="Agent">
              <select
                className="input"
                value={outbound.agent_id}
                onChange={(event) => setOutbound({ ...outbound, agent_id: event.target.value })}
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
            <Field label="Call from">
              <select
                className="input"
                value={outbound.from_number_id}
                onChange={(event) =>
                  setOutbound({ ...outbound, from_number_id: event.target.value })
                }
                required
              >
                <option value="">Select number</option>
                {numbers.map((number) => (
                  <option key={number.id} value={number.id}>
                    {number.phone_number}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Phone number to call">
              <input
                className="input"
                placeholder="+15550001111"
                value={outbound.to}
                onChange={(event) => setOutbound({ ...outbound, to: event.target.value })}
                required
              />
            </Field>
            <div className="form-actions">
              <button className="btn primary" disabled={calling}>
                {calling ? 'Calling…' : 'Call'}
              </button>
              <button
                className="btn"
                type="button"
                onClick={() => {
                  setShowOutbound(false)
                  setCallError('')
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </Card>
      )}

      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : loading ? (
        <Empty>Loading…</Empty>
      ) : visibleCalls.length === 0 ? (
        <Empty>No calls found.</Empty>
      ) : (
        <Card>
          <table className="table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Direction</th>
                <th>Agent</th>
                <th>Phone</th>
                <th>Started</th>
                <th>Duration</th>
                <th>Outcome</th>
                <th>Summary</th>
              </tr>
            </thead>
            <tbody>
              {visibleCalls.map((call) => (
                <tr key={call.id}>
                  <td>
                    <Link to={`/app/calls/${call.id}`}>
                      <Badge variant={statusVariant(call.status)}>{call.status}</Badge>
                    </Link>
                  </td>
                  <td>{call.direction}</td>
                  <td>{call.agent_name}</td>
                  <td>{call.caller_number}</td>
                  <td>{formatDate(call.started_at)}</td>
                  <td>{formatDuration(call.duration_seconds)}</td>
                  <td>
                    <Badge variant={outcomeVariant(call.outcome)}>{call.outcome || '—'}</Badge>
                  </td>
                  <td className="muted table-cell-truncate">{call.summary || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}