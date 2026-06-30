import { useEffect, useState } from 'react'
import { modelsService } from '../services/models'

function Models() {
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    modelsService
      .getModels()
      .then((res) => {
        setModels(res.data?.data || [])
        setLoading(false)
      })
      .catch((err) => {
        console.error(err)
        setError('Failed to load models')
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-slate-900">Models</h2>
        <p className="text-sm text-slate-500">Loading models...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-slate-900">Models</h2>
        <p className="text-sm text-red-500">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-900">Models</h2>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-panel">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Model</th>
              <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Object</th>
              <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Owner</th>
              <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {models.length === 0 ? (
              <tr>
                <td colSpan="4" className="px-6 py-8 text-center text-sm text-slate-500">
                  No models available.
                </td>
              </tr>
            ) : (
              models.map((model) => (
                <tr key={model.id} className="hover:bg-slate-50">
                  <td className="px-6 py-4 text-sm font-medium text-slate-900">{model.id}</td>
                  <td className="px-6 py-4 text-sm text-slate-500">{model.object}</td>
                  <td className="px-6 py-4 text-sm text-slate-500">{model.owned_by}</td>
                  <td className="px-6 py-4 text-sm text-slate-500">
                    {new Date(model.created * 1000).toLocaleString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Models