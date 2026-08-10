import { useState } from 'react'
import { Sparkles, ExternalLink, X, Download, Settings } from 'lucide-react'
import client from '../api/client'
import toast from 'react-hot-toast'

export default function ApplyModal({ job, onClose }) {
  const [step, setStep] = useState('confirm') // confirm | tailoring | done
  const [tailorResult, setTailorResult] = useState(null)
  const [customInstructions, setCustomInstructions] = useState('')
  const [showInstructions, setShowInstructions] = useState(false)

  const handleTailorAndApply = async () => {
    setStep('tailoring')
    try {
      // 1. save the job as an application
      const appRes = await client.post('/applications', {
        job_title: job.title,
        company: job.company?.display_name,
        location: job.location?.display_name,
        job_url: job.redirect_url,
        job_description: job.description?.replace(/<[^>]*>/g, ''),
        status: 'saved',
      })
      const appId = appRes.data.id

      // 2. get active resume
      const resumeRes = await client.get('/resume/active')
      const resumeId = resumeRes.data.id

      // 3. tailor resume
      const params = { application_id: appId, resume_id: resumeId }
      if (customInstructions.trim()) params.custom_instructions = customInstructions.trim()
      const tailorRes = await client.post('/resume/tailor', null, { params })

      setTailorResult(tailorRes.data)
      setStep('done')
      toast.success('Resume tailored!')
    } catch (err) {
      const msg = err.response?.data?.detail || 'Something went wrong'
      toast.error(msg)
      setStep('confirm')
    }
  }

  const handleJustApply = () => {
    window.open(job.redirect_url, '_blank')
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div
        className="glass w-full max-w-md p-6 animate-fade-up"
        style={{ border: '1px solid rgba(167,139,250,0.2)' }}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-5">
          <div>
            <h2 className="text-white font-semibold text-lg">{job.title}</h2>
            <p className="text-slate-400 text-sm">{job.company?.display_name}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Confirm step */}
        {step === 'confirm' && (
          <>
            <p className="text-slate-300 text-sm mb-4">
              Would you like Claude to tailor your resume for this job before applying?
              It rewrites your resume to match the job's keywords for a better ATS score.
            </p>

            {/* Custom instructions toggle */}
            <button
              onClick={() => setShowInstructions(s => !s)}
              className="flex items-center gap-2 text-xs text-slate-400 hover:text-white transition-colors mb-2"
            >
              <Settings size={13} />
              Custom instructions (optional)
              <span className="ml-auto">{showInstructions ? '▲' : '▼'}</span>
            </button>
            {showInstructions && (
              <textarea
                value={customInstructions}
                onChange={e => setCustomInstructions(e.target.value)}
                placeholder="e.g. Skip certifications. Emphasize Python. Include AWS skills."
                rows={3}
                className="w-full border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 outline-none focus:border-accent/40 transition-all resize-none mb-3"
                style={{ background: 'rgba(255,255,255,0.05)' }}
              />
            )}

            <div className="flex flex-col gap-3 mt-2">
              <button
                onClick={handleTailorAndApply}
                className="btn-primary flex items-center justify-center gap-2 py-3"
              >
                <Sparkles size={15} />
                Yes, tailor my resume
              </button>
              <button
                onClick={handleJustApply}
                className="btn-ghost flex items-center justify-center gap-2 py-3"
              >
                <ExternalLink size={15} />
                No, take me to the job
              </button>
              <button
                onClick={onClose}
                className="text-slate-500 text-sm hover:text-slate-300 transition-colors text-center py-1"
              >
                Cancel
              </button>
            </div>
          </>
        )}

        {/* Tailoring step */}
        {step === 'tailoring' && (
          <div className="text-center py-6">
            <div className="w-10 h-10 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-white font-medium mb-1">Tailoring your resume...</p>
            <p className="text-slate-400 text-sm">Claude is matching your resume to the job</p>
          </div>
        )}

        {/* Done step */}
        {step === 'done' && tailorResult && (
          <div className="flex flex-col gap-3">
            {/* ATS score badge */}
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-center">
              <p className="text-green-300 text-sm font-medium mb-0.5">Resume tailored successfully!</p>
              <p className="text-white text-lg font-bold">
                ATS Score: <span className={
                  tailorResult.ats_score >= 90 ? 'text-green-400' :
                  tailorResult.ats_score >= 75 ? 'text-yellow-400' : 'text-red-400'
                }>{tailorResult.ats_score}%</span>
              </p>
              {tailorResult.iterations > 1 && (
                <p className="text-slate-500 text-xs mt-0.5">Refined in {tailorResult.iterations} iterations</p>
              )}
            </div>

            {/* Matched keywords */}
            {tailorResult.matched_keywords?.length > 0 && (
              <div>
                <p className="text-xs text-slate-400 mb-1.5">Keywords matched:</p>
                <div className="flex flex-wrap gap-1.5">
                  {tailorResult.matched_keywords.slice(0, 10).map((kw, i) => (
                    <span key={i} className="px-2 py-0.5 rounded-full text-[11px] bg-green-500/10 text-green-300 border border-green-500/20">{kw}</span>
                  ))}
                  {tailorResult.matched_keywords.length > 10 && (
                    <span className="text-[11px] text-slate-500">+{tailorResult.matched_keywords.length - 10} more</span>
                  )}
                </div>
              </div>
            )}

            <button
              onClick={async () => {
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
              }}
              className="btn-primary flex items-center justify-center gap-2 py-3"
            >
              <Download size={15} />
              Download Tailored Resume
            </button>
            <a
              href={job.redirect_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-ghost flex items-center justify-center gap-2 py-3"
              onClick={onClose}
            >
              <ExternalLink size={15} />
              Go to Job Page
            </a>
          </div>
        )}
      </div>
    </div>
  )
}