import React from 'react'
import { MealSlot } from '../types'

export type TeamFoodLogItem = {
  id: string
  athleteName: string
  sportLabel: string
  timing: MealSlot
  timingLabel: string
  title: string
  note: string
  kcal: number
  carbs: number
  protein: number
  photoDataUrl?: string
  tags: string[]
}

type Props = {
  items: TeamFoodLogItem[]
  onCopyPlan: (item: TeamFoodLogItem) => void
  onAddReminder: (item: TeamFoodLogItem) => void
}

export default function TeamFoodLogPanel({ items, onCopyPlan, onAddReminder }: Props) {
  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">Team Food Log</h3>
          <div className="mt-1 text-sm text-slate-400">仲間の実例から、今日まねできる食事を探すCtoCログ</div>
        </div>
        <div className="rounded-full border border-neon-500/30 px-3 py-1 text-xs text-neon-300">Share</div>
      </div>

      {items.length === 0 ? (
        <div className="mt-4 rounded-lg border border-dashed border-white/10 bg-[rgba(255,255,255,0.02)] p-4 text-sm text-slate-400">
          まだ共有できるフードログがありません。他の選手の食事記録が入るとここに表示されます。
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
          {items.map((item) => (
            <article key={item.id} className="rounded-lg border border-white/10 bg-[rgba(255,255,255,0.03)] p-3">
              {item.photoDataUrl && (
                <img
                  alt={`${item.title} shared meal`}
                  className="mb-3 aspect-[4/3] w-full rounded-lg object-cover"
                  src={item.photoDataUrl}
                />
              )}
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{item.timingLabel}</div>
                  <h4 className="mt-1 font-semibold text-neon-300">{item.title}</h4>
                </div>
                <div className="text-right text-xs text-slate-500">
                  <div>{item.athleteName}</div>
                  <div>{item.sportLabel}</div>
                </div>
              </div>
              <div className="mt-2 text-sm text-slate-300">{item.kcal} kcal / 糖質 {item.carbs}g / たんぱく質 {item.protein}g</div>
              <p className="mt-2 text-xs text-slate-400">{item.note}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {item.tags.map((tag) => (
                  <span key={tag} className="rounded-full bg-white/5 px-2 py-1 text-[11px] text-slate-300">{tag}</span>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  className="rounded-full border border-neon-500/40 px-3 py-2 text-xs text-neon-300"
                  onClick={() => onCopyPlan(item)}
                  type="button"
                >
                  真似する
                </button>
                <button
                  className="rounded-full border border-white/10 px-3 py-2 text-xs text-slate-300 hover:border-neon-500/40 hover:text-neon-300"
                  onClick={() => onAddReminder(item)}
                  type="button"
                >
                  リマインドに追加
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
