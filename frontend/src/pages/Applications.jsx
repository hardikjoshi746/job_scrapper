import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Trash2, ExternalLink, Zap, Search } from 'lucide-react'
import client from '../api/client'
import toast from 'react-hot-toast'
import ApplyModal from '../components/ApplyModal'

const STATUSES = ['saved', 'applied', 'interview', 'offer', 'rejected']

async function fetchApplications() {
  const res = await client.get('/applications')
  return res.data
}

async function deleteApplication(id) {
  await client.delete(`/applications/${id}`)
}

async function updateStatus(id, status) {
  await client.patch(`/applications/${id}`, { status })
}

async function triggerApply(id) {
  await client.post(`/apply/${id}`)
}

export default function Applications() {
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [applyModalApp, setApplyModalApp] = useState(null)

  const { data: applications = [], isLoading } = useQuery({
    queryKey: ['applications'],
    queryFn: fetchApplications,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteApplication,
    onSuccess: () => {
      queryClient.invalidateQueries(['applications'])
      toast.success('Application deleted')
    },
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }) => updateStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries(['applications']),
  })

const counts = STATUSES.reduce((acc, s) => {
    acc[s] = applications.filter(a => a.status === s).length
    return acc
  }, {})

  const filtered = applications
    .filter(a => filter === 'all' || a.status === filter)
    .filter(a =>
      !search ||
      a.job_title.toLowerCase().includes(search.toLowerCase()) ||
      a.company.toLowerCase().includes(search.toLowerCase())
    )

  if (isLoading) return <div className="text-slate-400 text-center py-20">Loading...</div>

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-1">Applications</h1>
        <p className="text-slate-400 text-sm">{applications.length} total applications</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-3 mb-8 stagger">
        {[
          { label: 'Saved', key: 'saved', color: 'text-slate-300' },
          { label: 'Applied', key: 'applied', color: 'text-blue-300' },
          { label: 'Interview', key: 'interview', color: 'text-violet-300' },
          { label: 'Offer', key: 'offer', color: 'text-green-300' },
          { label: 'Rejected', key: 'rejected', color: 'text-red-300' },
        ].map(({ label, key, color }) => (
          <div key={key} className="glass p-4 text-center">
            <p className={`text-2xl font-bold ${color}`}>{counts[key] || 0}</p>
            <p className="text-xs text-slate-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Filters + Search */}
      <div className="flex items-center justify-between gap-4 mb-6 flex-wrap">
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-1.5 rounded-full text-xs font-medium border transition-all ${
              filter === 'all'
                ? 'bg-accent/20 text-accent border-accent/30'
                : 'bg-white/5 text-slate-400 border-white/10 hover:border-white/20'
            }`}
          >
            All ({applications.length})
          </button>
          {STATUSES.map(s => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-4 py-1.5 rounded-full text-xs font-medium border transition-all capitalize ${
                filter === s
                  ? 'bg-accent/20 text-accent border-accent/30'
                  : 'bg-white/5 text-slate-400 border-white/10 hover:border-white/20'
              }`}
            >
              {s} ({counts[s] || 0})
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="flex items-center gap-2 rounded-lg px-3 py-2 w-56" style={{background: 'rgba(255,255,255,0.05)'}}>
          <Search size={14} className="text-slate-400 shrink-0" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search..."
            className="text-white text-sm outline-none w-full placeholder-slate-500"
            style={{background: 'transparent'}}
          />
        </div>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="text-center py-20 text-slate-500">
          {applications.length === 0
            ? 'No applications yet. Save jobs from the Job Search page!'
            : 'No results match your filter.'}
        </div>
      ) : (
        <div className="glass overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5 text-slate-400 text-xs uppercase tracking-wide">
                <th className="text-left px-5 py-3">Job</th>
                <th className="text-left px-5 py-3">Company</th>
                <th className="text-left px-5 py-3">Status</th>
                <th className="text-left px-5 py-3">Applied</th>
                <th className="text-left px-5 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((app, i) => (
                <tr
                  key={app.id}
                  className={`border-b border-white/5 hover:bg-white/3 transition-colors ${
                    i === filtered.length - 1 ? 'border-b-0' : ''
                  }`}
                >
                  <td className="px-5 py-3">
                    <span className="text-white font-medium">{app.job_title}</span>
                  </td>
                  <td className="px-5 py-3 text-slate-400">{app.company}</td>
                  <td className="px-5 py-3">
                    <select
                      value={app.status}
                      onChange={e => statusMutation.mutate({ id: app.id, status: e.target.value })}
                      className={`text-xs px-2 py-1 rounded-full border cursor-pointer capitalize status-${app.status}`}
                      style={{background: 'transparent'}}
                    >
                      {STATUSES.map(s => (
                        <option key={s} value={s} style={{background: '#0f0f1a'}}>{s}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-5 py-3 text-slate-500 text-xs">
                    {app.applied_date ? new Date(app.applied_date).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setApplyModalApp(app)}
                        disabled={!app.job_url}
                        className="flex items-center gap-1 text-xs text-accent hover:text-accent-hover disabled:opacity-30 transition-colors"
                        title={!app.job_url ? 'No job URL' : 'Apply to this job'}
                      >
                        <Zap size={13} />
                        Apply
                      </button>
                      {app.job_url && (
                        <a
                          href={app.job_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-slate-400 hover:text-accent transition-colors"
                        >
                          <ExternalLink size={14} />
                        </a>
                      )}
                      <button
                        onClick={() => deleteMutation.mutate(app.id)}
                        className="text-slate-400 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {applyModalApp && (
        <ApplyModal
          application={applyModalApp}
          onClose={() => setApplyModalApp(null)}
        />
      )}
    </div>
  )
}