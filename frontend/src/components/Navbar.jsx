import { NavLink } from 'react-router-dom'
import { Search, LayoutDashboard, FileText } from 'lucide-react'

export default function Navbar() {
  const links = [
    { to: '/jobs', icon: <Search size={18} />, label: 'Job Search' },
    { to: '/applications', icon: <LayoutDashboard size={18} />, label: 'Applications' },
    { to: '/resume', icon: <FileText size={18} />, label: 'Resume' },
  ]

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 glass border-r border-white/5 flex flex-col p-6 z-50">
      {/* Logo */}
      <div className="mb-10">
        <h1 className="text-xl font-bold text-white tracking-tight">
          Job<span className="text-accent">Hunt</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">AI-powered job tracker</p>
      </div>

      {/* Nav Links */}
      <nav className="flex flex-col gap-2">
        {links.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 text-sm font-medium ${
                isActive
                  ? 'bg-accent/20 text-accent border border-accent/30'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`
            }
          >
            {icon}
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Bottom badge */}
      <div className="mt-auto">
        <div className="glass rounded-lg p-3 text-center">
          <p className="text-xs text-slate-500">Powered by</p>
          <p className="text-xs font-semibold text-accent mt-0.5">Claude AI</p>
        </div>
      </div>
    </aside>
  )
}