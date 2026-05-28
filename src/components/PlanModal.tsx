import React, { useCallback, useEffect, useState } from 'react'
import { useAthlete } from '../context/AthleteContext'
import { useSnackbar } from '../context/SnackbarContext'
import { EditablePlan, MEAL_SLOTS, MEAL_SLOT_LABELS, Plan } from '../types'

type FormState = {
  title: string
  timing: Plan['timing']
  kcal: number
  carbs: number
  protein: number
}

const DEFAULT_FORM: FormState = {
  title: '',
  timing: 'Breakfast',
  kcal: 0,
  carbs: 0,
  protein: 0
}

function parseNumberOrZero(value: number) {
  return Number.isFinite(value) ? value : 0
}

export default function PlanModal({ plan, onClose }: { plan: EditablePlan | null, onClose: () => void }){
  const { updatePlan, addPlan, deletePlan, selectedAthleteId } = useAthlete()
  const { show } = useSnackbar()
  const [form, setForm] = useState<FormState>(DEFAULT_FORM)
  const [error, setError] = useState<string | null>(null)
  const titleId = React.useId()
  const titleInputId = React.useId()
  const timingInputId = React.useId()
  const kcalInputId = React.useId()
  const carbsInputId = React.useId()
  const proteinInputId = React.useId()
  const initialFormRef = React.useRef<FormState>(DEFAULT_FORM)

  const isNew = !plan?.id
  const resolvedAthleteId = plan?.athleteId ?? selectedAthleteId ?? undefined

  useEffect(() => {
    const nextForm = plan ? {
      title: plan.title ?? '',
      timing: plan.timing ?? 'Breakfast',
      kcal: parseNumberOrZero(plan.kcal ?? 0),
      carbs: parseNumberOrZero(plan.carbs ?? 0),
      protein: parseNumberOrZero(plan.protein ?? 0)
    } : DEFAULT_FORM

    initialFormRef.current = nextForm
    setForm(nextForm)
    setError(null)
  }, [plan])

  const containerRef = React.useRef<HTMLDivElement | null>(null)
  const firstInputRef = React.useRef<HTMLInputElement | null>(null)
  const previouslyFocused = React.useRef<HTMLElement | null>(null)

  const isDirty =
    form.title !== initialFormRef.current.title ||
    form.timing !== initialFormRef.current.timing ||
    form.kcal !== initialFormRef.current.kcal ||
    form.carbs !== initialFormRef.current.carbs ||
    form.protein !== initialFormRef.current.protein

  const requestClose = useCallback(() => {
    if (isDirty && !confirm('編集中の内容を破棄しますか？')) {
      return
    }

    onClose()
  }, [isDirty, onClose])

  useEffect(() => {
    function onKey(event: KeyboardEvent){
      if (event.key === 'Escape') {
        requestClose()
      }
    }

    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [requestClose])

  useEffect(() => {
    previouslyFocused.current = document.activeElement as HTMLElement | null
    setTimeout(() => firstInputRef.current?.focus(), 0)
    return () => previouslyFocused.current?.focus()
  }, [])

  const onKeyDownTrap = (event: React.KeyboardEvent) => {
    if (event.key !== 'Tab' || !containerRef.current) return

    const focusable = containerRef.current.querySelectorAll<HTMLElement>(
      'a[href], button, textarea, input, select, [tabindex]:not([tabindex="-1"])'
    )

    if (focusable.length === 0) return

    const first = focusable[0]
    const last = focusable[focusable.length - 1]

    if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    }
  }

  const save = () => {
    if (!form.title.trim()) {
      setError('タイトルは必須です')
      return
    }

    if (!(Number.isFinite(form.kcal) && form.kcal > 0)) {
      setError('kcal は 0 より大きい値を入力してください')
      return
    }

    if (!(Number.isFinite(form.carbs) && form.carbs > 0)) {
      setError('炭水化物は 0 より大きい値を入力してください')
      return
    }

    if (!(Number.isFinite(form.protein) && form.protein >= 0)) {
      setError('たんぱく質は 0 以上の値を入力してください')
      return
    }

    if (isNew) {
      if (!resolvedAthleteId) {
        setError('選手が選択されていません')
        return
      }

      addPlan({
        athleteId: resolvedAthleteId,
        title: form.title,
        timing: form.timing,
        kcal: form.kcal,
        carbs: form.carbs,
        protein: form.protein,
        status: 'planned'
      })
      show('プランを追加しました')
    } else {
      if (!plan?.id) return

      updatePlan({
        id: plan.id,
        title: form.title,
        timing: form.timing,
        kcal: form.kcal,
        carbs: form.carbs,
        protein: form.protein
      })
      show('プランを保存しました')
    }

    onClose()
  }

  const del = () => {
    if (!plan?.id) return
    if (!confirm('このプランを削除しますか？')) return

    deletePlan(plan.id)
    show('プランを削除しました')
    onClose()
  }

  return (
    <div role="dialog" aria-modal="true" aria-labelledby={titleId} className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={requestClose} />
      <div ref={containerRef} onKeyDown={onKeyDownTrap} className="relative glass mx-4 max-h-[90vh] w-full max-w-md overflow-y-auto rounded-xl p-6">
        <h3 id={titleId} className="text-lg font-semibold">{isNew ? 'New Plan' : 'Edit Plan'}</h3>
        <div className="mt-4 space-y-3">
          {error && <div className="text-sm text-red-400">{error}</div>}
          <div>
            <label className="text-sm text-slate-300" htmlFor={titleInputId}>Title</label>
            <input
              id={titleInputId}
              ref={firstInputRef}
              aria-label="plan-title"
              className="mt-1 w-full rounded bg-[rgba(255,255,255,0.02)] p-2"
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
            />
          </div>
          <div>
            <label className="text-sm text-slate-300" htmlFor={timingInputId}>Meal Slot</label>
            <select
              id={timingInputId}
              aria-label="plan-timing"
              className="mt-1 w-full rounded bg-[rgba(255,255,255,0.02)] p-2"
              value={form.timing}
              onChange={(event) => setForm({ ...form, timing: event.target.value as Plan['timing'] })}
            >
              {MEAL_SLOTS.map((slot) => (
                <option key={slot} value={slot}>{MEAL_SLOT_LABELS[slot]}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm text-slate-300" htmlFor={kcalInputId}>kcal</label>
              <input
                id={kcalInputId}
                aria-label="plan-kcal"
                min={0}
                step={1}
                type="number"
                className="mt-1 w-full rounded bg-[rgba(255,255,255,0.02)] p-2"
                value={form.kcal}
                onChange={(event) => setForm({ ...form, kcal: parseNumberOrZero(event.currentTarget.valueAsNumber) })}
              />
            </div>
            <div>
              <label className="text-sm text-slate-300" htmlFor={carbsInputId}>carbs (g)</label>
              <input
                id={carbsInputId}
                aria-label="plan-carbs"
                min={0}
                step={1}
                type="number"
                className="mt-1 w-full rounded bg-[rgba(255,255,255,0.02)] p-2"
                value={form.carbs}
                onChange={(event) => setForm({ ...form, carbs: parseNumberOrZero(event.currentTarget.valueAsNumber) })}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm text-slate-300" htmlFor={proteinInputId}>protein (g)</label>
              <input
                id={proteinInputId}
                aria-label="plan-protein"
                min={0}
                step={1}
                type="number"
                className="mt-1 w-full rounded bg-[rgba(255,255,255,0.02)] p-2"
                value={form.protein}
                onChange={(event) => setForm({ ...form, protein: parseNumberOrZero(event.currentTarget.valueAsNumber) })}
              />
            </div>
            <div className="rounded bg-[rgba(255,255,255,0.03)] p-3 text-xs text-slate-400">
              新規作成時のステータスは「未実施」で開始します。実行チェックはカード上で切り替えられます。
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between">
          <div>
            {!isNew && <button className="rounded bg-[rgba(255,75,75,0.12)] px-3 py-2 text-red-300" onClick={del}>Delete</button>}
          </div>
          <div className="flex gap-3">
            <button className="rounded bg-[rgba(255,255,255,0.03)] px-4 py-2" onClick={requestClose}>Cancel</button>
            <button className="rounded bg-neon-500 px-4 py-2 text-black" onClick={save}>Save</button>
          </div>
        </div>
      </div>
    </div>
  )
}
