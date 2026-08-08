import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, MapPin, Building2, BookmarkPlus, Zap } from 'lucide-react'
import client from '../api/client'
import toast from 'react-hot-toast'
import ApplyModal from '../components/ApplyModal'

async function searchJobs(role, location, page) {
  const res = await client.get('/jobs/search', { params: { role, location, page } })
  return res.data
}

async function saveJob(job) {
  await client.post('/applications', {
    job_title: job.title,
    company: job.company.display_name,
    location: job.location.display_name,
    job_url: job.redirect_url,
    job_description: job.description,
    status: 'saved',
  })
}

export default function JobSearch() {
  const [role, setRole] = useState('')
  const [location, setLocation] = useState('')
  const [page, setPage] = useState(1)
  const [submitted, setSubmitted] = useState(false)
  const [sortRecent, setSortRecent] = useState(false)
  const [applyJob, setApplyJob] = useState(null)

  const { data, isFetching, refetch } = useQuery({
    queryKey: ['jobs', role, location, page],
    queryFn: () => searchJobs(role, location, page),
    enabled: submitted,
  })

  const handleSearch = (e) => {
    e.preventDefault()
    if (!role.trim()) return toast.error('Enter a job role')
    setPage(1)
    setSubmitted(true)
    refetch()
  }

  const handleSave = async (job) => {
    try {
      await saveJob(job)
      toast.success(`Saved ${job.title} at ${job.company.display_name}`)
    } catch {
      toast.error('Failed to save job')
    }
  }

  const jobs = sortRecent
    ? [...(data?.results || [])].sort((a, b) => new Date(b.created) - new Date(a.created))
    : (data?.results || [])

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-1">Find Jobs</h1>
        <p className="text-slate-400 text-sm">Search across thousands of listings</p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="glass p-4 mb-8 flex gap-3">
        <div className="flex-1 flex items-center gap-2 rounded-lg px-4 py-2.5" style={{background: 'rgba(255,255,255,0.05)'}}>
          <Search size={16} className="text-slate-400 shrink-0" />
          <input
            value={role}
            onChange={e => setRole(e.target.value)}
            placeholder="Job title, role, or keyword"
            className="text-white placeholder-slate-500 text-sm outline-none w-full"
            style={{background: 'transparent'}}
          />
        </div>
        <div className="flex-1 flex items-center gap-2 rounded-lg px-4 py-2.5" style={{background: 'rgba(255,255,255,0.05)'}}>
          <MapPin size={16} className="text-slate-400 shrink-0" />
          <input
            value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder="Location (e.g. New York, Remote)"
            className="text-white placeholder-slate-500 text-sm outline-none w-full"
            style={{background: 'transparent'}}
          />
        </div>
        <button type="submit" className="btn-primary px-6 flex items-center gap-2 shrink-0">
          <Search size={16} />
          Search
        </button>
      </form>

      {/* Results */}
      {isFetching && (
        <div className="text-center py-16 text-slate-400">Searching jobs...</div>
      )}

      {!isFetching && submitted && jobs.length === 0 && (
        <div className="text-center py-16 text-slate-400">No jobs found. Try different keywords.</div>
      )}

      {!isFetching && jobs.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-4">
            <p className="text-slate-500 text-sm">{data?.count?.toLocaleString()} results</p>
            <button
              onClick={() => setSortRecent(s => !s)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
                sortRecent
                  ? 'bg-accent/20 text-accent border-accent/30'
                  : 'bg-white/5 text-slate-400 border-white/10 hover:border-accent/30'
              }`}
            >
              Most Recent
            </button>
          </div>
          <div className="flex flex-col gap-4 stagger">
            {jobs.map((job, i) => (
              <div key={i} className="glass glass-hover p-4 flex items-center gap-4">
                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-white font-semibold text-sm truncate">{job.title}</h3>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-400 mb-2">
                    <span className="flex items-center gap-1"><Building2 size={11} />{job.company?.display_name}</span>
                    <span className="flex items-center gap-1"><MapPin size={11} />{job.location?.display_name}</span>
                    {job.created && <span>{new Date(job.created).toLocaleDateString()}</span>}
                    {job.salary_min && (
                      <span className="text-accent font-medium">
                        ${job.salary_min?.toLocaleString()} – ${job.salary_max?.toLocaleString()}
                      </span>
                    )}
                  </div>
                  <p className="text-slate-500 text-xs line-clamp-1">
                    {job.description?.replace(/<[^>]*>/g, '').slice(0, 120)}...
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleSave(job)}
                    className="btn-ghost flex items-center gap-1.5 text-xs px-3 py-1.5"
                  >
                    <BookmarkPlus size={13} />
                    Save
                  </button>
                  <button
                    onClick={() => setApplyJob(job)}
                    className="btn-primary flex items-center gap-1.5 text-xs px-3 py-1.5"
                  >
                    <Zap size={13} />
                    Apply
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex justify-center gap-3 mt-8">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn-ghost px-5 py-2 text-sm disabled:opacity-30"
            >
              Previous
            </button>
            <span className="flex items-center text-slate-400 text-sm">Page {page}</span>
            <button
              onClick={() => setPage(p => p + 1)}
              className="btn-ghost px-5 py-2 text-sm"
            >
              Next
            </button>
          </div>
        </>
      )}

      {/* Empty state */}
      {!submitted && (
        <div className="text-center py-20">
          <Zap size={40} className="text-accent/40 mx-auto mb-4" />
          <p className="text-slate-500">Search for jobs to get started</p>
        </div>
      )}

      {applyJob && (
        <ApplyModal job={applyJob} onClose={() => setApplyJob(null)} />
      )}
    </div>
  )
}