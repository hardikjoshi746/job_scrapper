import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Globe,
  Search,
  MapPin,
  Building2,
  BookmarkPlus,
  ExternalLink,
  AlertTriangle,
  Clock,
  Wifi,
  Tag,
} from 'lucide-react'
import client from '../api/client'
import toast from 'react-hot-toast'

// ---------------------------------------------------------------------------
// Source metadata
// ---------------------------------------------------------------------------

const SOURCE_META = {
  google_jobs:    { label: 'Google Jobs',     color: 'text-red-400',    bg: 'bg-red-400/10 border-red-400/30' },
  linkedin:       { label: 'LinkedIn',        color: 'text-sky-400',    bg: 'bg-sky-400/10 border-sky-400/30' },
  adzuna:         { label: 'Adzuna',          color: 'text-blue-400',   bg: 'bg-blue-400/10 border-blue-400/30' },
  remoteok:       { label: 'RemoteOK',        color: 'text-green-400',  bg: 'bg-green-400/10 border-green-400/30' },
  arbeitnow:      { label: 'Arbeitnow',       color: 'text-orange-400', bg: 'bg-orange-400/10 border-orange-400/30' },
  weworkremotely: { label: 'We Work Remotely',color: 'text-violet-400', bg: 'bg-violet-400/10 border-violet-400/30' },
  indeed_rss:     { label: 'Indeed',          color: 'text-yellow-400', bg: 'bg-yellow-400/10 border-yellow-400/30' },
}

const ALL_SOURCES = Object.keys(SOURCE_META)

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function runScrape(keyword, location, sources, experienceLevel, datePosted) {
  const res = await client.post('/scraper/search', {
    keyword,
    location,
    sources: sources.length > 0 ? sources : null,
    experience_level: experienceLevel || null,
    date_posted: datePosted || null,
  })
  return res.data
}

async function saveJob(job) {
  const res = await client.post('/scraper/save', {
    job_url: job.job_url,
    title: job.title,
    company: job.company,
    location: job.location,
    job_description: job.description,
  })
  return res.data
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SourceBadge({ source }) {
  const meta = SOURCE_META[source] || { label: source, color: 'text-slate-400', bg: 'bg-slate-400/10 border-slate-400/30' }
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium ${meta.color} ${meta.bg}`}>
      {meta.label}
    </span>
  )
}

function SourcePill({ source, active, onToggle }) {
  const meta = SOURCE_META[source]
  return (
    <button
      onClick={() => onToggle(source)}
      className={`text-xs px-3 py-1.5 rounded-lg border transition-all font-medium ${
        active
          ? `${meta.color} ${meta.bg}`
          : 'text-slate-500 bg-white/5 border-white/10 hover:border-white/20'
      }`}
    >
      {meta.label}
    </button>
  )
}

function SourceSummary({ sources, errors }) {
  return (
    <div className="flex flex-wrap gap-3 text-xs">
      {Object.entries(sources).map(([src, count]) => {
        const meta = SOURCE_META[src] || { label: src, color: 'text-slate-400' }
        const hasError = !!errors[src]
        return (
          <span key={src} className={`flex items-center gap-1 ${hasError ? 'text-slate-500 line-through' : meta.color}`}>
            {hasError ? <AlertTriangle size={11} /> : null}
            {meta.label}: {hasError ? 'failed' : count}
          </span>
        )
      })}
    </div>
  )
}

function JobCard({ job, isSaved, onSave }) {
  const posted = job._date_posted || (job.posted_at ? new Date(job.posted_at).toLocaleDateString() : null)
  const salaryText = job._salary_text || (
    (job.salary_min || job.salary_max)
      ? `${job.currency || '$'}${job.salary_min?.toLocaleString()}${job.salary_max ? ` – ${job.salary_max?.toLocaleString()}` : '+'}`
      : null
  )
  const tags = (job.tags || []).slice(0, 5)
  const desc = (job.description || '').slice(0, 160)

  return (
    <div className="glass glass-hover p-4 flex flex-col gap-3">
      {/* Top row */}
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h3 className="text-white font-semibold text-sm">{job.title}</h3>
            {job.is_remote && (
              <span className="flex items-center gap-0.5 text-xs text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 px-1.5 py-0.5 rounded-full">
                <Wifi size={9} /> Remote
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mb-1">
            {job.company && (
              <span className="flex items-center gap-1"><Building2 size={11} />{job.company}</span>
            )}
            {job.location && (
              <span className="flex items-center gap-1"><MapPin size={11} />{job.location}</span>
            )}
            {posted && (
              <span className="flex items-center gap-1"><Clock size={11} />{posted}</span>
            )}
            {salaryText && (
              <span className="text-accent font-medium">{salaryText}</span>
            )}
            {job._via && (
              <span className="text-slate-500">{job._via}</span>
            )}
          </div>
          <SourceBadge source={job.source} />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => onSave(job)}
            disabled={isSaved}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-all ${
              isSaved
                ? 'text-accent border-accent/30 bg-accent/10 cursor-default'
                : 'btn-ghost'
            }`}
          >
            <BookmarkPlus size={13} />
            {isSaved ? 'Saved' : 'Save'}
          </button>
          <a
            href={job.job_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary flex items-center gap-1.5 text-xs px-3 py-1.5"
          >
            <ExternalLink size={13} />
            View
          </a>
        </div>
      </div>

      {/* Description */}
      {desc && (
        <p className="text-slate-500 text-xs leading-relaxed line-clamp-2">{desc}…</p>
      )}

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.map((tag, i) => (
            <span key={i} className="flex items-center gap-1 text-xs text-slate-500 bg-white/5 border border-white/10 px-2 py-0.5 rounded-full">
              <Tag size={9} />{tag}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function JobScraper() {
  const [keyword, setKeyword] = useState('')
  const [location, setLocation] = useState('remote')
  const [activeSources, setActiveSources] = useState([]) // empty = all
  const [experienceLevel, setExperienceLevel] = useState('')  // '' = any
  const [datePosted, setDatePosted] = useState('')            // '' = any
  const [submitted, setSubmitted] = useState(false)
  const [savedUrls, setSavedUrls] = useState(new Set())

  const queryClient = useQueryClient()

  const { data, isFetching, error, refetch } = useQuery({
    queryKey: ['scraped-jobs', keyword, location, activeSources, experienceLevel, datePosted],
    queryFn: () => runScrape(keyword, location, activeSources, experienceLevel, datePosted),
    enabled: submitted,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const saveMutation = useMutation({
    mutationFn: saveJob,
    onSuccess: (_, job) => {
      setSavedUrls(prev => new Set([...prev, job.job_url]))
      toast.success(`Saved "${job.title}"`)
      queryClient.invalidateQueries(['applications'])
    },
    onError: (err, job) => {
      if (err.response?.status === 409) {
        setSavedUrls(prev => new Set([...prev, job.job_url]))
        toast('Already in your tracker', { icon: 'ℹ️' })
      } else {
        toast.error(err.response?.data?.detail || 'Failed to save job')
      }
    },
  })

  const handleSearch = (e) => {
    e.preventDefault()
    if (!keyword.trim()) return toast.error('Enter a job keyword')
    if (keyword.trim().length > 100) return toast.error('Keyword is too long (max 100 chars)')
    setSubmitted(true)
    refetch()
  }

  const toggleSource = (src) => {
    setActiveSources(prev =>
      prev.includes(src) ? prev.filter(s => s !== src) : [...prev, src]
    )
  }

  const isRateLimited = error?.response?.status === 429
  const hasPartialErrors = data?.errors && Object.keys(data.errors).length > 0

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <Globe size={28} className="text-accent" />
          <h1 className="text-3xl font-bold text-white">Job Scraper</h1>
        </div>
        <p className="text-slate-400 text-sm">
          Search Google Jobs + Adzuna, RemoteOK, Arbeitnow, We Work Remotely, and Indeed in one click.
        </p>
      </div>

      {/* Search form */}
      <form onSubmit={handleSearch} className="glass p-4 mb-4 flex flex-col gap-3">
        <div className="flex gap-3">
          <div className="flex-1 flex items-center gap-2 rounded-lg px-4 py-2.5" style={{ background: 'rgba(255,255,255,0.05)' }}>
            <Search size={16} className="text-slate-400 shrink-0" />
            <input
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
              placeholder="Job title, role, or keyword"
              maxLength={100}
              className="text-white placeholder-slate-500 text-sm outline-none w-full bg-transparent"
            />
          </div>
          <div className="flex-1 flex items-center gap-2 rounded-lg px-4 py-2.5" style={{ background: 'rgba(255,255,255,0.05)' }}>
            <MapPin size={16} className="text-slate-400 shrink-0" />
            <input
              value={location}
              onChange={e => setLocation(e.target.value)}
              placeholder="Location (e.g. Remote, New York)"
              maxLength={100}
              className="text-white placeholder-slate-500 text-sm outline-none w-full bg-transparent"
            />
          </div>
          <button
            type="submit"
            disabled={isFetching}
            className="btn-primary px-6 flex items-center gap-2 shrink-0 disabled:opacity-50"
          >
            <Globe size={16} />
            {isFetching ? 'Scraping…' : 'Scrape'}
          </button>
        </div>

        {/* Filters row */}
        <div className="flex flex-wrap gap-4 pt-2 border-t border-white/5">
          {/* Experience Level */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-500 shrink-0">Level:</span>
            {[
              { value: '', label: 'Any' },
              { value: 'entry', label: 'Entry Level' },
              { value: 'associate', label: 'Associate' },
              { value: 'mid', label: 'Mid-Level' },
              { value: 'senior', label: 'Senior' },
              { value: 'lead', label: 'Lead' },
            ].map(opt => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setExperienceLevel(opt.value)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition-all font-medium ${
                  experienceLevel === opt.value
                    ? 'text-accent bg-accent/10 border-accent/30'
                    : 'text-slate-500 bg-white/5 border-white/10 hover:border-white/20'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Date Posted */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-500 shrink-0">Posted:</span>
            {[
              { value: '', label: 'Any time' },
              { value: 'day', label: 'Past 24h' },
              { value: 'week', label: 'Past week' },
              { value: 'month', label: 'Past month' },
            ].map(opt => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setDatePosted(opt.value)}
                className={`text-xs px-3 py-1.5 rounded-lg border transition-all font-medium ${
                  datePosted === opt.value
                    ? 'text-accent bg-accent/10 border-accent/30'
                    : 'text-slate-500 bg-white/5 border-white/10 hover:border-white/20'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Source filters */}
        <div className="flex items-center gap-2 flex-wrap pt-1 border-t border-white/5">
          <span className="text-xs text-slate-500 mr-1">Sources:</span>
          <button
            type="button"
            onClick={() => setActiveSources([])}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-all font-medium ${
              activeSources.length === 0
                ? 'text-accent bg-accent/10 border-accent/30'
                : 'text-slate-500 bg-white/5 border-white/10 hover:border-white/20'
            }`}
          >
            All
          </button>
          {ALL_SOURCES.map(src => (
            <SourcePill
              key={src}
              source={src}
              active={activeSources.includes(src)}
              onToggle={toggleSource}
            />
          ))}
        </div>
      </form>

      {/* Rate limit error */}
      {isRateLimited && (
        <div className="glass border border-red-500/30 rounded-lg p-4 mb-6 flex items-center gap-3 text-red-400">
          <AlertTriangle size={18} className="shrink-0" />
          <div>
            <p className="text-sm font-medium">Search limit reached</p>
            <p className="text-xs text-red-400/70 mt-0.5">You've used 10 searches this hour. Try again later.</p>
          </div>
        </div>
      )}

      {/* Generic error */}
      {error && !isRateLimited && (
        <div className="glass border border-red-500/30 rounded-lg p-4 mb-6 text-red-400 text-sm">
          {error.response?.data?.detail || 'Something went wrong. Please try again.'}
        </div>
      )}

      {/* Loading */}
      {isFetching && (
        <div className="text-center py-16">
          <Globe size={36} className="text-accent/40 mx-auto mb-4 animate-pulse" />
          <p className="text-slate-400 text-sm">Scraping {activeSources.length > 0 ? activeSources.length : 5} sources…</p>
          <p className="text-slate-600 text-xs mt-1">This may take up to 15 seconds</p>
        </div>
      )}

      {/* Results */}
      {!isFetching && data && (
        <>
          {/* Summary bar */}
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div className="flex flex-col gap-1">
              <p className="text-slate-400 text-sm">
                <span className="text-white font-semibold">{data.total}</span> jobs found
              </p>
              <SourceSummary sources={data.sources} errors={data.errors} />
            </div>
          </div>

          {/* Partial errors banner */}
          {hasPartialErrors && (
            <div className="glass border border-yellow-500/20 rounded-lg p-3 mb-4 flex items-start gap-2 text-yellow-400/80">
              <AlertTriangle size={15} className="mt-0.5 shrink-0" />
              <div className="text-xs">
                <span className="font-medium">Some sources failed: </span>
                {Object.entries(data.errors).map(([src, msg]) => (
                  <span key={src} className="mr-3">
                    {SOURCE_META[src]?.label || src} — {msg.slice(0, 80)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Job list */}
          {data.results.length > 0 ? (
            <div className="flex flex-col gap-4 stagger">
              {data.results.map(job => (
                <JobCard
                  key={job.id}
                  job={job}
                  isSaved={savedUrls.has(job.job_url)}
                  onSave={() => saveMutation.mutate(job)}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-16 text-slate-400">
              No jobs found for <span className="text-white">"{keyword}"</span>. Try different keywords or sources.
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {!submitted && !isFetching && (
        <div className="text-center py-20">
          <Globe size={44} className="text-accent/30 mx-auto mb-4" />
          <p className="text-slate-500 text-sm">Enter a keyword to search Google Jobs + 5 other sources</p>
          <p className="text-slate-600 text-xs mt-2">Rate limited to 10 searches per hour</p>
        </div>
      )}
    </div>
  )
}