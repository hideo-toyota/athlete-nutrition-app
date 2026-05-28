import React from 'react'
import { DAY_MODE_LABELS, DayMode } from '../types'

export default function Header({
  athleteName,
  sportLabel,
  dayMode,
  onNewPlan
}: {
  athleteName: string
  sportLabel: string
  dayMode: DayMode
  onNewPlan: () => void
}){
  return (
    <header className="flex flex-col gap-4 py-4 md:flex-row md:items-center md:justify-between">
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-neon-300 to-neon-500 flex items-center justify-center neon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2v20M2 12h20" stroke="#001" strokeWidth="1.5" opacity="0.9"/>
          </svg>
        </div>
        <div>
          <h1 className="text-xl font-semibold">Athlete Nutrition</h1>
          <p className="text-sm text-slate-400">試合日と体調に合わせて、食事実行まで支援するコンディショニングUI</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden rounded-full border border-white/10 bg-[rgba(255,255,255,0.03)] px-4 py-2 text-right text-xs text-slate-300 md:block">
          <div>{athleteName}</div>
          <div className="text-slate-500">{sportLabel}</div>
          <div className="text-neon-300">{DAY_MODE_LABELS[dayMode]}</div>
        </div>
        <button aria-label="新しいプランを追加" className="px-3 py-2 bg-[rgba(255,255,255,0.03)] glass rounded-md text-sm" onClick={onNewPlan}>New Plan</button>
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-neon-300 to-neon-500 text-xs font-semibold text-slate-950">
          {athleteName.slice(0, 2).toUpperCase()}
        </div>
      </div>
    </header>
  )
}
