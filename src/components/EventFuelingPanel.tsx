import React from 'react'
import { useAthlete } from '../context/AthleteContext'
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
  EventPriority
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

export default function EventFuelingPanel() {
  const {
    selectedAthlete,
    selectedAthleteId,
    selectedSportProfile,
    selectedDate,
    todayDateKey,
    checkin,
    eventsForSelected,
    upcomingEventForSelected,
    addEvent,
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

  return (
    <div className="glass rounded-xl p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="font-semibold">Event Fueling / 本番逆算</h3>
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
          className="rounded bg-neon-500 px-3 py-2 text-sm font-semibold text-black disabled:opacity-50 lg:mt-5"
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
              className={`rounded-full border px-3 py-1 text-xs ${event.id === activeEvent?.id ? 'border-neon-500/60 bg-neon-500/10 text-neon-200' : 'border-white/10 text-slate-300'}`}
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
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-4">
            <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3 lg:col-span-2">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Countdown</div>
              <div className="mt-2 text-xl font-semibold text-neon-300">
                {daysUntil != null && daysUntil >= 0 ? `本番まであと${daysUntil}日` : '本番後の回復期間'}
              </div>
              <div className="mt-1 text-sm text-slate-400">
                {activeEvent.title} / {formatDateLabel(activeEvent.date)} / {EVENT_DURATION_LABELS[activeEvent.duration]}
              </div>
            </div>
            <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Today Target</div>
              <div className="mt-2 text-sm text-slate-300">
                糖質 {selectedFuelingDay ? rangeLabel(selectedFuelingDay, 'carbs') : '-'}
              </div>
              <div className="mt-1 text-sm text-slate-300">
                たんぱく質 {selectedFuelingDay ? rangeLabel(selectedFuelingDay, 'protein') : '-'}
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

          <div className="overflow-x-auto">
            <div className="min-w-[760px] space-y-2">
              {fuelingDays.map((day) => (
                <div
                  className={`grid grid-cols-12 gap-3 rounded-lg border p-3 text-sm ${day.date === selectedDate ? 'border-neon-500/50 bg-neon-500/10' : 'border-white/10 bg-[rgba(255,255,255,0.02)]'}`}
                  key={day.date}
                >
                  <div className="col-span-2">
                    <div className="font-medium text-slate-100">{offsetLabel(day.offset)} {day.label}</div>
                    <div className="mt-1 text-xs text-slate-500">{day.date}</div>
                    <div className="mt-1 text-xs text-slate-400">{DAY_MODE_LABELS[day.dayMode]}</div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-xs text-slate-500">糖質</div>
                    <div className="font-semibold text-neon-300">{rangeLabel(day, 'carbs')}</div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-xs text-slate-500">たんぱく質</div>
                    <div className="font-semibold text-neon-300">{rangeLabel(day, 'protein')}</div>
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
                      className="rounded border border-white/10 px-2 py-1 text-xs text-slate-200 hover:border-neon-500/50"
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
                <a className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300 hover:text-neon-300" href="https://pubmed.ncbi.nlm.nih.gov/26920240/" rel="noreferrer" target="_blank">ACSM/AND/DC</a>
                <a className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300 hover:text-neon-300" href="https://www.dietitians.ca/DietitiansOfCanada/media/Documents/Resources/noap-position-paper.pdf" rel="noreferrer" target="_blank">Position Paper PDF</a>
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
