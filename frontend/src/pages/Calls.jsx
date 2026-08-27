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

export default function Calls() {
  const [agentId, setAgentId] = useState('')

  const fetchCalls = () => {
    const params = new URLSearchParams()
    if (agentId) params.set('agent_id', agentId)
    const query = params.toString()
    return api.get(`/calls${query ? `?${query}` : ''}`)
  }
  const { data, error, loading, reload } = useFetch(fetchCalls, [agentId])
  const calls = data || []

  const fetchAgents = () => api.get('/agents')
  const agentsResult = useFetch(fetchAgents, [])
  const agents = agentsResult.data || []

  return (
    <div>
      <PageTitle title="Calls" />
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
        </div>
      </Card>

      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : loading ? (
        <Empty>Loading…</Empty>
      ) : calls.length === 0 ? (
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
              </tr>
            </thead>
            <tbody>
              {calls.map((call) => (
                <tr key={call.id}>
                  <td>
                    <Link to={`/calls/${call.id}`}>
                      <Badge variant={statusVariant(call.status)}>{call.status}</Badge>
                    </Link>
                  </td>
                  <td>{call.direction}</td>
                  <td>{call.agent_name}</td>
                  <td>{call.caller_number}</td>
                  <td>{formatDate(call.started_at)}</td>
                  <td>{formatDuration(call.duration_seconds)}</td>
                  <td>{call.outcome || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}