import React from 'react'
import { DayMode, DAY_MODES, DAY_MODE_HINTS, DAY_MODE_LABELS } from '../types'

export default function DayModeSelector({
  value,
  onChange
}: {
  value: DayMode
  onChange: (mode: DayMode) => void
}){
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="day mode">
        {DAY_MODES.map((mode) => (
          <button
            key={mode}
            role="radio"
            aria-checked={value === mode}
            className={`rounded-full border px-3 py-2 text-sm transition-colors ${value === mode ? 'border-neon-500/50 bg-neon-500/10 text-neon-300' : 'border-white/10 text-slate-400 hover:border-neon-500/40 hover:text-slate-100'}`}
            onClick={() => onChange(mode)}
            type="button"
          >
            {DAY_MODE_LABELS[mode]}
          </button>
        ))}
      </div>
      <div className="text-sm text-slate-400">{DAY_MODE_HINTS[value]}</div>
    </div>
  )
}
