import { useEffect, useState } from 'react'
import { DateKey } from '../types'

function pad(value: number) {
  return String(value).padStart(2, '0')
}

export function getTodayDateKey(now = new Date()): DateKey {
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

export function isDateKey(value: unknown): value is DateKey {
  return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
}

export function normalizeDateKey(value: unknown, fallback = getTodayDateKey()): DateKey {
  if (!isDateKey(value)) return fallback
  return value
}

export function formatDateLabel(dateKey: DateKey) {
  const [year, month, day] = dateKey.split('-').map(Number)
  const date = new Date(year, (month ?? 1) - 1, day ?? 1)

  if (Number.isNaN(date.getTime())) {
    return dateKey
  }

  return new Intl.DateTimeFormat('ja-JP', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  }).format(date)
}

export function useToday(intervalMs = 60_000) {
  const [today, setToday] = useState<DateKey>(() => getTodayDateKey())

  useEffect(() => {
    const timerId = window.setInterval(() => {
      const next = getTodayDateKey()
      setToday((current) => current === next ? current : next)
    }, intervalMs)

    return () => window.clearInterval(timerId)
  }, [intervalMs])

  return today
}
