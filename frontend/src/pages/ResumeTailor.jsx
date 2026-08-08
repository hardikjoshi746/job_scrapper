import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Upload, FileText, Sparkles, Download } from 'lucide-react'
import client from '../api/client'
import toast from 'react-hot-toast'

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
  const [selectedAppId, setSelectedAppId] = useState('')
  const [downloadUrl, setDownloadUrl] = useState(null)

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

  const tailorMutation = useMutation({
    mutationFn: async ({ appId, resumeId }) => {
      const res = await client.post('/resume/tailor', null, {
        params: { application_id: appId, resume_id: resumeId },
      })
      return res.data
    },
    onSuccess: (data) => {
      toast.success('Resume tailored!')
      setDownloadUrl(data.download_url)
    },
    onError: () => toast.error('Tailoring failed'),
  })

  const handleUpload = () => {
    if (!selectedFile) return toast.error('Select a file first')
    uploadMutation.mutate(selectedFile)
  }

  const handleTailor = () => {
    if (!selectedAppId) return toast.error('Select a job application')
    if (!activeResume) return toast.error('Upload a resume first')
    tailorMutation.mutate({ appId: selectedAppId, resumeId: activeResume.id })
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
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
              <p className="text-slate-400 text-xs">Active resume · Uploaded {new Date(activeResume.created_at).toLocaleDateString()}</p>
            </div>
          </div>
        )}

        <div className="flex gap-3">
          <label className="flex-1 flex items-center gap-3 bg-white/5 border border-white/10 border-dashed rounded-lg px-4 py-3 cursor-pointer hover:border-accent/40 transition-all">
            <Upload size={15} className="text-slate-400 shrink-0" />
            <span className="text-sm text-slate-400 truncate">
              {selectedFile ? selectedFile.name : 'Choose PDF or DOCX'}
            </span>
            <input
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={e => setSelectedFile(e.target.files[0])}
            />
          </label>
          <button
            onClick={handleUpload}
            disabled={!selectedFile || uploadMutation.isPending}
            className="btn-primary px-5 disabled:opacity-40 shrink-0"
          >
            {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      </div>

      {/* Tailor Section */}
      <div className="glass p-6 mb-6">
        <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
          <Sparkles size={16} className="text-accent" />
          Tailor for a Job
        </h2>

        <div className="mb-4">
          <label className="text-xs text-slate-400 mb-2 block">Select Application</label>
          <select
            value={selectedAppId}
            onChange={e => setSelectedAppId(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white outline-none focus:border-accent/40 transition-all"
            style={{background: 'rgba(255,255,255,0.05)'}}
          >
            <option value="" style={{background: '#0f0f1a'}}>Choose a job...</option>
            {applications.map(app => (
              <option key={app.id} value={app.id} style={{background: '#0f0f1a'}}>
                {app.job_title} @ {app.company}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleTailor}
          disabled={!selectedAppId || !activeResume || tailorMutation.isPending}
          className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-40"
        >
          <Sparkles size={15} />
          {tailorMutation.isPending ? 'Tailoring with Claude AI...' : 'Tailor Resume'}
        </button>
      </div>

      {/* Download Section */}
      {downloadUrl && (
        <div className="glass p-6 border border-accent/20">
          <h2 className="text-white font-semibold mb-3 flex items-center gap-2">
            <Download size={16} className="text-accent" />
            Tailored Resume Ready
          </h2>
          <a
            href={downloadUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary flex items-center justify-center gap-2 w-full"
          >
            <Download size={15} />
            Download PDF
          </a>
        </div>
      )}
    </div>
  )
}