import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../../api'
import {
  Badge,
  Card,
  Empty,
  ErrorBox,
  formatDate,
  formatDuration,
  PageTitle,
  statusVariant,
  Tabs,
} from '../../components/Ui'

const TABS = [
  'Overview',
  'Users',
  'Agents',
  'Deployments',
  'Calls',
  'Appointments',
  'Customers',
  'Phone numbers',
  'Knowledge',
  'Services',
]

export default function AdminOrganizationDetail() {
  const { id } = useParams()
  const [tab, setTab] = useState('Overview')

  const [detail, setDetail] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let mounted = true
    setDetail(null)
    setError(null)
    api
      .get(`/platform/organizations/${id}/detail`)
      .then((data) => mounted && setDetail(data))
      .catch((err) => mounted && setError(err))
    return () => {
      mounted = false
    }
  }, [id])

  const summaryKeys = [
    ['members_count', 'Members'],
    ['agents_count', 'Agents'],
    ['active_agents_count', 'Active agents'],
    ['deployments_count', 'Deployments'],
    ['phone_numbers_count', 'Phone numbers'],
    ['calls_count', 'Calls'],
    ['conversations_count', 'Conversations'],
    ['customers_count', 'Customers'],
    ['appointments_count', 'Appointments'],
    ['knowledge_bases_count', 'Knowledge bases'],
  ]

  const summary = detail ? detail.summary : null

  return (
    <div>
      {detail && (
        <PageTitle
          title={detail.organization.business_name || detail.organization.name}
          subtitle={`Organization #${detail.organization.id} · ${detail.organization.timezone}`}
          actions={
            <Badge variant={detail.organization.is_active ? 'success' : ''}>
              {detail.organization.is_active ? 'Active' : 'Inactive'}
            </Badge>
          }
        />
      )}

      <Tabs tabs={TABS} active={tab} onChange={setTab} />

      {error ? (
        <ErrorBox message={error} />
      ) : !detail ? (
        <Empty>Loading…</Empty>
      ) : tab === 'Overview' ? (
        <>
          <Card title="Summary">
            <div className="meta-grid">
              {summaryKeys.map(([key, label]) => (
                <div className="meta-stat" key={key}>
                  <div className="val">{summary[key] ?? 0}</div>
                  <div className="lab">{label}</div>
                </div>
              ))}
            </div>
          </Card>
          {detail.organization.address || detail.organization.contact_phone || detail.organization.website_url ? (
            <Card title="Contact">
              <ul className="breakdown">
                {detail.organization.contact_phone ? (
                  <li>
                    <span>Phone</span>
                    <strong>{detail.organization.contact_phone}</strong>
                  </li>
                ) : null}
                {detail.organization.address ? (
                  <li>
                    <span>Address</span>
                    <strong>{detail.organization.address}</strong>
                  </li>
                ) : null}
                {detail.organization.website_url ? (
                  <li>
                    <span>Website</span>
                    <strong>{detail.organization.website_url}</strong>
                  </li>
                ) : null}
              </ul>
            </Card>
          ) : null}
        </>
      ) : (
        <ResourceTab tab={tab} organizationId={id} />
      )}
    </div>
  )
}

function ResourceTab({ tab, organizationId }) {
  const pathMap = {
    Users: 'users',
    Agents: 'agents',
    Deployments: 'deployments',
    Calls: 'calls',
    Appointments: 'appointments',
    Customers: 'customers',
    'Phone numbers': 'phone-numbers',
    Knowledge: 'knowledge',
    Services: 'services',
  }
  const endpoint = pathMap[tab]
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let mounted = true
    setData(null)
    setError(null)
    api
      .get(`/platform/organizations/${organizationId}/${endpoint}`)
      .then((rows) => mounted && setData(rows))
      .catch((err) => mounted && setError(err))
    return () => {
      mounted = false
    }
  }, [organizationId, endpoint])

  if (error) return <ErrorBox message={error} />
  if (!data) return <Empty>Loading…</Empty>

  switch (tab) {
    case 'Users':
      return (
        <Card>
          {data.length === 0 ? <Empty>No users in this organization.</Empty> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>User</th><th>Email</th><th>Platform role</th><th>Org role</th><th>Joined</th></tr></thead>
                <tbody>
                  {data.map((user) => (
                    <tr key={user.id}>
                      <td>{user.full_name || '—'}</td>
                      <td>{user.email}</td>
                      <td>
                        {user.platform_role ? <Badge variant="info">{user.platform_role}</Badge> : '—'}
                      </td>
                      <td>{user.organizations.find((o) => o.id === Number(organizationId))?.role || '—'}</td>
                      <td>{formatDate(user.date_joined)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )
    case 'Agents':
      return (
        <Card>
          {data.length === 0 ? <Empty>No agents.</Empty> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Status</th><th>Agent</th><th>Deployments</th><th>Conversations</th><th>Created</th></tr></thead>
                <tbody>
                  {data.map((agent) => (
                    <tr key={agent.id}>
                      <td><Badge variant={agent.is_active ? 'success' : ''}>{agent.is_active ? 'Active' : 'Inactive'}</Badge></td>
                      <td>{agent.name}</td>
                      <td>{agent.deployments_count}</td>
                      <td>{agent.conversations_count}</td>
                      <td>{formatDate(agent.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )
    case 'Deployments':
      return (
        <Card>
          {data.length === 0 ? <Empty>No deployments.</Empty> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Status</th><th>Deployment</th><th>Channel</th><th>Agent</th><th>Conversations</th></tr></thead>
                <tbody>
                  {data.map((deployment) => (
                    <tr key={deployment.id}>
                      <td><Badge variant={deployment.enabled ? 'success' : ''}>{deployment.enabled ? 'Enabled' : 'Disabled'}</Badge></td>
                      <td>{deployment.name}</td>
                      <td>{deployment.channel}</td>
                      <td>{deployment.agent.name}</td>
                      <td>{deployment.conversations_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )
    case 'Calls':
      return (
        <Card>
          {data.length === 0 ? <Empty>No calls.</Empty> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Status</th><th>Direction</th><th>Agent</th><th>Phone</th><th>Started</th><th>Duration</th></tr></thead>
                <tbody>
                  {data.map((call) => (
                    <tr key={call.id}>
                      <td><Badge variant={statusVariant((call.provider_status || call.status))}>{call.provider_status || call.status}</Badge></td>
                      <td>{call.direction}</td>
                      <td>{call.agent.name}</td>
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
      )
    case 'Appointments':
      return (
        <Card>
          {data.length === 0 ? <Empty>No appointments.</Empty> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Status</th><th>Customer</th><th>Service</th><th>Start</th><th>End</th></tr></thead>
                <tbody>
                  {data.map((appointment) => (
                    <tr key={appointment.id}>
                      <td><Badge variant={statusVariant(appointment.status)}>{appointment.status}</Badge></td>
                      <td>{appointment.customer_name}</td>
                      <td>{appointment.service_name || '—'}</td>
                      <td>{formatDate(appointment.start_time)}</td>
                      <td>{formatDate(appointment.end_time)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )
    case 'Customers':
      return (
        <Card>
          {data.length === 0 ? <Empty>No customers.</Empty> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Name</th><th>Phone</th><th>Email</th><th>Conversations</th><th>Created</th></tr></thead>
                <tbody>
                  {data.map((customer) => (
                    <tr key={customer.id}>
                      <td>{customer.name}</td>
                      <td>{customer.phone_number || '—'}</td>
                      <td>{customer.email || '—'}</td>
                      <td>{customer.conversations_count}</td>
                      <td>{formatDate(customer.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )
    case 'Phone numbers':
      return (
        <Card>
          {data.length === 0 ? <Empty>No phone numbers.</Empty> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Status</th><th>Phone number</th><th>Provider</th><th>Agent</th><th>Capabilities</th></tr></thead>
                <tbody>
                  {data.map((number) => (
                    <tr key={number.id}>
                      <td><Badge variant={number.is_active ? 'success' : ''}>{number.is_active ? 'Active' : 'Inactive'}</Badge></td>
                      <td>{number.phone_number}</td>
                      <td>{number.provider}</td>
                      <td>{number.agent.name}</td>
                      <td>{(number.capabilities || []).join(', ') || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )
    case 'Knowledge':
      return (
        <Card>
          {data.length === 0 ? <Empty>No knowledge bases.</Empty> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Name</th><th>Agent</th><th>Documents</th><th>Updated</th></tr></thead>
                <tbody>
                  {data.map((kb) => (
                    <tr key={kb.id}>
                      <td>{kb.name}</td>
                      <td>{kb.agent.name}</td>
                      <td>{kb.documents_count}</td>
                      <td>{formatDate(kb.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )
    case 'Services':
      return (
        <Card>
          {data.length === 0 ? <Empty>No services.</Empty> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Status</th><th>Service</th><th>Duration</th><th>Price</th></tr></thead>
                <tbody>
                  {data.map((service) => (
                    <tr key={service.id}>
                      <td><Badge variant={service.active ? 'success' : ''}>{service.active ? 'Active' : 'Inactive'}</Badge></td>
                      <td>{service.name}</td>
                      <td>{service.duration_minutes} min</td>
                      <td>{service.price != null ? `${service.price} ${service.currency}` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )
    default:
      return null
  }
}