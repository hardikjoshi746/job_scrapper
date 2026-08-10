import { Download, CheckCircle, AlertCircle } from 'lucide-react'

export default function ATSResult({ atsScore, matchedKeywords = [], missingKeywords = [], iterations, onDownload }) {
  const scoreColor =
    atsScore >= 90 ? 'text-green-400' :
    atsScore >= 75 ? 'text-yellow-400' :
    'text-red-400'

  const ringColor =
    atsScore >= 90 ? '#4ade80' :
    atsScore >= 75 ? '#facc15' :
    '#f87171'

  const circumference = 2 * Math.PI * 36
  const dashOffset = circumference - (atsScore / 100) * circumference

  return (
    <div className="glass p-6 border border-accent/20">
      {/* Score header */}
      <div className="flex items-center gap-5 mb-5">
        {/* Circular progress */}
        <div className="relative shrink-0">
          <svg width="88" height="88" viewBox="0 0 88 88">
            <circle cx="44" cy="44" r="36" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="7" />
            <circle
              cx="44" cy="44" r="36"
              fill="none"
              stroke={ringColor}
              strokeWidth="7"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              transform="rotate(-90 44 44)"
              style={{ transition: 'stroke-dashoffset 0.6s ease' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-xl font-bold ${scoreColor}`}>{atsScore}%</span>
            <span className="text-slate-500 text-[9px] uppercase tracking-wide">ATS</span>
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <h2 className="text-white font-semibold text-base mb-0.5">Resume Tailored</h2>
          <p className="text-slate-400 text-xs mb-1">
            {atsScore >= 95
              ? 'Excellent ATS match — ready to submit.'
              : atsScore >= 75
              ? 'Good match — should pass most ATS filters.'
              : 'Moderate match — consider improving keyword coverage.'}
          </p>
          {iterations > 1 && (
            <span className="text-xs text-slate-500">Refined over {iterations} iterations</span>
          )}
        </div>
      </div>

      {/* Download button */}
      <button
        onClick={onDownload}
        className="btn-primary flex items-center justify-center gap-2 w-full mb-5"
      >
        <Download size={15} />
        Download PDF
      </button>

      {/* Keywords */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {matchedKeywords.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <CheckCircle size={13} className="text-green-400 shrink-0" />
              <span className="text-xs font-medium text-green-400">Matched Keywords</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {matchedKeywords.map((kw, i) => (
                <span key={i} className="px-2 py-0.5 rounded-full text-[11px] bg-green-500/10 text-green-300 border border-green-500/20">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {missingKeywords.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <AlertCircle size={13} className="text-slate-500 shrink-0" />
              <span className="text-xs font-medium text-slate-500">Not Matched</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {missingKeywords.map((kw, i) => (
                <span key={i} className="px-2 py-0.5 rounded-full text-[11px] bg-white/5 text-slate-500 border border-white/10">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
