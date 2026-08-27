import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import {
  Badge,
  Card,
  Empty,
  ErrorBox,
  formatDate,
  formatDuration,
  PageTitle,
  statusVariant,
  useFetch,
} from '../components/Ui'

function Stat({ label, value, variant }) {
  return (
    <Card className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label muted">
        {label}
        {variant && <Badge variant={variant}>{variant}</Badge>}
      </div>
    </Card>
  )
}

export default function Dashboard() {
  const { logout } = useAuth()
  const fetchOverview = () => api.get('/analytics/overview')
  const { data, error, loading, reload } = useFetch(fetchOverview, [])

  if (error && error.status === 401) {
    logout()
    return null
  }

  return (
    <div>
      <PageTitle title="Dashboard" />
      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : loading || !data ? (
        <Card className="stat" />
      ) : (
        <>
          <div className="stats-grid">
            <Stat label="Total calls" value={data.total_calls} />
            <Stat label="Completed" value={data.completed_calls} variant="success" />
            <Stat label="Missed" value={data.missed_calls} variant="warn" />
            <Stat label="In progress" value={data.in_progress_calls} variant="info" />
            <Stat label="Transferred" value={data.transferred_calls} variant="info" />
            <Stat label="Failed" value={data.failed_calls} variant="danger" />
            <Stat label="Avg duration" value={formatDuration(data.average_duration_seconds)} />
            <Stat label="Customers" value={data.total_customers} />
            <Stat label="Agents" value={data.total_agents} />
            <Stat label="Appointments" value={data.appointments_scheduled} />
          </div>

          <div className="grid two">
            <Card title="Calls — last 7 days">
              {data.calls_last_7_days.length === 0 ? (
                <Empty>No call data yet.</Empty>
              ) : (
                <div className="bars">
                  {data.calls_last_7_days.map((entry) => (
                    <div className="bar-col" key={entry.day} title={`${entry.day}: ${entry.count}`}>
                      <div className="bar-track">
                        <div
                          className="bar"
                          style={{
                            height: `${
                              entry.count === 0
                                ? 2
                                : Math.max(8, (entry.count / data.total_calls) * 100)
                            }%`,
                          }}
                        />
                      </div>
                      <span className="bar-day">{entry.day.slice(5)}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
            <Card title="Outcome breakdown">
              {data.outcome_breakdown.length === 0 ? (
                <Empty>No outcomes recorded yet.</Empty>
              ) : (
                <ul className="breakdown">
                  {data.outcome_breakdown.map((item) => (
                    <li key={item.outcome || 'unknown'}>
                      <span>{item.outcome || 'unknown'}</span>
                      <strong>{item.count}</strong>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <Card title="Recent calls">
            {data.recent_calls.length === 0 ? (
              <Empty>No calls yet.</Empty>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Agent</th>
                    <th>Phone</th>
                    <th>Started</th>
                    <th>Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_calls.map((call) => (
                    <tr key={call.id}>
                      <td>
                        <Link to={`/calls/${call.id}`}>
                          <Badge variant={statusVariant(call.status)}>{call.status}</Badge>
                        </Link>
                      </td>
                      <td>{call.agent_name}</td>
                      <td>{call.phone_number}</td>
                      <td>{formatDate(call.started_at)}</td>
                      <td>{formatDuration(call.duration_seconds)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}
    </div>
  )
}