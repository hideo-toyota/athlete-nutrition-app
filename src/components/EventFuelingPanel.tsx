import React from 'react'
import { useAthlete } from '../context/AthleteContext'
import { useSnackbar } from '../context/SnackbarContext'
import {
  addDaysToDateKey,
  buildEventFuelingPlan,
  getDaysBetweenDateKeys
} from '../lib/appModel'
import {
  COMPETITION_EVENT_KIND_LABELS,
  CompetitionEventKind,
  DAY_MODE_LABELS,
  EVENT_DURATION_LABELS,
  EVENT_PRIORITY_LABELS,
  EventDuration,
  EventFuelingDay,
  EventPriority,
  Plan
} from '../types'
import { formatDateLabel } from '../lib/date'

function offsetLabel(offset: number) {
  if (offset === 0) return '当日'
  if (offset > 0) return `+${offset}日`
  return `${offset}日`
}

function rangeLabel(day: EventFuelingDay, key: 'carbs' | 'protein') {
  const grams = day[key]
  const perKg = key === 'carbs' ? day.carbsPerKg : day.proteinPerKg

  return `${grams.min}-${grams.max}g (${perKg.min}-${perKg.max}g/kg)`
}

function midpoint(min: number, max: number) {
  return Math.round((min + max) / 2)
}

function distributedGrams(total: number, ratio: number, minimum: number) {
  return Math.max(minimum, Math.round(total * ratio))
}

function estimatedKcal(carbs: number, protein: number) {
  return Math.max(120, Math.round(((carbs * 4 + protein * 4) * 1.25) / 10) * 10)
}

function generatedPlanKey(plan: Pick<Plan, 'timing' | 'title'>) {
  return `${plan.timing}:${plan.title.split(' / ')[0]}`
}

function athleteActionText(day?: EventFuelingDay) {
  if (!day) return '本番日を登録すると、今日やることがここに出ます。'
  if (day.dayMode === 'game') return '消化しやすい糖質を先に決め、競技中の水分・補食を携帯します。'
  if (day.dayMode === 'pre_game') return '主食を抜かず、脂質を重くしすぎない形で糖質を積み上げます。'
  if (day.dayMode === 'recovery') return '糖質とたんぱく質を戻し、睡眠と水分で翌日の疲労を残さないようにします。'
  return '練習量に合わせて補食を先に確保し、夕食で不足分を戻します。'
}

function supporterActionText(day?: EventFuelingDay) {
  if (!day) return '保護者・コーチ向けの支援ポイントもここに出ます。'
  if (day.appetite <= 2) return '食欲が低めなので、ゼリー・ヨーグルト・おにぎりなど小分けで渡せる形を用意します。'
  if (day.fatigue >= 4) return '疲労が高めなので、食事量の確認より「補食と早めの就寝」を声かけします。'
  if (day.dayMode === 'game') return '試合前後に迷わないよう、補食・水分・回復食をバッグに入れておきます。'
  return '細かい計算より、今日の主食・補食・水分が抜けていないかを一緒に確認します。'
}

function buildFuelingMealPlans(day: EventFuelingDay, athleteId: string): Array<Omit<Plan, 'id' | 'date'>> {
  const targetCarbs = midpoint(day.carbs.min, day.carbs.max)
  const targetProtein = midpoint(day.protein.min, day.protein.max)
  const appetiteNote = day.appetite <= 2 ? '小分け・飲める形' : '実行しやすい形'
  const snackTitle = day.dayMode === 'game' ? '本番逆算 補食（試合前後）' : '本番逆算 補食'
  const dinnerTitle = day.dayMode === 'recovery' ? '本番逆算 夕食（回復）' : '本番逆算 夕食'
  const meals: Array<{ timing: Plan['timing']; title: string; carbRatio: number; proteinRatio: number; minCarbs: number; minProtein: number }> = [
    { timing: 'Breakfast', title: '本番逆算 朝食', carbRatio: 0.3, proteinRatio: 0.25, minCarbs: 35, minProtein: 12 },
    { timing: 'Lunch', title: '本番逆算 昼食', carbRatio: 0.25, proteinRatio: 0.25, minCarbs: 35, minProtein: 15 },
    { timing: 'Snack', title: snackTitle, carbRatio: 0.2, proteinRatio: 0.15, minCarbs: 20, minProtein: 6 },
    { timing: 'Dinner', title: dinnerTitle, carbRatio: 0.25, proteinRatio: 0.35, minCarbs: 35, minProtein: 18 }
  ]

  return meals.map((meal) => {
    const carbs = distributedGrams(targetCarbs, meal.carbRatio, meal.minCarbs)
    const protein = distributedGrams(targetProtein, meal.proteinRatio, meal.minProtein)

    return {
      athleteId,
      title: `${meal.title} / ${appetiteNote}`,
      timing: meal.timing,
      kcal: estimatedKcal(carbs, protein),
      carbs,
      protein,
      status: 'planned'
    }
  })
}

export default function EventFuelingPanel() {
  const { show } = useSnackbar()
  const {
    selectedAthlete,
    selectedAthleteId,
    selectedSportProfile,
    selectedDate,
    todayDateKey,
    plans,
    checkin,
    eventsForSelected,
    upcomingEventForSelected,
    addEvent,
    addPlanForDate,
    deleteEvent,
    checkinForAthleteOnDate,
    setSelectedDate,
    setDayModeForDate
  } = useAthlete()
  const events = eventsForSelected()
  const upcomingEvent = upcomingEventForSelected()
  const defaultEventDate = addDaysToDateKey(todayDateKey, 5)
  const [activeEventId, setActiveEventId] = React.useState<string | null>(upcomingEvent?.id ?? null)
  const [title, setTitle] = React.useState('週末の本番')
  const [date, setDate] = React.useState(defaultEventDate)
  const [kind, setKind] = React.useState<CompetitionEventKind>('match')
  const [duration, setDuration] = React.useState<EventDuration>('medium')
  const [priority, setPriority] = React.useState<EventPriority>('key')

  React.useEffect(() => {
    if (activeEventId && events.some((event) => event.id === activeEventId)) return
    setActiveEventId(upcomingEvent?.id ?? events[0]?.id ?? null)
  }, [activeEventId, events, upcomingEvent])

  const activeEvent = events.find((event) => event.id === activeEventId) ?? upcomingEvent ?? events[0] ?? null
  const fuelingDays = activeEvent
    ? buildEventFuelingPlan({
      event: activeEvent,
      athlete: selectedAthlete,
      profile: selectedSportProfile,
      todayDateKey,
      fallbackCheckin: checkin,
      getCheckinForDate: (targetDate) => selectedAthleteId
        ? checkinForAthleteOnDate(selectedAthleteId, targetDate)
        : checkin
    })
    : []
  const selectedFuelingDay = fuelingDays.find((day) => day.date === selectedDate)
    ?? fuelingDays.find((day) => day.date === todayDateKey)
    ?? fuelingDays.find((day) => day.offset === 0)
    ?? fuelingDays[0]
  const daysUntil = activeEvent ? getDaysBetweenDateKeys(todayDateKey, activeEvent.date) : null

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!selectedAthleteId || !title.trim()) return

    addEvent({
      title: title.trim(),
      date,
      kind,
      duration,
      priority
    })
    setTitle('')
  }

  const applyDay = (day: EventFuelingDay) => {
    setDayModeForDate(day.date, day.dayMode)
    setSelectedDate(day.date)
  }

  const createMealPlansFromFueling = () => {
    if (!selectedAthleteId || !selectedFuelingDay) return

    applyDay(selectedFuelingDay)

    const existingKeys = new Set(
      plans
        .filter((plan) => plan.athleteId === selectedAthleteId && plan.date === selectedFuelingDay.date)
        .map((plan) => generatedPlanKey(plan))
    )
    const mealPlans = buildFuelingMealPlans(selectedFuelingDay, selectedAthleteId)
    const newMealPlans = mealPlans.filter((plan) => !existingKeys.has(generatedPlanKey(plan)))

    if (newMealPlans.length === 0) {
      show('この日の本番逆算プランは作成済みです')
      return
    }

    newMealPlans.forEach((plan) => addPlanForDate(selectedFuelingDay.date, plan))
    show(`${formatDateLabel(selectedFuelingDay.date)} に食事プランを${newMealPlans.length}件作成しました`)
  }

  return (
    <div className="glass event-panel rounded-xl p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.22em] text-amber-200">Main Demo</div>
          <h3 className="mt-1 font-semibold">Event Fueling / 本番逆算</h3>
          <div className="mt-1 text-sm text-slate-400">
            試合・大会・本番日から逆算し、体重 x g/kg/day と疲労感で1日単位の栄養目標を出します。
          </div>
        </div>
        <div className="rounded-full border border-amber-300/30 bg-amber-300/10 px-3 py-1 text-xs text-amber-100">
          エビデンス: ACSM/AND/DC 2016
        </div>
      </div>

      <form className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-6" onSubmit={handleSubmit}>
        <label className="lg:col-span-2">
          <span className="text-xs text-slate-500">本番名</span>
          <input
            aria-label="event-title"
            className="mt-1 w-full rounded border border-white/10 bg-[rgba(255,255,255,0.03)] px-3 py-2 text-sm text-slate-100"
            onChange={(event) => setTitle(event.target.value)}
            placeholder="例: 県大会 決勝"
            value={title}
          />
        </label>
        <label>
          <span className="text-xs text-slate-500">日付</span>
          <input
            aria-label="event-date"
            className="mt-1 w-full rounded border border-white/10 bg-[rgba(255,255,255,0.03)] px-3 py-2 text-sm text-slate-100"
            onChange={(event) => setDate(event.target.value)}
            type="date"
            value={date}
          />
        </label>
        <label>
          <span className="text-xs text-slate-500">種別</span>
          <select
            aria-label="event-kind"
            className="mt-1 w-full rounded border border-white/10 bg-[rgba(255,255,255,0.03)] px-3 py-2 text-sm text-slate-100"
            onChange={(event) => setKind(event.target.value as CompetitionEventKind)}
            value={kind}
          >
            {Object.entries(COMPETITION_EVENT_KIND_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <label>
          <span className="text-xs text-slate-500">競技時間</span>
          <select
            aria-label="event-duration"
            className="mt-1 w-full rounded border border-white/10 bg-[rgba(255,255,255,0.03)] px-3 py-2 text-sm text-slate-100"
            onChange={(event) => setDuration(event.target.value as EventDuration)}
            value={duration}
          >
            {Object.entries(EVENT_DURATION_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <label>
          <span className="text-xs text-slate-500">優先度</span>
          <select
            aria-label="event-priority"
            className="mt-1 w-full rounded border border-white/10 bg-[rgba(255,255,255,0.03)] px-3 py-2 text-sm text-slate-100"
            onChange={(event) => setPriority(event.target.value as EventPriority)}
            value={priority}
          >
            {Object.entries(EVENT_PRIORITY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <button
          className="rounded bg-amber-300 px-3 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50 lg:mt-5"
          disabled={!selectedAthleteId || !title.trim()}
          type="submit"
        >
          本番日を追加
        </button>
      </form>

      {events.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {events.map((event) => (
            <button
              className={`rounded-full border px-3 py-1 text-xs ${event.id === activeEvent?.id ? 'border-amber-300/60 bg-amber-300/10 text-amber-100' : 'border-white/10 text-slate-300'}`}
              key={event.id}
              onClick={() => setActiveEventId(event.id)}
              type="button"
            >
              {event.title} / {event.date}
            </button>
          ))}
        </div>
      )}

      {!activeEvent ? (
        <div className="mt-4 rounded-lg border border-dashed border-white/10 bg-[rgba(255,255,255,0.02)] p-4 text-sm text-slate-400">
          本番日を追加すると、カーボローディング・たんぱく質・水分の逆算プランが表示されます。
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          <div className="rounded-xl border border-amber-300/20 bg-amber-300/10 p-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="text-xs uppercase tracking-[0.22em] text-amber-100">Action Path</div>
                <div className="mt-1 font-semibold text-amber-50">初めてでも迷わない3ステップ</div>
                <div className="mt-2 grid grid-cols-1 gap-2 text-sm text-slate-300 lg:grid-cols-3">
                  <div>1. 本番日を登録して、逆算の起点を作る</div>
                  <div>2. 今日の糖質・たんぱく質目標を見る</div>
                  <div>3. ボタンで食事カードに変換して実行記録する</div>
                </div>
              </div>
              <button
                className="rounded-lg bg-amber-300 px-4 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-amber-950/20 disabled:opacity-50"
                disabled={!selectedAthleteId || !selectedFuelingDay}
                onClick={createMealPlansFromFueling}
                type="button"
              >
                選択日の食事プランを作る
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-4">
            <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3 lg:col-span-2">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Countdown</div>
              <div className="mt-2 text-xl font-semibold text-amber-200">
                {daysUntil != null && daysUntil >= 0 ? `本番まであと${daysUntil}日` : '本番後の回復期間'}
              </div>
              <div className="mt-1 text-sm text-slate-400">
                {activeEvent.title} / {formatDateLabel(activeEvent.date)} / {EVENT_DURATION_LABELS[activeEvent.duration]}
              </div>
            </div>
            <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Today Target</div>
              <div className="mt-2 text-sm text-slate-300">
                糖質 <span className="font-semibold text-amber-100">{selectedFuelingDay ? rangeLabel(selectedFuelingDay, 'carbs') : '-'}</span>
              </div>
              <div className="mt-1 text-sm text-slate-300">
                たんぱく質 <span className="font-semibold text-emerald-100">{selectedFuelingDay ? rangeLabel(selectedFuelingDay, 'protein') : '-'}</span>
              </div>
            </div>
            <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Condition</div>
              <div className="mt-2 text-sm text-slate-300">
                疲労 {selectedFuelingDay?.fatigue ?? checkin.fatigue}/5 / 睡眠 {selectedFuelingDay?.sleepHours.toFixed(1) ?? checkin.sleepHours.toFixed(1)}h
              </div>
              <div className="mt-1 text-xs text-slate-400">
                疲労が高い日は糖質下限を+0.25-0.5g/kgで補正します。
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <div className="rounded-lg border border-white/10 bg-[rgba(255,255,255,0.02)] p-3 text-sm">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Athlete View</div>
              <div className="mt-2 font-medium text-slate-100">選手本人が今日やること</div>
              <div className="mt-2 text-slate-400">{athleteActionText(selectedFuelingDay)}</div>
            </div>
            <div className="rounded-lg border border-white/10 bg-[rgba(255,255,255,0.02)] p-3 text-sm">
              <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Supporter View</div>
              <div className="mt-2 font-medium text-slate-100">保護者・コーチが支援すること</div>
              <div className="mt-2 text-slate-400">{supporterActionText(selectedFuelingDay)}</div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <div className="min-w-[760px] space-y-2">
              {fuelingDays.map((day) => (
                <div
                  className={`grid grid-cols-12 gap-3 rounded-lg border p-3 text-sm ${day.date === selectedDate ? 'border-amber-300/50 bg-amber-300/10' : 'border-white/10 bg-[rgba(255,255,255,0.02)]'}`}
                  key={day.date}
                >
                  <div className="col-span-2">
                    <div className="font-medium text-slate-100">{offsetLabel(day.offset)} {day.label}</div>
                    <div className="mt-1 text-xs text-slate-500">{day.date}</div>
                    <div className="mt-1 text-xs text-slate-400">{DAY_MODE_LABELS[day.dayMode]}</div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-xs text-slate-500">糖質</div>
                    <div className="font-semibold text-amber-100">{rangeLabel(day, 'carbs')}</div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-xs text-slate-500">たんぱく質</div>
                    <div className="font-semibold text-emerald-100">{rangeLabel(day, 'protein')}</div>
                  </div>
                  <div className="col-span-4">
                    <div className="text-slate-300">{day.focus}</div>
                    <div className="mt-2 text-xs text-slate-500">{day.hydration}</div>
                    {day.adjustments.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {day.adjustments.map((adjustment) => (
                          <span className="rounded-full bg-amber-300/10 px-2 py-1 text-[11px] text-amber-100" key={adjustment}>{adjustment}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="col-span-2 flex flex-col gap-2">
                    <div className="text-xs text-slate-500">タイミング: {day.timing}</div>
                    <button
                      className="rounded border border-white/10 px-2 py-1 text-xs text-slate-200 hover:border-amber-300/50"
                      onClick={() => applyDay(day)}
                      type="button"
                    >
                      この日を開く
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <div className="rounded-lg border border-white/10 bg-[rgba(255,255,255,0.02)] p-3 text-sm text-slate-300">
              <div className="font-medium text-slate-100">エビデンスと使い方</div>
              <div className="mt-2 text-slate-400">
                糖質は練習量・本番時間に応じて 5-7 / 6-10 / 7-12g/kg/day を使い分けます。
                90分以上の本番はカーボローディングを優先し、60分超は競技中補給も検討します。
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <a className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300 hover:text-amber-100" href="https://pubmed.ncbi.nlm.nih.gov/26920240/" rel="noreferrer" target="_blank">ACSM/AND/DC</a>
                <a className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300 hover:text-amber-100" href="https://www.dietitians.ca/DietitiansOfCanada/media/Documents/Resources/noap-position-paper.pdf" rel="noreferrer" target="_blank">Position Paper PDF</a>
              </div>
            </div>
            <div className="rounded-lg border border-white/10 bg-[rgba(255,255,255,0.02)] p-3 text-sm text-slate-300">
              <div className="font-medium text-slate-100">重点栄養素</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {selectedSportProfile.focusNutrients.map((nutrient) => (
                  <span className="rounded-full bg-[rgba(0,229,255,0.08)] px-2 py-1 text-xs text-neon-300" key={nutrient}>{nutrient}</span>
                ))}
              </div>
              <div className="mt-3 text-slate-400">
                体重だけでなく、疲労・睡眠・食欲のログに応じて「増やす」「小分けにする」「飲める形にする」を切り替えます。
              </div>
              <button
                className="mt-3 rounded border border-rose-300/30 px-3 py-1 text-xs text-rose-100"
                onClick={() => deleteEvent(activeEvent.id)}
                type="button"
              >
                この本番日を削除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
