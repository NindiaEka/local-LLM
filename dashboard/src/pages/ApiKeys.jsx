import { useEffect, useState } from 'react'
import { AlertTriangle, Check, Copy, Plus, Trash2 } from 'lucide-react'
import { keysService } from '../services/keys'

function ApiKeys() {
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(true)

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [appName, setAppName] = useState('')

  const [isSuccessOpen, setIsSuccessOpen] = useState(false)
  const [newKeyDetails, setNewKeyDetails] = useState(null)
  const [copied, setCopied] = useState(false)

  const [isDeleteOpen, setIsDeleteOpen] = useState(false)
  const [keyToDelete, setKeyToDelete] = useState(null)

  const fetchKeys = () => {
    setLoading(true)
    keysService
      .getKeys()
      .then((res) => {
        setKeys(res.data)
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchKeys()
  }, [])

  const handleCreate = (e) => {
    e.preventDefault()
    keysService
      .createKey({ name: appName })
      .then((res) => {
        setNewKeyDetails(res.data)
        setAppName('')
        setIsCreateOpen(false)
        setIsSuccessOpen(true)
        fetchKeys()
      })
      .catch((err) => console.error(err))
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(newKeyDetails.key)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDelete = () => {
    if (!keyToDelete) return
    keysService
      .deleteKey(keyToDelete.id)
      .then(() => {
        setIsDeleteOpen(false)
        setKeyToDelete(null)
        fetchKeys()
      })
      .catch((err) => console.error(err))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-900">API Keys</h2>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          <Plus size={16} /> Create API Key
        </button>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Name</th>
              <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Status</th>
              <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Created At</th>
              <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan="4" className="px-6 py-8 text-center text-sm text-slate-500">Loading API keys...</td>
              </tr>
            ) : keys.length === 0 ? (
              <tr>
                <td colSpan="4" className="px-6 py-8 text-center text-sm text-slate-500">No API keys found.</td>
              </tr>
            ) : (
              keys.map((key) => (
                <tr key={key.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm font-medium text-slate-900">{key.name}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${key.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-700'}`}>
                      {key.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-500">{new Date(key.created_at).toLocaleString()}</td>
                  <td className="px-6 py-4 text-right text-sm">
                    <button
                      onClick={() => {
                        setKeyToDelete(key)
                        setIsDeleteOpen(true)
                      }}
                      className="text-red-500 hover:text-red-700 disabled:opacity-50"
                    >
                      <Trash2 size={18} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900">Create New API Key</h3>
            <form onSubmit={handleCreate} className="mt-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700">Application Name</label>
                <input
                  type="text"
                  required
                  value={appName}
                  onChange={(e) => setAppName(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500"
                  placeholder="e.g. Production App"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!appName.trim()}
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Success Modal */}
      {isSuccessOpen && newKeyDetails && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                <Check size={20} />
              </div>
              <h3 className="text-lg font-semibold text-slate-900">API Key Created</h3>
            </div>
            <div className="mt-4 rounded-lg bg-amber-50 p-4">
              <div className="flex gap-3 text-amber-800">
                <AlertTriangle size={20} className="shrink-0" />
                <p className="text-sm">Please copy this API key now. For your security, it will <strong>never be shown again</strong>.</p>
              </div>
            </div>
            <div className="mt-4 flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3">
              <code className="text-sm text-slate-800 tracking-wide break-all">{newKeyDetails.key}</code>
              <button
                onClick={copyToClipboard}
                className="ml-3 shrink-0 rounded-md p-2 text-slate-500 hover:bg-slate-200 hover:text-slate-800"
                title="Copy to clipboard"
              >
                {copied ? <Check size={18} className="text-emerald-600" /> : <Copy size={18} />}
              </button>
            </div>
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => {
                  setIsSuccessOpen(false)
                  setNewKeyDetails(null)
                }}
                className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirm Modal */}
      {isDeleteOpen && keyToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900">Revoke API Key</h3>
            <p className="mt-2 text-sm text-slate-600">
              Are you sure you want to revoke the key <strong>{keyToDelete.name}</strong>? This action cannot be undone and any applications using this key will immediately lose access.
            </p>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setIsDeleteOpen(false)}
                className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                Revoke Key
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ApiKeys