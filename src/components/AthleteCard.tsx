import React from 'react'

type Athlete = {
  name: string
  sport: string
  category: string
  focus: string
  selected?: boolean
  onClick?: () => void
}

export default function AthleteCard({ name, sport, category, focus, selected, onClick }: Athlete){
  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick && onClick() }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onKeyDown={handleKey}
      onClick={onClick}
      className={`glass rounded-lg p-3 transition-colors ${selected ? 'border-neon-500/60 bg-[rgba(0,229,255,0.08)]' : ''}`}
    >
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-md bg-gradient-to-br from-neon-300 to-neon-500" />
        <div>
          <div className="font-medium">{name}</div>
          <div className="text-sm text-slate-400">{sport}</div>
          <div className="text-xs text-slate-500">{category}</div>
        </div>
      </div>
      <div className="mt-3 text-xs text-slate-400">{focus}</div>
    </div>
  )
}
