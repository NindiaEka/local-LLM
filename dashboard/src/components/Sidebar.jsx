import { BarChart3, Boxes, KeyRound, LayoutDashboard } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const links = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard },
  { label: 'API Keys', to: '/apikeys', icon: KeyRound },
  { label: 'Models', to: '/models', icon: Boxes },
  { label: 'Analytics', to: '/analytics', icon: BarChart3 },
]

function Sidebar({ isOpen, onClose }) {
  return (
    <>
      <div
        className={`fixed inset-0 z-30 bg-slate-900/40 transition-opacity md:hidden ${
          isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={onClose}
      />
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 transform border-r border-slate-200 bg-white px-4 py-6 transition-transform md:static md:z-auto md:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
      <nav className="space-y-1">
        {links.map(({ label, to, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition ${
                isActive
                  ? 'bg-slate-900 text-white shadow-panel'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`
            }
          >
            <Icon size={16} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      </aside>
    </>
  )
}

export default Sidebar