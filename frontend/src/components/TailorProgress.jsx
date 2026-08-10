import { Sparkles, BarChart2, RefreshCw, CheckCircle } from 'lucide-react'

export default function TailorProgress({ progress }) {
  const { step, iteration = 1, total = 3, score, missing_keywords = [] } = progress

  const steps = [
    {
      key: 'generating',
      icon: Sparkles,
      label: `Generating resume${total > 1 ? ` (attempt ${iteration} of ${total})` : ''}`,
      status: getStatus(step, 'generating', iteration),
    },
    {
      key: 'evaluating',
      icon: BarChart2,
      label: 'Evaluating ATS score with GPT',
      status: getStatus(step, 'evaluating', iteration),
    },
    ...(step === 'refining' || iteration > 1
      ? [{
          key: 'refining',
          icon: RefreshCw,
          label: step === 'refining'
            ? `Score ${score}% — refining with missing keywords`
            : `Refining (iteration ${iteration})`,
          status: step === 'refining' ? 'active' : 'done',
          detail: step === 'refining' && missing_keywords.length > 0
            ? missing_keywords.slice(0, 6).join(', ')
            : null,
        }]
      : []),
  ]

  return (
    <div className="glass p-6 border border-accent/20" style={{ animation: 'fadeSlideUp 0.4s ease' }}>
      <p className="text-xs text-slate-500 uppercase tracking-wider mb-6">AI is working on your resume</p>

      <div className="flex flex-col gap-0">
        {steps.map((s, i) => (
          <StepRow key={`${s.key}-${iteration}`} {...s} isLast={i === steps.length - 1} index={i} />
        ))}
      </div>

      {/* Animated progress bar */}
      <div className="mt-6 h-1 rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full rounded-full bg-accent"
          style={{
            width: step === 'generating' ? '30%' : step === 'evaluating' ? '60%' : '85%',
            transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
            boxShadow: '0 0 8px rgba(139, 92, 246, 0.6)',
          }}
        />
      </div>

      <style>{`
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(12px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes stepIn {
          from { opacity: 0; transform: translateX(-8px); }
          to   { opacity: 1; transform: translateX(0); }
        }
        @keyframes pulse-ring {
          0%   { box-shadow: 0 0 0 0 rgba(139,92,246,0.4); }
          70%  { box-shadow: 0 0 0 7px rgba(139,92,246,0); }
          100% { box-shadow: 0 0 0 0 rgba(139,92,246,0); }
        }
        @keyframes bounce-dot {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.35; }
          40%            { transform: translateY(-5px); opacity: 1; }
        }
        @keyframes spin-smooth {
          to { transform: rotate(360deg); }
        }
        @keyframes checkPop {
          0%   { transform: scale(0); opacity: 0; }
          60%  { transform: scale(1.25); }
          100% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  )
}

function StepRow({ icon: Icon, label, status, detail, isLast, index }) {
  return (
    <div
      style={{ animation: `stepIn 0.35s ease ${index * 0.1}s both` }}
      className="flex gap-3"
    >
      {/* Timeline column */}
      <div className="flex flex-col items-center">
        {/* Icon circle */}
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all duration-500"
          style={
            status === 'active'
              ? { background: 'rgba(139,92,246,0.15)', border: '1px solid rgba(139,92,246,0.4)', animation: 'pulse-ring 1.5s ease-out infinite' }
              : status === 'done'
              ? { background: 'rgba(74,222,128,0.12)', border: '1px solid rgba(74,222,128,0.3)' }
              : { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }
          }
        >
          {status === 'active' ? (
            <div
              className="w-3.5 h-3.5 border-2 border-accent border-t-transparent rounded-full"
              style={{ animation: 'spin-smooth 0.7s linear infinite' }}
            />
          ) : status === 'done' ? (
            <CheckCircle size={14} className="text-green-400" style={{ animation: 'checkPop 0.3s ease' }} />
          ) : (
            <Icon size={13} className="text-slate-600" />
          )}
        </div>

        {/* Connector line */}
        {!isLast && (
          <div className="w-px flex-1 my-1" style={{
            background: status === 'done'
              ? 'linear-gradient(to bottom, rgba(74,222,128,0.3), rgba(255,255,255,0.06))'
              : 'rgba(255,255,255,0.06)',
            minHeight: '20px',
            transition: 'background 0.5s ease',
          }} />
        )}
      </div>

      {/* Content */}
      <div className="pb-5 min-w-0 flex-1">
        <p
          className="text-sm font-medium transition-colors duration-300 leading-tight pt-1.5"
          style={{
            color: status === 'active' ? '#fff' : status === 'done' ? '#64748b' : '#334155',
          }}
        >
          {label}
        </p>
        {detail && (
          <p
            className="text-xs mt-1 text-slate-500 truncate"
            style={{ animation: 'stepIn 0.3s ease' }}
          >
            Missing: {detail}
          </p>
        )}
      </div>
    </div>
  )
}

function getStatus(currentStep, thisStep, iteration) {
  if (currentStep === thisStep) return 'active'
  if (thisStep === 'generating' && (currentStep === 'evaluating' || currentStep === 'refining')) return 'done'
  if (thisStep === 'evaluating' && currentStep === 'refining') return 'done'
  if (thisStep === 'generating' && iteration > 1 && currentStep === 'generating') return 'done'
  return 'pending'
}
