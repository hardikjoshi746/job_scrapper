import { useState } from 'react'
import { Sparkles, ExternalLink, X, Download } from 'lucide-react'
import client from '../api/client'
import toast from 'react-hot-toast'

export default function ApplyModal({ job, onClose }) {
  const [step, setStep] = useState('confirm') // confirm | tailoring | done
  const [downloadUrl, setDownloadUrl] = useState(null)

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
      const tailorRes = await client.post('/resume/tailor', null, {
        params: { application_id: appId, resume_id: resumeId },
      })

      setDownloadUrl(tailorRes.data.download_url)
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
            <p className="text-slate-300 text-sm mb-6">
              Would you like Claude to tailor your resume for this job before applying?
              It rewrites your resume to match the job's keywords for a better ATS score.
            </p>
            <div className="flex flex-col gap-3">
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
        {step === 'done' && (
          <div className="flex flex-col gap-3">
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg px-4 py-3 text-center mb-2">
              <p className="text-green-300 text-sm font-medium">Resume tailored successfully!</p>
            </div>
            <a
              href={downloadUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary flex items-center justify-center gap-2 py-3"
            >
              <Download size={15} />
              Download Tailored Resume
            </a>
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