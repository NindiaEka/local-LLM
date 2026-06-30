import { useEffect, useState } from 'react'
import StatCard from '../components/StatCard'
import { analyticsService } from '../services/analytics'

function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    analyticsService
      .getSummary()
      .then((res) => {
        setData(res.data)
        setLoading(false)
      })
      .catch((err) => {
        setError('Failed to load analytics')
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-semibold text-slate-900">Dashboard</h2>
        <p className="text-slate-500">Loading analytics...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-semibold text-slate-900">Dashboard</h2>
        <p className="text-red-500">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-900">Dashboard</h2>
      
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <StatCard title="Total Requests" value={data?.total_requests} />
        <StatCard title="Success Requests" value={data?.success_requests} />
        <StatCard title="Failed Requests" value={data?.failed_requests} />
        <StatCard title="Average Latency" value={data?.avg_latency_ms} unit="ms" />
        <StatCard title="Active API Keys" value={data?.active_api_keys} />
      </div>
    </div>
  )
}

export default Dashboard