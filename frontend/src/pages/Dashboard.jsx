import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import {
  BarChart,
  Badge,
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
  UsersIcon,
  AgentIcon,
  CalendarIcon,
  TransferIcon,
  ClockIcon,
  ChartIcon,
} from '../components/icons'

export default function Dashboard() {
  const { user, logout } = useAuth()
  const fetchOverview = () => api.get('/analytics/overview')
  const { data, error, loading, reload } = useFetch(fetchOverview, [])

  if (error && error.status === 401) {
    logout()
    return null
  }

  const firstName = (user?.full_name || user?.email || '').split(' ')[0]

  return (
    <div>
      <PageTitle
        title="Dashboard"
        subtitle={`Welcome back${firstName ? `, ${firstName}` : ''}. Here's what's happening with your AI agents.`}
      />
      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : loading || !data ? (
        <div className="stats-grid">
          {[...Array(8)].map((_, index) => (
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
            <StatCard label="In progress" value={data.in_progress_calls} variant="info" icon={<ClockIcon width={17} height={17} />} />
            <StatCard label="Transferred" value={data.transferred_calls} icon={<TransferIcon width={17} height={17} />} />
            <StatCard label="Customers" value={data.total_customers} icon={<UsersIcon width={17} height={17} />} />
            <StatCard label="Agents" value={data.total_agents} icon={<AgentIcon width={17} height={17} />} />
            <StatCard label="Appointments" value={data.appointments_scheduled} variant="info" icon={<CalendarIcon width={17} height={17} />} />
          </div>

          <div className="grid two">
            <ChartCard
              title="Calls — last 7 days"
              subtitle={`${data.total_calls} total calls`}
              actions={<ChartIcon width={18} height={18} style={{ color: 'var(--muted)' }} />}
            >
              {data.calls_last_7_days.length === 0 ? (
                <Empty>No call data yet.</Empty>
              ) : (
                <BarChart data={data.calls_last_7_days} height={200} />
              )}
            </ChartCard>
            <Card title="Outcome breakdown">
              {data.outcome_breakdown.length === 0 ? (
                <Empty>No outcomes recorded yet.</Empty>
              ) : (
                <ul className="breakdown">
                  {data.outcome_breakdown.map((item) => (
                    <li key={item.outcome || 'unknown'}>
                      <span>
                        <span className={`status-dot ${statusVariant(item.outcome) || 'info'}`} />
                        {item.outcome || 'unknown'}
                      </span>
                      <strong>{item.count}</strong>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <Card
            title="Recent calls"
            actions={<Link to="/calls" className="btn small ghost">View all</Link>}
          >
            {data.recent_calls.length === 0 ? (
              <Empty>No calls yet.</Empty>
            ) : (
              <div className="table-wrap">
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
                      <tr key={call.id} style={{ cursor: 'pointer' }} onClick={() => (window.location.hash = `#/calls/${call.id}`)}>
                        <td>
                          <Badge variant={statusVariant(call.status)}>{call.status}</Badge>
                        </td>
                        <td>{call.agent_name}</td>
                        <td>{call.caller_number}</td>
                        <td>{formatDate(call.started_at)}</td>
                        <td>{formatDuration(call.duration_seconds)}</td>
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