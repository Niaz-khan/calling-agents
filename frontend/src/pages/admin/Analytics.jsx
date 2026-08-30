import { useState } from 'react'
import { api } from '../../api'
import {
  BarChart,
  Card,
  ChartCard,
  Empty,
  ErrorBox,
  PageTitle,
  Seg,
  StatCard,
  useFetch,
  statusVariant,
  Badge,
} from '../../components/Ui'
import {
  OrganizationIcon,
  UsersIcon,
  AgentIcon,
  DeployIcon,
  PhoneIcon,
  CallIcon,
  CalendarIcon,
} from '../../components/icons'

export default function AdminAnalytics() {
  const [days, setDays] = useState(30)
  const { data, error, loading, reload } = useFetch(
    () => api.get(`/platform/analytics?days=${days}`),
    [days]
  )

  if (error) {
    return (
      <div>
        <PageTitle title="Platform analytics" />
        <ErrorBox message={error} onRetry={reload} />
      </div>
    )
  }

  return (
    <div>
      <PageTitle
        title="Platform analytics"
        subtitle="Aggregate metrics across every organization."
        actions={
          <Seg
            options={[
              { value: '7', label: '7d' },
              { value: '30', label: '30d' },
              { value: '90', label: '90d' },
            ]}
            value={String(days)}
            onChange={(value) => setDays(Number(value))}
          />
        }
      />

      {loading || !data ? (
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
            <StatCard label="Organizations" value={data.totals.organizations} icon={<OrganizationIcon width={17} height={17} />} />
            <StatCard label="Users" value={data.totals.users} icon={<UsersIcon width={17} height={17} />} />
            <StatCard label="Agents" value={data.totals.agents} icon={<AgentIcon width={17} height={17} />} />
            <StatCard label="Deployments" value={data.totals.deployments} icon={<DeployIcon width={17} height={17} />} />
            <StatCard label="Phone calls" value={data.totals.phone_calls} icon={<PhoneIcon width={17} height={17} />} />
            <StatCard label="Conversations" value={data.totals.conversations} icon={<CallIcon width={17} height={17} />} />
            <StatCard label="Customers" value={data.totals.customers} icon={<UsersIcon width={17} height={17} />} />
            <StatCard label="Appointments" value={data.totals.appointments} icon={<CalendarIcon width={17} height={17} />} />
          </div>

          <ChartCard title="Calls — per day" subtitle={`Last ${days} days`}>
            {!data.growth || data.growth.calls_by_day.length === 0 ? (
              <Empty>No call data yet.</Empty>
            ) : (
              <BarChart data={data.growth.calls_by_day} height={200} />
            )}
          </ChartCard>

          <Card title="Call status">
            {Object.keys(data.call_status).length === 0 ? (
              <Empty>No calls yet.</Empty>
            ) : (
              <div className="grid two">
                <ul className="breakdown">
                  {Object.entries(data.call_status).map(([status, count]) => (
                    <li key={status}>
                      <span>
                        <Badge variant={statusVariant(status)}>{status.replace('_', ' ')}</Badge>
                      </span>
                      <strong>{count}</strong>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          <div className="grid two">
            <Card title="Channel breakdown">
              {data.channel_breakdown.length === 0 ? (
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
            <Card title="Outcome breakdown">
              {data.outcome_breakdown.length === 0 ? (
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
          </div>
        </>
      )}
    </div>
  )
}