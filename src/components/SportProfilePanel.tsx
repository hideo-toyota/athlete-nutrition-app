import React from 'react'
import { getDailyTargets } from '../lib/appModel'
import { DayMode, SportId, SportProfile } from '../types'
import { SPORT_PROFILES } from '../data/sportProfiles'

export default function SportProfilePanel({
  profile,
  dayMode,
  bodyWeight,
  onChange
}: {
  profile: SportProfile
  dayMode: DayMode
  bodyWeight: number
  onChange: (sportId: SportId) => void
}){
  const targets = getDailyTargets(profile, dayMode, bodyWeight)

  return (
    <div className="glass rounded-xl p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="font-semibold">Sport Profile</h3>
          <div className="mt-1 text-sm text-slate-400">競技を選ぶと、根拠ベースのターゲット値と注目栄養素が切り替わります。</div>
        </div>
        <select
          aria-label="sport-profile"
          className="rounded border border-white/10 bg-[rgba(255,255,255,0.03)] px-3 py-2 text-sm text-slate-100"
          value={profile.id}
          onChange={(e) => onChange(e.target.value as SportId)}
        >
          {SPORT_PROFILES.map((option) => (
            <option key={option.id} value={option.id}>{option.label}</option>
          ))}
        </select>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Carbs</div>
          <div className="mt-2 text-lg font-semibold text-neon-300">{targets.carbs.min}-{targets.carbs.max}g</div>
          <div className="mt-1 text-xs text-slate-400">{bodyWeight.toFixed(1)}kg x {profile.carbTargets[dayMode].min}-{profile.carbTargets[dayMode].max}g/kg/日</div>
        </div>
        <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Protein</div>
          <div className="mt-2 text-lg font-semibold text-neon-300">{targets.protein.min}-{targets.protein.max}g</div>
          <div className="mt-1 text-xs text-slate-400">{bodyWeight.toFixed(1)}kg x {profile.proteinTarget.min}-{profile.proteinTarget.max}g/kg/日</div>
        </div>
        <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Focus</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {profile.focusNutrients.map((item) => (
              <span key={item} className="rounded-full bg-[rgba(0,229,255,0.08)] px-2 py-1 text-xs text-neon-300">{item}</span>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3 text-sm text-slate-300">
          <div className="font-medium text-slate-100">{profile.label}</div>
          <div className="mt-2 text-slate-400">{profile.summary}</div>
          <div className="mt-3 text-slate-300">競技カテゴリ: {profile.category}</div>
          <div className="mt-2 text-slate-400">{profile.fuelingNote}</div>
        </div>
        <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3 text-sm text-slate-300">
          <div className="font-medium text-slate-100">Hydration / Risk Notes</div>
          <div className="mt-2 text-slate-400">{profile.hydrationNote}</div>
          <div className="mt-3 text-slate-400">{profile.cautionNote}</div>
        </div>
      </div>

      <div className="mt-4 rounded-lg border border-white/10 bg-[rgba(255,255,255,0.02)] p-3">
        <div className="text-sm font-medium text-slate-100">Evidence Basis</div>
        <div className="mt-2 flex flex-wrap gap-2">
          {profile.references.map((reference) => (
            <a
              key={reference.url}
              className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300 transition-colors hover:border-neon-500/40 hover:text-neon-300"
              href={reference.url}
              rel="noreferrer"
              target="_blank"
            >
              {reference.label}
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
