function StatCard({ title, value, unit }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-panel">
      <p className="text-sm text-slate-500">{title}</p>
      <div className="mt-2 flex items-baseline gap-1">
        <p className="text-2xl font-semibold text-slate-900">{value}</p>
        {unit && <span className="text-base text-slate-500">{unit}</span>}
      </div>
    </div>
  )
}

export default StatCard
