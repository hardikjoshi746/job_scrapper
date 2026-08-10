import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileText, Sparkles, Settings, ClipboardList } from 'lucide-react'
import client, { baseURL } from '../api/client'
import toast from 'react-hot-toast'
import ATSResult from '../components/ATSResult'
import TailorProgress from '../components/TailorProgress'

async function fetchActiveResume() {
  const res = await client.get('/resume/active')
  return res.data
}

export default function CustomJob() {
  const [jobTitle, setJobTitle] = useState('')
  const [company, setCompany] = useState('')
  const [jd, setJd] = useState('')
  const [customInstructions, setCustomInstructions] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [tailoring, setTailoring] = useState(false)
  const [progress, setProgress] = useState(null)
  const [tailorResult, setTailorResult] = useState(null)

  const { data: activeResume } = useQuery({
    queryKey: ['activeResume'],
    queryFn: fetchActiveResume,
    retry: false,
  })

  const handleTailor = async () => {
    if (!activeResume) return toast.error('Upload a resume first on the Resume page')
    if (!jd.trim()) return toast.error('Paste a job description')

    setTailoring(true)
    setProgress({ step: 'generating', iteration: 1, total: 3 })
    setTailorResult(null)

    try {
      // Save as application first so the PDF is linked
      const appRes = await client.post('/applications', {
        job_title: jobTitle.trim() || 'Custom Job',
        company: company.trim() || 'Unknown',
        job_description: jd.trim(),
        status: 'saved',
      })
      const appId = appRes.data.id

      const params = new URLSearchParams({
        resume_id: activeResume.id,
        application_id: appId,
        job_description: jd.trim(),
      })
      if (customInstructions.trim()) params.set('custom_instructions', customInstructions.trim())

      const token = localStorage.getItem('auth_token')
      const response = await fetch(`${baseURL}/resume/tailor/stream?${params}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || 'Tailoring failed')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = JSON.parse(line.slice(6))
          if (data.step === 'done') {
            setTailorResult(data)
            toast.success('Resume tailored!')
          } else if (data.step === 'error') {
            throw new Error(data.message)
          } else {
            setProgress(data)
          }
        }
      }
    } catch (err) {
      toast.error(err.message || 'Tailoring failed')
    } finally {
      setTailoring(false)
      setProgress(null)
    }
  }

  const handleDownload = async () => {
    try {
      const path = tailorResult.download_url.replace('/api', '')
      const res = await client.get(path)
      const a = document.createElement('a')
      a.href = res.data.url
      a.download = 'tailored_resume.pdf'
      a.click()
    } catch {
      toast.error('Download failed')
    }
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-1">Custom Job</h1>
        <p className="text-slate-400 text-sm">Paste any job description and get a tailored resume instantly</p>
      </div>

      {/* Active resume indicator */}
      <div className="glass p-4 mb-6 flex items-center gap-3">
        <FileText size={16} className="text-accent shrink-0" />
        {activeResume ? (
          <div>
            <p className="text-white text-sm font-medium">{activeResume.filename}</p>
            <p className="text-slate-400 text-xs">Active resume · will be tailored</p>
          </div>
        ) : (
          <p className="text-slate-400 text-sm">
            No active resume — <a href="/resume" className="text-accent hover:underline">upload one first</a>
          </p>
        )}
      </div>

      {/* Job details */}
      <div className="glass p-6 mb-6">
        <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
          <ClipboardList size={16} className="text-accent" />
          Job Details
        </h2>
        <div className="flex gap-3 mb-4">
          <input
            value={jobTitle}
            onChange={e => setJobTitle(e.target.value)}
            placeholder="Job title (optional)"
            className="flex-1 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 outline-none focus:border-accent/40 transition-all"
            style={{ background: 'rgba(255,255,255,0.05)' }}
          />
          <input
            value={company}
            onChange={e => setCompany(e.target.value)}
            placeholder="Company (optional)"
            className="flex-1 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 outline-none focus:border-accent/40 transition-all"
            style={{ background: 'rgba(255,255,255,0.05)' }}
          />
        </div>
        <textarea
          value={jd}
          onChange={e => setJd(e.target.value)}
          placeholder="Paste the full job description here..."
          rows={10}
          className="w-full border border-white/10 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-500 outline-none focus:border-accent/40 transition-all resize-none"
          style={{ background: 'rgba(255,255,255,0.05)' }}
        />
      </div>

      {/* Custom instructions */}
      <div className="glass p-6 mb-6">
        <button
          onClick={() => setShowAdvanced(s => !s)}
          className="flex items-center gap-2 text-sm font-medium text-slate-400 hover:text-white transition-colors w-full"
        >
          <Settings size={15} />
          Custom Instructions
          <span className="ml-auto text-xs">{showAdvanced ? '▲' : '▼'}</span>
        </button>
        {showAdvanced && (
          <div className="mt-4">
            <p className="text-xs text-slate-500 mb-2">
              Tell Claude what to include, exclude, or emphasize. e.g. "Skip certifications", "Emphasize Python", "Add AWS to skills"
            </p>
            <textarea
              value={customInstructions}
              onChange={e => setCustomInstructions(e.target.value)}
              placeholder="e.g. Skip the certifications section. Emphasize leadership experience."
              rows={4}
              className="w-full border border-white/10 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-500 outline-none focus:border-accent/40 transition-all resize-none"
              style={{ background: 'rgba(255,255,255,0.05)' }}
            />
          </div>
        )}
      </div>

      {/* Tailor button */}
      <button
        onClick={handleTailor}
        disabled={!activeResume || tailoring}
        className="btn-primary w-full flex items-center justify-center gap-2 py-3 mb-6 disabled:opacity-40"
      >
        <Sparkles size={15} />
        {tailoring ? 'Working...' : 'Tailor Resume'}
      </button>

      {/* Progress */}
      {tailoring && progress && <TailorProgress progress={progress} />}

      {/* ATS Result */}
      {!tailoring && tailorResult && (
        <ATSResult
          atsScore={tailorResult.ats_score}
          matchedKeywords={tailorResult.matched_keywords}
          missingKeywords={tailorResult.missing_keywords}
          iterations={tailorResult.iterations}
          onDownload={handleDownload}
        />
      )}
    </div>
  )
}
