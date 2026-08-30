import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import {
  Badge,
  Button,
  Card,
  Empty,
  ErrorBox,
  Modal,
  PageTitle,
  formatDate,
  toast,
} from '../../components/Ui'

export default function CmsVersions() {
  const [versions, setVersions] = useState(null)
  const [error, setError] = useState(null)
  const [restoreTarget, setRestoreTarget] = useState(null)
  const [working, setWorking] = useState(false)

  const reload = () => {
    setError(null)
    setVersions(null)
    api
      .get('/platform/cms/versions')
      .then(setVersions)
      .catch((err) => setError(err))
  }

  useEffect(() => {
    reload()
  }, [])

  async function confirmRestore() {
    setWorking(true)
    try {
      const result = await api.post(`/platform/cms/restore/${restoreTarget.number}`)
      setRestoreTarget(null)
      toast(result.detail || 'Version restored as a draft')
    } catch (err) {
      window.alert(err.message || 'Restore failed')
    } finally {
      setWorking(false)
    }
  }

  return (
    <div>
      <PageTitle
        title="CMS versions"
        subtitle="Every publish is a snapshot. Restoring copies a version into a new draft — it does not republish."
        actions={
          <>
            <Link className="btn" to="/admin/cms">
              Back to CMS
            </Link>
            <Link className="btn primary" to="/admin/cms/preview">
              Preview draft
            </Link>
          </>
        }
      />

      {error ? (
        <ErrorBox message={error} onRetry={reload} />
      ) : !versions ? (
        <Empty>Loading…</Empty>
      ) : versions.length === 0 ? (
        <Empty>No versions published yet.</Empty>
      ) : (
        <Card>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Published</th>
                  <th>By</th>
                  <th>Status</th>
                  <th>Summary</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {versions.map((version) => (
                  <tr key={version.id}>
                    <td>
                      <strong>{`v${version.number}`}</strong>
                    </td>
                    <td>{formatDate(version.published_at)}</td>
                    <td>{version.published_by || '—'}</td>
                    <td>
                      <Badge variant={version.is_current ? 'success' : ''}>
                        {version.is_current ? 'Live' : 'Archived'}
                      </Badge>
                    </td>
                    <td className="muted" style={{ whiteSpace: 'pre-line' }}>
                      {version.summary}
                    </td>
                    <td>
                      <div className="row-actions">
                        <Link className="btn small" to="/admin/cms/preview">
                          Preview
                        </Link>
                        <Button
                          className="btn small"
                          disabled={version.is_current}
                          onClick={() => setRestoreTarget(version)}
                          title={version.is_current ? 'This version is already live' : 'Copy into a new draft'}
                        >
                          Restore
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Card title="How restore works">
        <p className="muted">
          Restore copies the selected version's content back into the editable draft tables — it
          never overwrites the live site. Review the result in <strong>Preview draft</strong>, then
          publish to promote the restored draft as a new version.
        </p>
      </Card>

      <Modal
        open={Boolean(restoreTarget)}
        onClose={() => setRestoreTarget(null)}
        title={`Restore v${restoreTarget?.number}?`}
      >
        <p>
          This copies <strong>{`v${restoreTarget?.number}`}</strong> into a new draft. The live
          site keeps showing the current published version until you publish again.
        </p>
        <div className="form-actions">
          <Button onClick={() => setRestoreTarget(null)}>Cancel</Button>
          <Button className="primary" onClick={confirmRestore} disabled={working} loading={working}>
            {working ? 'Restoring…' : 'Restore as draft'}
          </Button>
        </div>
      </Modal>
    </div>
  )
}