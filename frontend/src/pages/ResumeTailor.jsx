import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Upload, FileText, Sparkles, ClipboardList, Settings } from 'lucide-react'
import client, { baseURL } from '../api/client'
import toast from 'react-hot-toast'
import ATSResult from '../components/ATSResult'
import TailorProgress from '../components/TailorProgress'

async function fetchApplications() {
  const res = await client.get('/applications')
  return res.data
}

async function fetchActiveResume() {
  const res = await client.get('/resume/active')
  return res.data
}

export default function ResumeTailor() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [jdMode, setJdMode] = useState('application') // 'application' | 'paste'
  const [selectedAppId, setSelectedAppId] = useState('')
  const [pastedJD, setPastedJD] = useState('')
  const [customInstructions, setCustomInstructions] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [tailoring, setTailoring] = useState(false)
  const [progress, setProgress] = useState(null)
  const [tailorResult, setTailorResult] = useState(null)

  const { data: applications = [] } = useQuery({
    queryKey: ['applications'],
    queryFn: fetchApplications,
  })

  const { data: activeResume, refetch: refetchResume } = useQuery({
    queryKey: ['activeResume'],
    queryFn: fetchActiveResume,
    retry: false,
  })

  const uploadMutation = useMutation({
    mutationFn: async (file) => {
      const formData = new FormData()
      formData.append('file', file)
      const res = await client.post('/resume/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return res.data
    },
    onSuccess: (data) => {
      toast.success(`Uploaded ${data.filename}`)
      refetchResume()
      setSelectedFile(null)
    },
    onError: () => toast.error('Upload failed'),
  })

  const handleTailor = async () => {
    if (!activeResume) return toast.error('Upload a resume first')
    if (jdMode === 'application' && !selectedAppId) return toast.error('Select a job application')
    if (jdMode === 'paste' && !pastedJD.trim()) return toast.error('Paste a job description')

    setTailoring(true)
    setProgress({ step: 'generating', iteration: 1, total: 3 })
    setTailorResult(null)

    try {
      const params = new URLSearchParams({ resume_id: activeResume.id })
      if (jdMode === 'application' && selectedAppId) params.set('application_id', selectedAppId)
      if (jdMode === 'paste' && pastedJD.trim()) params.set('job_description', pastedJD.trim())
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
        <h1 className="text-3xl font-bold text-white mb-1">Resume Tailor</h1>
        <p className="text-slate-400 text-sm">AI tailors your resume to match each job's keywords</p>
      </div>

      {/* Upload Section */}
      <div className="glass p-6 mb-6">
        <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
          <Upload size={16} className="text-accent" />
          Base Resume
        </h2>
        {activeResume && (
          <div className="flex items-center gap-3 bg-accent/10 border border-accent/20 rounded-lg px-4 py-3 mb-4">
            <FileText size={16} className="text-accent" />
            <div>
              <p className="text-white text-sm font-medium">{activeResume.filename}</p>
              <p className="text-slate-400 text-xs">Active · Uploaded {new Date(activeResume.created_at).toLocaleDateString()}</p>
            </div>
          </div>
        )}
        <div className="flex gap-3">
          <label className="flex-1 flex items-center gap-3 bg-white/5 border border-white/10 border-dashed rounded-lg px-4 py-3 cursor-pointer hover:border-accent/40 transition-all">
            <Upload size={15} className="text-slate-400 shrink-0" />
            <span className="text-sm text-slate-400 truncate">
              {selectedFile ? selectedFile.name : 'Choose PDF or DOCX'}
            </span>
            <input type="file" accept=".pdf,.docx" className="hidden" onChange={e => setSelectedFile(e.target.files[0])} />
          </label>
          <button
            onClick={() => { if (!selectedFile) return toast.error('Select a file first'); uploadMutation.mutate(selectedFile) }}
            disabled={!selectedFile || uploadMutation.isPending}
            className="btn-primary px-5 disabled:opacity-40 shrink-0"
          >
            {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      </div>

      {/* Job Description Section */}
      <div className="glass p-6 mb-6">
        <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
          <ClipboardList size={16} className="text-accent" />
          Job Description
        </h2>

        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setJdMode('application')}
            className={`px-4 py-1.5 rounded-full text-xs font-medium border transition-all ${
              jdMode === 'application'
                ? 'bg-accent/20 text-accent border-accent/30'
                : 'bg-white/5 text-slate-400 border-white/10 hover:border-white/20'
            }`}
          >
            From Saved Application
          </button>
          <button
            onClick={() => setJdMode('paste')}
            className={`px-4 py-1.5 rounded-full text-xs font-medium border transition-all ${
              jdMode === 'paste'
                ? 'bg-accent/20 text-accent border-accent/30'
                : 'bg-white/5 text-slate-400 border-white/10 hover:border-white/20'
            }`}
          >
            Paste JD
          </button>
        </div>

        {jdMode === 'application' ? (
          <select
            value={selectedAppId}
            onChange={e => setSelectedAppId(e.target.value)}
            className="w-full border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white outline-none focus:border-accent/40 transition-all"
            style={{ background: 'rgba(255,255,255,0.05)' }}
          >
            <option value="" style={{ background: '#0f0f1a' }}>Choose a saved job...</option>
            {applications.map(app => (
              <option key={app.id} value={app.id} style={{ background: '#0f0f1a' }}>
                {app.job_title} @ {app.company}
              </option>
            ))}
          </select>
        ) : (
          <textarea
            value={pastedJD}
            onChange={e => setPastedJD(e.target.value)}
            placeholder="Paste the full job description here..."
            rows={8}
            className="w-full border border-white/10 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-500 outline-none focus:border-accent/40 transition-all resize-none"
            style={{ background: 'rgba(255,255,255,0.05)' }}
          />
        )}
      </div>

      {/* Advanced Options */}
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
              Tell Claude what to include, exclude, or emphasize. e.g. "Skip certifications section", "Emphasize Python", "Add AWS to skills"
            </p>
            <textarea
              value={customInstructions}
              onChange={e => setCustomInstructions(e.target.value)}
              placeholder="e.g. Skip the certifications section. Emphasize leadership experience. Include cloud skills."
              rows={4}
              className="w-full border border-white/10 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-500 outline-none focus:border-accent/40 transition-all resize-none"
              style={{ background: 'rgba(255,255,255,0.05)' }}
            />
          </div>
        )}
      </div>

      {/* Tailor Button */}
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
