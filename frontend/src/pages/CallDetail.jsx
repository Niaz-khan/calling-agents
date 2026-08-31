import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import {
  Badge,
  Card,
  Empty,
  ErrorBox,
  formatDate,
  PageTitle,
  statusVariant,
  useFetch,
} from '../components/Ui'

function roleClass(role) {
  if (role === 'user') return 'msg user'
  if (role === 'tool') return 'msg tool'
  if (role === 'system') return 'msg system'
  return 'msg assistant'
}

export default function CallDetail() {
  const { callId } = useParams()
  const fetchCall = () => api.get(`/calls/${callId}`)
  const { data: call, error, loading, reload } = useFetch(fetchCall, [callId])

  if (error) return <ErrorBox message={error} onRetry={reload} />
  if (loading || !call) return <Empty>Loading…</Empty>

  return (
    <div>
      <PageTitle
        title={`Call #${call.id}`}
        actions={<Link to="/app/calls">← All calls</Link>}
      />

      <div className="grid two">
        <Card title="Call details">
          <dl className="details">
            <dt>Status</dt>
            <dd>
              <Badge variant={statusVariant(call.status)}>{call.status}</Badge>
            </dd>
            <dt>Direction</dt>
            <dd>{call.direction}</dd>
            <dt>Phone</dt>
            <dd>{call.caller_number}</dd>
            <dt>Started</dt>
            <dd>{formatDate(call.started_at)}</dd>
            <dt>Ended</dt>
            <dd>{formatDate(call.ended_at)}</dd>
            <dt>Outcome</dt>
            <dd>{call.outcome || '—'}</dd>
          </dl>
        </Card>
        <Card title="Summary">
          {call.summary ? <p>{call.summary}</p> : <Empty>No summary available.</Empty>}
        </Card>
      </div>

      <Card title="Transcript" className="transcript-card">
        {call.messages.length === 0 ? (
          <Empty>No messages in this call.</Empty>
        ) : (
          <div className="transcript">
            {call.messages.map((message) => (
              <div key={message.id} className={roleClass(message.role)}>
                <div className="msg-head">
                  <span className="msg-role">{message.role}</span>
                  <span className="muted">{formatDate(message.created_at)}</span>
                </div>
                <div className="msg-body">{message.content}</div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}