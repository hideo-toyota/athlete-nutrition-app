import React, { useEffect, useMemo, useState } from 'react'
import { DateKey, DAY_MODE_LABELS, DayMode } from '../types'
import { formatDateLabel, getTodayDateKey } from '../lib/date'

type DateSummary = {
  date: DateKey
  planCount: number
  completedCount: number
  dayMode: DayMode
  eventCount?: number
}

type Props = {
  selectedDate: DateKey
  todayDateKey: DateKey
  summaries: DateSummary[]
  onSelectDate: (date: DateKey) => void
}

const modeTone: Record<DayMode, string> = {
  normal: 'bg-slate-400',
  practice: 'bg-neon-500',
  pre_game: 'bg-amber-300',
  game: 'bg-rose-300',
  recovery: 'bg-emerald-300'
}

function pad(value: number) {
  return String(value).padStart(2, '0')
}

function toDateKey(date: Date): DateKey {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function parseDateKey(dateKey: DateKey) {
  const [year, month, day] = dateKey.split('-').map(Number)
  return new Date(year, (month ?? 1) - 1, day ?? 1)
}

function formatMonthLabel(date: Date) {
  return new Intl.DateTimeFormat('ja-JP', {
    year: 'numeric',
    month: 'long'
  }).format(date)
}

function buildMonthDays(viewMonth: Date) {
  const first = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), 1)
  const start = new Date(first)
  start.setDate(first.getDate() - first.getDay())

  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    return {
      date,
      dateKey: toDateKey(date),
      inMonth: date.getMonth() === viewMonth.getMonth()
    }
  })
}

export default function CalendarPanel({
  selectedDate,
  todayDateKey,
  summaries,
  onSelectDate
}: Props) {
  const [viewMonth, setViewMonth] = useState(() => parseDateKey(selectedDate))
  const summaryByDate = useMemo(() => new Map(summaries.map((summary) => [summary.date, summary])), [summaries])
  const monthDays = useMemo(() => buildMonthDays(viewMonth), [viewMonth])
  const selectedMonth = formatMonthLabel(viewMonth)
  const todayMonth = parseDateKey(todayDateKey || getTodayDateKey())
  const isViewingTodayMonth = viewMonth.getFullYear() === todayMonth.getFullYear() && viewMonth.getMonth() === todayMonth.getMonth()

  useEffect(() => {
    const next = parseDateKey(selectedDate)
    setViewMonth((current) => {
      if (current.getFullYear() === next.getFullYear() && current.getMonth() === next.getMonth()) {
        return current
      }
      return next
    })
  }, [selectedDate])

  const moveMonth = (offset: number) => {
    setViewMonth((current) => new Date(current.getFullYear(), current.getMonth() + offset, 1))
  }

  const selectToday = () => {
    const today = todayDateKey || getTodayDateKey()
    setViewMonth(parseDateKey(today))
    onSelectDate(today)
  }

  return (
    <div className="glass rounded-xl p-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="font-semibold">Calendar</h3>
          <div className="mt-1 text-sm text-slate-300">{selectedMonth}</div>
          <div className="text-sm text-slate-400">{formatDateLabel(selectedDate)} の記録</div>
        </div>
        <div className="flex items-center gap-2">
          <button className="rounded border border-white/10 px-3 py-2 text-sm text-slate-300" onClick={() => moveMonth(-1)} type="button">Prev</button>
          <div className="min-w-[120px] text-center text-sm text-slate-300">{selectedMonth}</div>
          <button className="rounded border border-white/10 px-3 py-2 text-sm text-slate-300" onClick={() => moveMonth(1)} type="button">Next</button>
          <button
            className="rounded border border-white/10 px-3 py-2 text-sm text-slate-300 disabled:opacity-40"
            disabled={selectedDate === todayDateKey && isViewingTodayMonth}
            onClick={selectToday}
            type="button"
          >
            Today
          </button>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-7 gap-1 text-center text-xs text-slate-500">
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
          <div key={day} className="py-1">{day}</div>
        ))}
      </div>

      <div className="mt-1 grid grid-cols-7 gap-1">
        {monthDays.map(({ date, dateKey, inMonth }) => {
          const summary = summaryByDate.get(dateKey)
          const isSelected = dateKey === selectedDate
          const isToday = dateKey === todayDateKey

          return (
            <button
              key={dateKey}
              aria-label={`select ${dateKey}`}
              className={`min-h-[58px] rounded-lg border p-2 text-left transition-colors ${isSelected ? 'border-neon-500/60 bg-neon-500/10' : 'border-white/10 bg-[rgba(255,255,255,0.02)]'} ${inMonth ? 'text-slate-200' : 'text-slate-600'}`}
              onClick={() => onSelectDate(dateKey)}
              type="button"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs">{date.getDate()}</span>
                {isToday && <span className="h-2 w-2 rounded-full bg-neon-500" />}
              </div>
              {summary && (
                <div className="mt-2 space-y-1">
                  <div className={`h-1.5 w-8 rounded-full ${modeTone[summary.dayMode]}`} title={DAY_MODE_LABELS[summary.dayMode]} />
                  <div className="flex items-center justify-between gap-1 text-[10px] text-slate-400">
                    <span>{summary.completedCount}/{summary.planCount}</span>
                    {(summary.eventCount ?? 0) > 0 && <span className="rounded-full bg-rose-300/20 px-1 text-rose-200">本番</span>}
                  </div>
                </div>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
