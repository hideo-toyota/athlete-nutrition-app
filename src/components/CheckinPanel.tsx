import React, { useEffect, useId, useRef, useState } from 'react'
import { DailyCheckin } from '../types'

function ScoreButtons({
  label,
  value,
  onChange
}: {
  label: string
  value: number
  onChange: (nextValue: number) => void
}){
  return (
    <div>
      <div className="text-sm text-slate-300">{label}</div>
      <div className="mt-2 flex flex-wrap gap-2">
        {[1, 2, 3, 4, 5].map((score) => (
          <button
            key={score}
            aria-label={`${label} ${score}`}
            className={`min-h-[44px] min-w-[44px] rounded-full border text-sm ${value === score ? 'border-neon-500/50 bg-neon-500/10 text-neon-300' : 'border-white/10 text-slate-400'}`}
            onClick={() => onChange(score)}
            onMouseDown={(event) => event.preventDefault()}
            onPointerDown={(event) => {
              event.preventDefault()
              onChange(score)
            }}
            type="button"
          >
            {score}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function CheckinPanel({
  checkin,
  onChange
}: {
  checkin: DailyCheckin
  onChange: (patch: Partial<DailyCheckin>) => void
}){
  const [activeField, setActiveField] = useState<'sleepHours' | 'weight' | 'note' | null>(null)
  const [draft, setDraft] = useState({
    sleepHours: checkin.sleepHours,
    weight: checkin.weight,
    note: checkin.note
  })
  const draftRef = useRef(draft)
  const pendingDraftRef = useRef<Partial<typeof draft> | null>(null)
  const sleepInputRef = useRef<HTMLInputElement | null>(null)
  const weightInputRef = useRef<HTMLInputElement | null>(null)
  const noteInputRef = useRef<HTMLTextAreaElement | null>(null)
  const sleepInputId = useId()
  const weightInputId = useId()
  const noteInputId = useId()

  useEffect(() => {
    setDraft((prev) => {
      const pendingDraft = pendingDraftRef.current
      const nextDraft = {
        sleepHours: activeField === 'sleepHours' ? prev.sleepHours : checkin.sleepHours,
        weight: activeField === 'weight' ? prev.weight : checkin.weight,
        note: activeField === 'note' ? prev.note : checkin.note
      }

      if (pendingDraft) {
        if (pendingDraft.sleepHours !== undefined && checkin.sleepHours !== pendingDraft.sleepHours) {
          nextDraft.sleepHours = pendingDraft.sleepHours
        }
        if (pendingDraft.weight !== undefined && checkin.weight !== pendingDraft.weight) {
          nextDraft.weight = pendingDraft.weight
        }
        if (pendingDraft.note !== undefined && checkin.note !== pendingDraft.note) {
          nextDraft.note = pendingDraft.note
        }
        if (
          (pendingDraft.sleepHours === undefined || checkin.sleepHours === pendingDraft.sleepHours) &&
          (pendingDraft.weight === undefined || checkin.weight === pendingDraft.weight) &&
          (pendingDraft.note === undefined || checkin.note === pendingDraft.note)
        ) {
          pendingDraftRef.current = null
        }
      }

      draftRef.current = nextDraft
      return nextDraft
    })
  }, [activeField, checkin])

  const currentDraftPatch = () => {
    const sleepHours = sleepInputRef.current?.valueAsNumber ?? draftRef.current.sleepHours
    const weight = weightInputRef.current?.valueAsNumber ?? draftRef.current.weight
    const note = noteInputRef.current?.value ?? draftRef.current.note

    return {
      sleepHours: Number.isFinite(sleepHours) ? sleepHours : 0,
      weight: Number.isFinite(weight) ? weight : 0,
      note
    }
  }

  const updateDraft = (patch: Partial<typeof draft>) => {
    setDraft((prev) => {
      const nextDraft = { ...prev, ...patch }
      draftRef.current = nextDraft
      return nextDraft
    })
  }

  const finishEditing = () => {
    window.setTimeout(() => setActiveField(null), 0)
  }

  const commitDraft = (patch: Partial<DailyCheckin>) => {
    const nextDraft = currentDraftPatch()
    pendingDraftRef.current = nextDraft
    updateDraft(nextDraft)
    onChange(patch)
    const syncInputValues = () => {
      if (sleepInputRef.current) sleepInputRef.current.value = String(nextDraft.sleepHours)
      if (weightInputRef.current) weightInputRef.current.value = String(nextDraft.weight)
      if (noteInputRef.current) noteInputRef.current.value = nextDraft.note
    }
    // Keep the visible field stable through React's batched parent update after blur/click.
    window.setTimeout(syncInputValues, 0)
    window.setTimeout(syncInputValues, 120)
  }

  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold">Condition Log</h4>
        <div className="text-xs text-slate-500">入力欄はフォーカスアウトで保存</div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <div>
          <label className="text-sm text-slate-300" htmlFor={sleepInputId}>睡眠時間</label>
          <input
            id={sleepInputId}
            ref={sleepInputRef}
            className="mt-1 w-full rounded bg-[rgba(255,255,255,0.02)] p-2"
            min={0}
            step={0.5}
            type="number"
            value={draft.sleepHours}
            onBlur={() => {
              commitDraft({ sleepHours: currentDraftPatch().sleepHours })
              finishEditing()
            }}
            onChange={(e) => {
              const value = e.currentTarget.valueAsNumber
              updateDraft({ sleepHours: Number.isFinite(value) ? value : 0 })
            }}
            onFocus={() => setActiveField('sleepHours')}
          />
        </div>
        <div>
          <label className="text-sm text-slate-300" htmlFor={weightInputId}>体重 (kg)</label>
          <input
            id={weightInputId}
            ref={weightInputRef}
            className="mt-1 w-full rounded bg-[rgba(255,255,255,0.02)] p-2"
            min={0}
            step={0.1}
            type="number"
            value={draft.weight}
            onBlur={() => {
              commitDraft({ weight: currentDraftPatch().weight })
              finishEditing()
            }}
            onChange={(e) => {
              const value = e.currentTarget.valueAsNumber
              updateDraft({ weight: Number.isFinite(value) ? value : 0 })
            }}
            onFocus={() => setActiveField('weight')}
          />
        </div>
      </div>
      <div className="mt-4 space-y-4">
        <ScoreButtons label="疲労感" value={checkin.fatigue} onChange={(fatigue) => commitDraft({ ...currentDraftPatch(), fatigue })} />
        <ScoreButtons label="食欲" value={checkin.appetite} onChange={(appetite) => commitDraft({ ...currentDraftPatch(), appetite })} />
        <div>
          <label className="text-sm text-slate-300" htmlFor={noteInputId}>メモ</label>
          <textarea
            id={noteInputId}
            ref={noteInputRef}
            className="mt-1 min-h-[96px] w-full rounded bg-[rgba(255,255,255,0.02)] p-2"
            placeholder="移動が長い、胃が重い、練習量が多い など"
            value={draft.note}
            onBlur={() => {
              commitDraft({ note: currentDraftPatch().note })
              finishEditing()
            }}
            onChange={(e) => updateDraft({ note: e.target.value })}
            onFocus={() => setActiveField('note')}
          />
        </div>
      </div>
    </div>
  )
}
