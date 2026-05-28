import React from 'react'
import { MealSlot, MEAL_SLOT_LABELS, PlanStatus, PLAN_STATUS_LABELS, PLAN_STATUSES } from '../types'
import { resizeImageToDataUrl } from '../lib/image'
import { useSnackbar } from '../context/SnackbarContext'

type Props = {
  title: string
  timing: MealSlot
  kcal: number
  carbs: number
  protein: number
  status: PlanStatus
  suggestions: string[]
  photoDataUrl?: string
  onClick?: () => void
  onStatusChange: (status: PlanStatus) => void
  onPhotoChange: (photoDataUrl: string | null) => void
}

const statusTone: Record<PlanStatus, string> = {
  planned: 'border-white/10 bg-[rgba(255,255,255,0.03)] text-slate-300',
  partial: 'border-amber-400/30 bg-amber-400/10 text-amber-200',
  done: 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200',
  skipped: 'border-rose-400/30 bg-rose-400/10 text-rose-200'
}

export default function NutritionCard({
  title,
  timing,
  kcal,
  carbs,
  protein,
  status,
  suggestions,
  photoDataUrl,
  onClick,
  onStatusChange,
  onPhotoChange
}: Props){
  const fileInputRef = React.useRef<HTMLInputElement | null>(null)
  const snackbar = useSnackbar()

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onClick && onClick()
    }
  }

  const handlePhotoSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.currentTarget.files?.[0]
    event.currentTarget.value = ''
    if (!file) return

    try {
      const dataUrl = await resizeImageToDataUrl(file)
      onPhotoChange(dataUrl)
    } catch (error) {
      console.error('photo load failed', error)
      snackbar.show('写真の読み込みに失敗しました。別の画像でお試しください。')
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onKeyDown={handleKey}
      onClick={onClick}
      className="glass neon w-full cursor-pointer rounded-xl p-4 transition-transform hover:scale-[1.01]"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">{MEAL_SLOT_LABELS[timing]}</div>
          <h3 className="mt-2 text-lg font-semibold text-neon-300">{title}</h3>
        </div>
        <div className={`rounded-full border px-2 py-1 text-xs ${statusTone[status]}`}>{PLAN_STATUS_LABELS[status]}</div>
      </div>

      <div className="mt-3 text-sm text-slate-300">{kcal} kcal • 炭水化物 {carbs}g • たんぱく質 {protein}g</div>
      {photoDataUrl && (
        <img
          alt={`${title} meal`}
          className="mt-4 aspect-[4/3] w-full rounded-lg object-cover"
          src={photoDataUrl}
        />
      )}
      <div className="mt-4 h-2 rounded-full bg-gradient-to-r from-neon-300 to-neon-500" />

      <div className="mt-4 flex flex-wrap gap-2" onClick={(e) => e.stopPropagation()}>
        {PLAN_STATUSES.map((nextStatus) => (
          <button
            key={nextStatus}
            className={`min-h-[44px] min-w-[44px] rounded-full border px-2 py-1 text-xs transition-colors ${status === nextStatus ? statusTone[nextStatus] : 'border-white/10 text-slate-400 hover:border-neon-500/40 hover:text-slate-100'}`}
            onClick={() => onStatusChange(nextStatus)}
            type="button"
          >
            {PLAN_STATUS_LABELS[nextStatus]}
          </button>
        ))}
      </div>

      <div className="mt-3 flex flex-wrap gap-2" onClick={(e) => e.stopPropagation()}>
        <input
          ref={fileInputRef}
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={handlePhotoSelect}
          type="file"
        />
        <button
          className="rounded-full border border-white/10 px-3 py-2 text-xs text-slate-300 hover:border-neon-500/40 hover:text-neon-300"
          onClick={() => fileInputRef.current?.click()}
          type="button"
        >
          {photoDataUrl ? '写真を変更' : '写真を追加'}
        </button>
        {photoDataUrl && (
          <button
            className="rounded-full border border-rose-400/30 px-3 py-2 text-xs text-rose-200"
            onClick={() => onPhotoChange(null)}
            type="button"
          >
            写真を削除
          </button>
        )}
      </div>

      <div className="mt-4 rounded-lg bg-[rgba(255,255,255,0.03)] p-3 text-xs text-slate-400">
        <div className="mb-2 text-slate-300">コンビニ代替案</div>
        <div>{suggestions.join(' / ')}</div>
      </div>
    </div>
  )
}
