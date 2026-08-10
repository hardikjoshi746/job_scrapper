import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Zap } from 'lucide-react'
import client from '../api/client'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'

export default function Register() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password.length < 6) return toast.error('Password must be at least 6 characters')
    setLoading(true)
    try {
      const res = await client.post('/auth/register', form)
      login(res.data)
      navigate('/jobs')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#030712] px-4">
      <div className="w-full max-w-sm animate-fade-up">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-accent/20 border border-accent/30 mb-4">
            <Zap size={24} className="text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-white">
            Job<span className="text-accent">Hunt</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">Create your account</p>
        </div>

        <form onSubmit={handleSubmit} className="glass p-6 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-slate-400 font-medium">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="Your name"
              className="rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 outline-none border border-white/10 focus:border-accent/50 transition-colors"
              style={{ background: 'rgba(255,255,255,0.05)' }}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-slate-400 font-medium">Email</label>
            <input
              type="email"
              value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              placeholder="you@example.com"
              required
              className="rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 outline-none border border-white/10 focus:border-accent/50 transition-colors"
              style={{ background: 'rgba(255,255,255,0.05)' }}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-slate-400 font-medium">Password</label>
            <input
              type="password"
              value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              placeholder="Min. 6 characters"
              required
              className="rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 outline-none border border-white/10 focus:border-accent/50 transition-colors"
              style={{ background: 'rgba(255,255,255,0.05)' }}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary py-2.5 mt-1 disabled:opacity-50"
          >
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p className="text-center text-sm text-slate-500 mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-accent hover:text-accent/80 transition-colors">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
