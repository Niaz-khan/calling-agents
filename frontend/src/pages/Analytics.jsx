import { Link } from 'react-router-dom'
import { api } from '../api'
import {
  Badge,
  BarChart,
  Card,
  ChartCard,
  Empty,
  ErrorBox,
  formatDate,
  formatDuration,
  PageTitle,
  StatCard,
  statusVariant,
  useFetch,
} from '../components/Ui'
import {
  PhoneIcon,
  CheckIcon,
  CloseIcon,
  TransferIcon,
  ClockIcon,
  UsersIcon,
  AgentIcon,
  CalendarIcon,
} from '../components/icons'

function outcomeVariant(outcome) {
  if (!outcome) return ''
  const label = outcome.toLowerCase()
  if (label.includes('booked')) return 'success'
  if (label.includes('transferred')) return 'warn'
  if (label.includes('unknown') || label.includes('no_resolution')) return ''
  return 'info'
}

export default function Analytics() {
  const fetchOverview = () => api.get('/analytics/overview')
  const { data, error, loading, reload } = useFetch(fetchOverview, [])

  const fetchCalls = () => api.get('/calls')
  const callsResult = useFetch(fetchCalls, [])
  const calls = callsResult.data || []

  return (
    <div>
      <PageTitle
        title="Analytics"
        subtitle="Performance across calls, conversations and outcomes."
      />
      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : loading || !data ? (
        <div className="stats-grid">
          {[...Array(6)].map((_, index) => (
            <Card className="stat" key={index}>
              <div className="skeleton" style={{ height: 14 }} />
            </Card>
          ))}
        </div>
      ) : (
        <>
          <div className="stats-grid">
            <StatCard label="Total calls" value={data.total_calls} icon={<PhoneIcon width={17} height={17} />} />
            <StatCard label="Completed" value={data.completed_calls} variant="success" icon={<CheckIcon width={17} height={17} />} />
            <StatCard label="Missed" value={data.missed_calls} variant="warn" icon={<CloseIcon width={17} height={17} />} />
            <StatCard label="Transferred" value={data.transferred_calls} icon={<TransferIcon width={17} height={17} />} />
            <StatCard label="Failed" value={data.failed_calls} variant="danger" icon={<CloseIcon width={17} height={17} />} />
            <StatCard
              label="Avg duration"
              value={formatDuration(data.average_duration_seconds)}
              icon={<ClockIcon width={17} height={17} />}
            />
            <StatCard label="Customers" value={data.total_customers} icon={<UsersIcon width={17} height={17} />} />
            <StatCard label="Agents" value={data.total_agents} icon={<AgentIcon width={17} height={17} />} />
          </div>

          <div className="grid two">
            <ChartCard
              title="Calls — last 7 days"
              subtitle={`${data.total_calls} total calls in period`}
            >
              {data.calls_last_7_days.length === 0 ? (
                <Empty>No call data yet.</Empty>
              ) : (
                <BarChart data={data.calls_last_7_days} height={220} />
              )}
            </ChartCard>
            <Card
              title="Appointments"
              actions={<CalendarIcon width={17} height={17} style={{ color: 'var(--muted)' }} />}
            >
              {data.appointments_scheduled === 0 && data.appointments_cancelled === 0 ? (
                <Empty>No appointments yet.</Empty>
              ) : (
                <ul className="breakdown">
                  <li>
                    <span>
                      <span className="status-dot success" />
                      Scheduled
                    </span>
                    <strong>{data.appointments_scheduled}</strong>
                  </li>
                  <li>
                    <span>
                      <span className="status-dot danger" />
                      Cancelled
                    </span>
                    <strong>{data.appointments_cancelled}</strong>
                  </li>
                </ul>
              )}
            </Card>
          </div>

          <Card title="Outcome breakdown">
            {data.outcome_breakdown.length === 0 ? (
              <Empty>No outcomes recorded yet.</Empty>
            ) : (
              <ul className="breakdown">
                {data.outcome_breakdown.map((item) => (
                  <li key={item.outcome || 'unknown'}>
                    <span>
                      <span className={`status-dot ${outcomeVariant(item.outcome) || 'info'}`} />
                      {item.outcome || 'unknown'}
                    </span>
                    <strong>{item.count}</strong>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card
            title="All calls"
            actions={<Link to="/calls" className="btn small ghost">Manage calls</Link>}
          >
            {calls.length === 0 ? (
              <Empty>No calls yet.</Empty>
            ) : (
              <div className="table-wrap">
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
                      <tr
                        key={call.id}
                        style={{ cursor: 'pointer' }}
                        onClick={() => (window.location.hash = `#/calls/${call.id}`)}
                      >
                        <td>
                          <Badge variant={statusVariant(call.status)}>{call.status}</Badge>
                        </td>
                        <td>{call.direction}</td>
                        <td>{call.agent_name}</td>
                        <td>{call.caller_number}</td>
                        <td>{formatDate(call.started_at)}</td>
                        <td>{formatDuration(call.duration_seconds)}</td>
                        <td>
                          <Badge variant={outcomeVariant(call.outcome)}>{call.outcome || '—'}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  )
}