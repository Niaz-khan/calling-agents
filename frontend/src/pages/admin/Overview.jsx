import { Link } from 'react-router-dom'
import { api } from '../../api'
import {
  BarChart,
  Card,
  ChartCard,
  Empty,
  ErrorBox,
  formatDay,
  PageTitle,
  StatCard,
  useFetch,
} from '../../components/Ui'
import {
  OrganizationIcon,
  UsersIcon,
  AgentIcon,
  PhoneIcon,
  CallIcon,
  CalendarIcon,
  ChartIcon,
  DeployIcon,
  WebsiteIcon,
} from '../../components/icons'

const activityLabel = {
  organization: 'Organization created',
  user: 'User registered',
  agent: 'Agent created',
  deployment: 'Deployment created',
  call: 'Call received',
  appointment: 'Appointment booked',
}

export default function AdminOverview() {
  const { data, error, loading, reload } = useFetch(() => api.get('/platform/dashboard'), [])

  return (
    <div>
      <PageTitle
        title="Platform overview"
        subtitle="Across every organization on the platform."
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
            <StatCard label="Organizations" value={data.total_organizations} icon={<OrganizationIcon width={17} height={17} />} />
            <StatCard label="Active orgs" value={data.active_organizations} variant="success" icon={<OrganizationIcon width={17} height={17} />} />
            <StatCard label="Users" value={data.total_users} icon={<UsersIcon width={17} height={17} />} />
            <StatCard label="Agents" value={data.total_agents} icon={<AgentIcon width={17} height={17} />} />
            <StatCard label="Calls today" value={data.calls_today} icon={<PhoneIcon width={17} height={17} />} />
            <StatCard label="Calls this month" value={data.calls_this_month} icon={<CallIcon width={17} height={17} />} />
            <StatCard label="Customers" value={data.total_customers} icon={<UsersIcon width={17} height={17} />} />
            <StatCard label="Appointments" value={data.appointments_scheduled} variant="info" icon={<CalendarIcon width={17} height={17} />} />
            <StatCard label="Deployments" value={data.total_deployments} icon={<DeployIcon width={17} height={17} />} />
            <StatCard label="Website / Phone" value={`${data.website_deployments} / ${data.phone_deployments}`} icon={<WebsiteIcon width={17} height={17} />} />
          </div>

          <div className="grid two">
            <ChartCard title="Calls — last 14 days" subtitle={`${data.total_calls} total calls`}>
              {!data.growth || data.growth.calls_by_day.length === 0 ? (
                <Empty>No call data yet.</Empty>
              ) : (
                <BarChart data={data.growth.calls_by_day} height={200} />
              )}
            </ChartCard>
            <Card title="Channel breakdown">
              {!data.channel_breakdown || data.channel_breakdown.length === 0 ? (
                <Empty>No conversations yet.</Empty>
              ) : (
                <ul className="breakdown">
                  {data.channel_breakdown.map((item) => (
                    <li key={item.channel}>
                      <span>{item.channel}</span>
                      <strong>{item.count}</strong>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <div className="grid two">
            <Card title="Outcome breakdown">
              {!data.outcome_breakdown || data.outcome_breakdown.length === 0 ? (
                <Empty>No outcomes recorded yet.</Empty>
              ) : (
                <ul className="breakdown">
                  {data.outcome_breakdown.map((item) => (
                    <li key={item.outcome}>
                      <span>{item.outcome}</span>
                      <strong>{item.count}</strong>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card title="Recent activity">
              {!data.recent_activity || data.recent_activity.length === 0 ? (
                <Empty>No recent activity.</Empty>
              ) : (
                <ul className="activity-list">
                  {data.recent_activity.map((event, index) => (
                    <li key={`${event.type}-${index}`}>
                      <span className="activity-dot">
                        <ChartIcon width={13} height={13} />
                      </span>
                      <div className="activity-body">
                        <div className="activity-title">
                          {activityLabel[event.type] || event.action}
                        </div>
                        <div className="activity-meta">
                          {event.label}
                          {event.organization ? ` · ${event.organization}` : ''}
                        </div>
                      </div>
                      <span className="activity-time">{formatDay(event.timestamp)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <Card title="Growth — organizations & agents">
            <div className="grid two">
              <div>
                <div className="muted small" style={{ marginBottom: 8 }}>
                  Organizations created (cumulative)
                </div>
                <BarChart data={data.growth.organizations_growth} height={150} />
              </div>
              <div>
                <div className="muted small" style={{ marginBottom: 8 }}>
                  Agents created (cumulative)
                </div>
                <BarChart data={data.growth.agents_created} height={150} />
              </div>
            </div>
          </Card>

          <div className="page-actions">
            <Link to="/admin/organizations" className="btn">
              Manage organizations
            </Link>
            <Link to="/admin/analytics" className="btn">
              Platform analytics
            </Link>
          </div>
        </>
      )}
    </div>
  )
}