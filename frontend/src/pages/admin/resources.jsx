import { useState } from 'react'
import { api } from '../../api'
import {
  Badge,
  Card,
  Empty,
  ErrorBox,
  formatDate,
  formatDuration,
  PageTitle,
  Select,
  statusVariant,
  useFetch,
} from '../../components/Ui'

const FILTERS = {
  agents: [],
  deployments: [],
  calls: [],
  customers: [],
  appointments: [{ param: 'status', op: 'status', label: 'Status' }],
  'phone-numbers': [],
  knowledge: [],
  services: [],
}

const LABELS = {
  agents: ['Status', 'Agent', 'Org', 'Deployments', 'Conversations', 'Created'],
  deployments: ['Status', 'Deployment', 'Channel', 'Agent', 'Org', 'Conversations', 'Created'],
  calls: ['Status', 'Direction', 'Phone', 'Agent', 'Org', 'Started', 'Duration'],
  customers: ['Name', 'Phone', 'Email', 'Org', 'Conversations', 'Created'],
  appointments: ['Status', 'Customer', 'Service', 'Agent', 'Org', 'Start', 'End'],
  'phone-numbers': ['Status', 'Phone number', 'Provider', 'Agent', 'Org', 'Capabilities', 'Created'],
  knowledge: ['Name', 'Org', 'Agent', 'Documents', 'Updated'],
  services: ['Status', 'Service', 'Duration', 'Price', 'Org', 'Created'],
}

function cellFor(resource, key, record) {
  switch (key) {
    case 'status':
      return <Badge variant={statusVariant(record.status)}>{record.status}</Badge>
    case 'provider_status':
      return <Badge variant={statusVariant(record.provider_status)}>{record.provider_status}</Badge>
    case 'is_active':
    case 'enabled':
    case 'active':
      return (
        <Badge variant={record[key] ? 'success' : ''}>
          {record[key]
            ? key === 'enabled'
              ? 'Enabled'
              : 'Active'
            : key === 'enabled'
              ? 'Disabled'
              : 'Inactive'}
        </Badge>
      )
    case 'agent.name':
      return record.agent ? record.agent.name : '—'
    case 'organization':
      return record.organization ? record.organization.name : '—'
    case 'capabilities':
      return Array.isArray(record.capabilities) && record.capabilities.length
        ? record.capabilities.join(', ')
        : '—'
    case 'price':
      return record.price == null ? '—' : `${record.price} ${record.currency || ''}`.trim()
    case 'duration_minutes':
      return record.duration_minutes != null ? `${record.duration_minutes} min` : '—'
    case 'started_at':
    case 'created_at':
    case 'updated_at':
    case 'start_time':
    case 'end_time':
      return formatDate(record[key])
    case 'duration_seconds':
      return formatDuration(record[key])
    default:
      return record[key] ?? '—'
  }
}

function buildPage(resource, title, subtitle) {
  return function AdminResourceList() {
    const [orgId, setOrgId] = useState('')
    const [extra, setExtra] = useState('')
    const fetchEm = () => {
      const params = new URLSearchParams()
      if (orgId) params.set('organization_id', orgId)
      if (extra) params.set('status', extra)
      const qs = params.toString()
      return api.get(`/platform/${resource}${qs ? `?${qs}` : ''}`)
    }
    const { data, error, loading, reload } = useFetch(fetchEm, [orgId, extra])
    const rows = data || []

    const orgsResult = useFetch(() => api.get('/platform/organizations'), [])
    const orgs = orgsResult.data || []

    const columns = LABELS[resource]

    if (error) {
      return (
        <div>
          <PageTitle title={title} />
          <ErrorBox message={error} onRetry={reload} />
        </div>
      )
    }

    return (
      <div>
        <PageTitle title={title} subtitle={subtitle} />
        <Card className="toolbar-card">
          <div className="toolbar">
            <Select value={orgId} onChange={(event) => setOrgId(event.target.value)}>
              <option value="">All organizations</option>
              {orgs.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.business_name || org.name}
                </option>
              ))}
            </Select>
            {FILTERS[resource].filter((f) => f.op === 'status').map((f) => (
              <Select key={f.param} value={extra} onChange={(event) => setExtra(event.target.value)}>
                <option value="">All statuses</option>
                <option value="scheduled">Scheduled</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </Select>
            ))}
          </div>
        </Card>
        {loading ? (
          <Empty>Loading…</Empty>
        ) : rows.length === 0 ? (
          <Empty>No {title.toLowerCase()} found.</Empty>
        ) : (
          <Card>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    {columns.map((column) => (
                      <th key={column}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((record) => (
                    <tr key={record.id}>
                      {columns.map((column, index) => (
                        <td key={index}>{cellFor(resource, COLUMN_KEYS[resource][index], record)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    )
  }
}

const COLUMN_KEYS = {
  agents: ['is_active', 'name', 'organization', 'deployments_count', 'conversations_count', 'created_at'],
  deployments: ['enabled', 'name', 'channel', 'agent.name', 'organization', 'conversations_count', 'created_at'],
  calls: ['provider_status', 'direction', 'caller_number', 'agent.name', 'organization', 'started_at', 'duration_seconds'],
  customers: ['name', 'phone_number', 'email', 'organization', 'conversations_count', 'created_at'],
  appointments: ['status', 'customer_name', 'service_name', 'agent.name', 'organization', 'start_time', 'end_time'],
  'phone-numbers': ['is_active', 'phone_number', 'provider', 'agent.name', 'organization', 'capabilities', 'created_at'],
  knowledge: ['name', 'organization', 'agent.name', 'documents_count', 'updated_at'],
  services: ['active', 'name', 'duration_minutes', 'price', 'organization', 'created_at'],
}

export const AdminAgents = buildPage('agents', 'Agents', 'Every agent across all organizations.')
export const AdminDeployments = buildPage('deployments', 'Deployments', 'Website and phone deployments across all organizations.')
export const AdminCalls = buildPage('calls', 'Calls', 'All phone conversations on the platform.')
export const AdminCustomers = buildPage('customers', 'Customers', 'All customers across all organizations.')
export const AdminAppointments = buildPage('appointments', 'Appointments', 'All bookings across all organizations.')
export const AdminPhoneNumbers = buildPage('phone-numbers', 'Phone numbers', 'All phone numbers across all organizations.')
export const AdminKnowledge = buildPage('knowledge', 'Knowledge', 'Every knowledge base across all organizations.')
export const AdminServices = buildPage('services', 'Services', 'Every service catalogue entry across all organizations.')