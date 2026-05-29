import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  ReactNode
} from 'react'
import { ATHLETES, PLANS } from '../data/mock'
import { isDateKey, normalizeDateKey, useToday } from '../lib/date'
import {
  createStableId,
  defaultCheckinForAthlete,
  getCompletionFactor,
  getSportProfile,
  normalizeAthlete,
  normalizePlan
} from '../lib/appModel'
import {
  Athlete,
  AthleteDateMap,
  CompetitionEvent,
  CompetitionEventKind,
  DailyCheckin,
  DailyTotal,
  DateKey,
  DatedCheckin,
  DayMode,
  DAY_MODES,
  EventDuration,
  EventPriority,
  Plan,
  PlanPatch,
  PlanStatus,
  SportId,
  SportProfile
} from '../types'

type Totals = {
  kcal: number
  carbs: number
  protein: number
  completed: number
  partial: number
  skipped: number
}

type DateSummary = {
  date: DateKey
  planCount: number
  completedCount: number
  dayMode: DayMode
  eventCount: number
}

type ContextValue = {
  athletes: Athlete[]
  plans: Plan[]
  selectedAthleteId: string | null
  selectedAthlete: Athlete | null
  selectedSportProfile: SportProfile
  selectedDate: DateKey
  todayDateKey: DateKey
  setSelectedAthleteId: (id: string | null) => void
  setSelectedDate: (date: DateKey) => void
  availableDatesForSelected: () => DateKey[]
  dateSummariesForSelected: () => DateSummary[]
  dailyTotalsForSelected: () => DailyTotal[]
  dailyTotalsForAthlete: (athleteId: string) => DailyTotal[]
  recentCheckinsForSelected: () => DatedCheckin[]
  checkinForAthleteOnDate: (athleteId: string, date: DateKey) => DailyCheckin
  events: CompetitionEvent[]
  eventsForSelected: () => CompetitionEvent[]
  upcomingEventForSelected: () => CompetitionEvent | null
  addEvent: (event: Omit<CompetitionEvent, 'id' | 'athleteId' | 'createdAt'>) => void
  deleteEvent: (id: string) => void
  updateSelectedAthleteSport: (sportId: SportId) => void
  dayMode: DayMode
  setDayMode: (mode: DayMode) => void
  setDayModeForDate: (date: DateKey, mode: DayMode) => void
  checkin: DailyCheckin
  updateCheckin: (patch: Partial<DailyCheckin>) => void
  plansForSelected: () => Plan[]
  totalsForSelected: () => Totals
  updatePlan: (patch: PlanPatch) => void
  addPlan: (plan: Omit<Plan, 'id' | 'date'>) => void
  addPlanForDate: (date: DateKey, plan: Omit<Plan, 'id' | 'date'>) => void
  deletePlan: (id: string) => void
  setPlanStatus: (id: string, status: PlanStatus) => void
  setPlanPhoto: (id: string, photoDataUrl: string | null) => void
}

type StoredJsonResult =
  | { status: 'missing'; raw: null; parsed: null }
  | { status: 'invalid-json'; raw: string; parsed: null }
  | { status: 'ok'; raw: string; parsed: unknown }

const AthleteContext = createContext<ContextValue | undefined>(undefined)
const PLAN_STORAGE_KEY = 'plans'
const CHECKIN_STORAGE_KEY = 'athlete-checkins'
const DAY_MODE_STORAGE_KEY = 'athlete-day-modes'
const ATHLETE_STORAGE_KEY = 'athletes'
const SELECTED_ATHLETE_STORAGE_KEY = 'selected-athlete-id'
const EVENT_STORAGE_KEY = 'athlete-events'

function persistJson(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (error) {}
}

function usePersistAfterChange(key: string, value: unknown, persistInitial = false) {
  const stateRef = useRef({
    initialSnapshot: JSON.stringify(value),
    hasChanged: false
  })

  useEffect(() => {
    const snapshot = JSON.stringify(value)

    if (persistInitial && !stateRef.current.hasChanged && snapshot === stateRef.current.initialSnapshot) {
      persistJson(key, value)
      return
    }

    if (!stateRef.current.hasChanged) {
      if (snapshot === stateRef.current.initialSnapshot) {
        return
      }
      stateRef.current.hasChanged = true
    }

    persistJson(key, value)
  }, [key, persistInitial, value])
}

function warnInvalidStorage(key: string, message: string) {
  if ((import.meta as ImportMeta & { env?: { DEV?: boolean } }).env?.DEV) {
    console.warn(`[AthleteContext] ${key}: ${message}`)
  }
}

function readStoredJson(key: string): StoredJsonResult {
  const raw = localStorage.getItem(key)
  if (!raw) {
    return { status: 'missing', raw: null, parsed: null }
  }

  try {
    return { status: 'ok', raw, parsed: JSON.parse(raw) as unknown }
  } catch (error) {
    warnInvalidStorage(key, 'JSON の読み込みに失敗したため既定値へ戻します。')
    return { status: 'invalid-json', raw, parsed: null }
  }
}

function backupInvalidStorage(key: string, raw: string | null, todayDateKey: DateKey) {
  if (!raw) return

  try {
    const backupKey = `${key}:backup-${todayDateKey}`
    if (localStorage.getItem(backupKey) == null) {
      localStorage.setItem(backupKey, raw)
    }
  } catch (error) {}
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function padDatePart(value: number) {
  return String(value).padStart(2, '0')
}

function toDateKey(date: Date): DateKey {
  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())}`
}

function parseDateKey(dateKey: DateKey) {
  const [year, month, day] = dateKey.split('-').map(Number)
  return new Date(year, (month ?? 1) - 1, day ?? 1)
}

function buildRecentDateKeys(anchorDateKey: DateKey, days: number) {
  const anchor = parseDateKey(anchorDateKey)

  return Array.from({ length: days }, (_, index) => {
    const date = new Date(anchor)
    date.setDate(anchor.getDate() - (days - 1 - index))
    return toDateKey(date)
  })
}

function hasOnlyDateKeys(value: Record<string, unknown>) {
  const keys = Object.keys(value)
  return keys.length > 0 && keys.every((key) => isDateKey(key))
}

function isDailyCheckinValue(value: unknown): value is Partial<DailyCheckin> {
  if (!isRecord(value)) return false

  return (
    'sleepHours' in value ||
    'fatigue' in value ||
    'appetite' in value ||
    'weight' in value ||
    'note' in value
  )
}

function readStoredArray<T>(
  key: string,
  mapValue: (item: unknown) => T | null,
  fallback: T[],
  todayDateKey: DateKey
) {
  const stored = readStoredJson(key)
  if (stored.status === 'missing') return fallback
  if (stored.status === 'invalid-json') {
    backupInvalidStorage(key, stored.raw, todayDateKey)
    return fallback
  }
  if (!Array.isArray(stored.parsed)) {
    warnInvalidStorage(key, '配列ではない値が保存されていました。')
    backupInvalidStorage(key, stored.raw, todayDateKey)
    return fallback
  }

  return stored.parsed.reduce<T[]>((acc, item) => {
    const mapped = mapValue(item)
    if (mapped != null) {
      acc.push(mapped)
    }
    return acc
  }, [])
}

function normalizeStoredCheckin(value: unknown, athlete?: Athlete | null): DailyCheckin {
  const fallback = defaultCheckinForAthlete(athlete)
  if (!isRecord(value)) return fallback

  const sleepHours = Number(value.sleepHours)
  const fatigue = Number(value.fatigue)
  const appetite = Number(value.appetite)
  const weight = Number(value.weight)

  return {
    sleepHours: Number.isFinite(sleepHours) ? sleepHours : fallback.sleepHours,
    fatigue: Number.isFinite(fatigue) ? fatigue : fallback.fatigue,
    appetite: Number.isFinite(appetite) ? appetite : fallback.appetite,
    weight: Number.isFinite(weight) ? weight : fallback.weight,
    note: typeof value.note === 'string' ? value.note : fallback.note
  }
}

function normalizeStoredDayMode(value: unknown): DayMode {
  return DAY_MODES.includes(value as DayMode) ? (value as DayMode) : 'practice'
}

const EVENT_KINDS: CompetitionEventKind[] = ['race', 'match', 'tournament', 'performance']
const EVENT_DURATIONS: EventDuration[] = ['short', 'medium', 'long']
const EVENT_PRIORITIES: EventPriority[] = ['normal', 'key']

function normalizeStoredEvent(
  value: unknown,
  todayDateKey: DateKey,
  fallbackAthleteId?: string | null
): CompetitionEvent | null {
  if (!isRecord(value)) return null

  const athleteId = typeof value.athleteId === 'string' && value.athleteId.trim()
    ? value.athleteId.trim()
    : fallbackAthleteId
  if (!athleteId) return null

  return {
    id: typeof value.id === 'string' && value.id.trim() ? value.id.trim() : createStableId('event'),
    athleteId,
    date: normalizeDateKey(typeof value.date === 'string' ? value.date : todayDateKey, todayDateKey),
    title: typeof value.title === 'string' && value.title.trim() ? value.title.trim() : '本番',
    kind: EVENT_KINDS.includes(value.kind as CompetitionEventKind) ? (value.kind as CompetitionEventKind) : 'match',
    duration: EVENT_DURATIONS.includes(value.duration as EventDuration) ? (value.duration as EventDuration) : 'medium',
    priority: EVENT_PRIORITIES.includes(value.priority as EventPriority) ? (value.priority as EventPriority) : 'key',
    createdAt: typeof value.createdAt === 'string' && value.createdAt.trim() ? value.createdAt : new Date().toISOString()
  }
}

function readStoredCheckins(key: string, athletes: Athlete[], todayDateKey: DateKey): AthleteDateMap<DailyCheckin> {
  const stored = readStoredJson(key)
  if (stored.status === 'missing') return {}
  if (stored.status === 'invalid-json') {
    backupInvalidStorage(key, stored.raw, todayDateKey)
    return {}
  }
  if (!isRecord(stored.parsed)) {
    warnInvalidStorage(key, 'オブジェクトではない値が保存されていました。')
    backupInvalidStorage(key, stored.raw, todayDateKey)
    return {}
  }

  const athleteById = Object.fromEntries(athletes.map((athlete) => [athlete.id, athlete]))
  const next: AthleteDateMap<DailyCheckin> = {}

  for (const [athleteId, value] of Object.entries(stored.parsed)) {
    if (isRecord(value) && hasOnlyDateKeys(value)) {
      const byDate = Object.entries(value).reduce<Record<DateKey, DailyCheckin>>((acc, [dateKey, dateValue]) => {
        acc[normalizeDateKey(dateKey, todayDateKey)] = normalizeStoredCheckin(dateValue, athleteById[athleteId] ?? null)
        return acc
      }, {})

      if (Object.keys(byDate).length > 0) {
        next[athleteId] = byDate
      }
      continue
    }

    if (isDailyCheckinValue(value)) {
      next[athleteId] = {
        [todayDateKey]: normalizeStoredCheckin(value, athleteById[athleteId] ?? null)
      }
    }
  }

  return next
}

function readStoredDayModes(key: string, todayDateKey: DateKey): AthleteDateMap<DayMode> {
  const stored = readStoredJson(key)
  if (stored.status === 'missing') return {}
  if (stored.status === 'invalid-json') {
    backupInvalidStorage(key, stored.raw, todayDateKey)
    return {}
  }
  if (!isRecord(stored.parsed)) {
    warnInvalidStorage(key, 'オブジェクトではない値が保存されていました。')
    backupInvalidStorage(key, stored.raw, todayDateKey)
    return {}
  }

  const next: AthleteDateMap<DayMode> = {}

  for (const [athleteId, value] of Object.entries(stored.parsed)) {
    if (isRecord(value) && hasOnlyDateKeys(value)) {
      const byDate = Object.entries(value).reduce<Record<DateKey, DayMode>>((acc, [dateKey, dateValue]) => {
        acc[normalizeDateKey(dateKey, todayDateKey)] = normalizeStoredDayMode(dateValue)
        return acc
      }, {})

      if (Object.keys(byDate).length > 0) {
        next[athleteId] = byDate
      }
      continue
    }

    if (typeof value === 'string') {
      next[athleteId] = {
        [todayDateKey]: normalizeStoredDayMode(value)
      }
    }
  }

  return next
}

export function AthleteProvider({ children }: { children: ReactNode }){
  const todayDateKey = useToday()
  const previousTodayRef = useRef(todayDateKey)
  const shouldPersistInitialPlansRef = useRef(localStorage.getItem(PLAN_STORAGE_KEY) == null)

  const fallbackPlans = useMemo(
    () => PLANS.map((plan) => normalizePlan({ ...plan, date: todayDateKey }, { fallbackDate: todayDateKey, fallbackAthleteId: plan.athleteId }))
      .filter((plan): plan is Plan => plan != null),
    [todayDateKey]
  )

  const [athletes, setAthletes] = useState<Athlete[]>(
    () => readStoredArray(ATHLETE_STORAGE_KEY, (item) => normalizeAthlete(item as Partial<Athlete> & { sport?: string }), ATHLETES, todayDateKey)
  )
  const [plans, setPlans] = useState<Plan[]>(
    () => readStoredArray(
      PLAN_STORAGE_KEY,
      (item) => normalizePlan(item as Partial<Plan>, { fallbackDate: todayDateKey }),
      fallbackPlans,
      todayDateKey
    )
  )
  const [selectedAthleteIdState, setSelectedAthleteIdState] = useState<string | null>(() => {
    const stored = readStoredJson(SELECTED_ATHLETE_STORAGE_KEY)
    if (stored.status !== 'ok') return ATHLETES[0]?.id ?? null
    return typeof stored.parsed === 'string' ? stored.parsed : ATHLETES[0]?.id ?? null
  })
  const [selectedDate, setSelectedDateState] = useState<DateKey>(() => todayDateKey)
  const [checkins, setCheckins] = useState<AthleteDateMap<DailyCheckin>>(() => readStoredCheckins(CHECKIN_STORAGE_KEY, ATHLETES, todayDateKey))
  const [dayModes, setDayModes] = useState<AthleteDateMap<DayMode>>(() => readStoredDayModes(DAY_MODE_STORAGE_KEY, todayDateKey))
  const [events, setEvents] = useState<CompetitionEvent[]>(
    () => readStoredArray(EVENT_STORAGE_KEY, (item) => normalizeStoredEvent(item, todayDateKey), [], todayDateKey)
  )

  useEffect(() => {
    const previousToday = previousTodayRef.current
    if (selectedDate === previousToday) {
      setSelectedDateState(todayDateKey)
    }
    previousTodayRef.current = todayDateKey
  }, [selectedDate, todayDateKey])

  const selectedAthlete = useMemo(
    () => athletes.find((athlete) => athlete.id === selectedAthleteIdState) ?? athletes[0] ?? null,
    [athletes, selectedAthleteIdState]
  )
  const selectedAthleteId = selectedAthlete?.id ?? null
  const selectedSportProfile = useMemo(() => getSportProfile(selectedAthlete?.sportId), [selectedAthlete?.sportId])

  const checkin = useMemo(
    () => selectedAthlete
      ? checkins[selectedAthlete.id]?.[selectedDate] ?? defaultCheckinForAthlete(selectedAthlete)
      : defaultCheckinForAthlete(null),
    [checkins, selectedAthlete, selectedDate]
  )

  const dayMode = useMemo(
    () => selectedAthleteId ? dayModes[selectedAthleteId]?.[selectedDate] ?? 'practice' : 'practice',
    [dayModes, selectedAthleteId, selectedDate]
  )

  const selectedPlans = useMemo(
    () => plans.filter((plan) => {
      const athleteMatches = selectedAthleteId ? plan.athleteId === selectedAthleteId : true
      return athleteMatches && plan.date === selectedDate
    }),
    [plans, selectedAthleteId, selectedDate]
  )

  const totals = useMemo<Totals>(
    () => selectedPlans.reduce(
      (summary, plan) => {
        summary.kcal += plan.kcal
        summary.carbs += plan.carbs
        summary.protein += plan.protein

        if (plan.status === 'done') summary.completed += 1
        if (plan.status === 'partial') summary.partial += 1
        if (plan.status === 'skipped') summary.skipped += 1

        return summary
      },
      { kcal: 0, carbs: 0, protein: 0, completed: 0, partial: 0, skipped: 0 }
    ),
    [selectedPlans]
  )

  const availableDates = useMemo(() => {
    const dates = new Set<DateKey>([todayDateKey, selectedDate])

    if (selectedAthleteId) {
      plans
        .filter((plan) => plan.athleteId === selectedAthleteId)
        .forEach((plan) => dates.add(plan.date))

      Object.keys(checkins[selectedAthleteId] ?? {}).forEach((date) => dates.add(date))
      Object.keys(dayModes[selectedAthleteId] ?? {}).forEach((date) => dates.add(date))
      events
        .filter((event) => event.athleteId === selectedAthleteId)
        .forEach((event) => dates.add(event.date))
    }

    return Array.from(dates).sort().reverse()
  }, [checkins, dayModes, events, plans, selectedAthleteId, selectedDate, todayDateKey])

  const dateSummaries = useMemo<DateSummary[]>(() => {
    return availableDates.map((date) => {
      const plansForDate = selectedAthleteId
        ? plans.filter((plan) => plan.athleteId === selectedAthleteId && plan.date === date)
        : plans.filter((plan) => plan.date === date)

      return {
        date,
        planCount: plansForDate.length,
        completedCount: plansForDate.filter((plan) => plan.status === 'done').length,
        dayMode: selectedAthleteId ? dayModes[selectedAthleteId]?.[date] ?? 'practice' : 'practice',
        eventCount: selectedAthleteId
          ? events.filter((event) => event.athleteId === selectedAthleteId && event.date === date).length
          : events.filter((event) => event.date === date).length
      }
    })
  }, [availableDates, dayModes, events, plans, selectedAthleteId])

  const recentDateKeys = useMemo(() => buildRecentDateKeys(todayDateKey, 30), [todayDateKey])

  const buildDailyTotalsForAthlete = useCallback((athleteId: string): DailyTotal[] => {
    const athlete = athletes.find((item) => item.id === athleteId) ?? null

    return recentDateKeys.map((date) => {
      const dayPlans = plans.filter((plan) => plan.athleteId === athleteId && plan.date === date)
      const dayCheckin = checkins[athleteId]?.[date] ?? defaultCheckinForAthlete(athlete)
      const dayMode = dayModes[athleteId]?.[date] ?? 'practice'
      const completedCount = dayPlans.filter((plan) => plan.status === 'done').length

      return {
        date,
        dayMode,
        planCount: dayPlans.length,
        completedCount,
        skippedSnackCount: dayPlans.filter((plan) => plan.timing === 'Snack' && plan.status === 'skipped').length,
        plannedKcal: dayPlans.reduce((sum, plan) => sum + plan.kcal, 0),
        actualKcal: Math.round(dayPlans.reduce((sum, plan) => sum + plan.kcal * getCompletionFactor(plan.status), 0)),
        totalCarbs: Math.round(dayPlans.reduce((sum, plan) => sum + plan.carbs * getCompletionFactor(plan.status), 0)),
        totalProtein: Math.round(dayPlans.reduce((sum, plan) => sum + plan.protein * getCompletionFactor(plan.status), 0)),
        completionRate: dayPlans.length === 0 ? 0 : completedCount / dayPlans.length,
        bodyWeight: dayCheckin.weight,
        sleepHours: dayCheckin.sleepHours,
        fatigue: dayCheckin.fatigue,
        appetite: dayCheckin.appetite
      }
    })
  }, [athletes, checkins, dayModes, plans, recentDateKeys])

  const dailyTotals = useMemo<DailyTotal[]>(() => {
    if (!selectedAthleteId) return []
    return buildDailyTotalsForAthlete(selectedAthleteId)
  }, [buildDailyTotalsForAthlete, selectedAthleteId])

  const selectedEvents = useMemo(() => {
    if (!selectedAthleteId) return []

    return events
      .filter((event) => event.athleteId === selectedAthleteId)
      .sort((a, b) => a.date.localeCompare(b.date))
  }, [events, selectedAthleteId])

  const upcomingEvent = useMemo(() => {
    return selectedEvents.find((event) => event.date >= todayDateKey) ?? selectedEvents[selectedEvents.length - 1] ?? null
  }, [selectedEvents, todayDateKey])

  const recentCheckins = useMemo<DatedCheckin[]>(() => {
    if (!selectedAthleteId) return []

    return recentDateKeys.map((date) => ({
      date,
      checkin: checkins[selectedAthleteId]?.[date] ?? defaultCheckinForAthlete(selectedAthlete)
    }))
  }, [checkins, recentDateKeys, selectedAthlete, selectedAthleteId])

  usePersistAfterChange(ATHLETE_STORAGE_KEY, athletes)
  usePersistAfterChange(PLAN_STORAGE_KEY, plans, shouldPersistInitialPlansRef.current)
  usePersistAfterChange(CHECKIN_STORAGE_KEY, checkins)
  usePersistAfterChange(DAY_MODE_STORAGE_KEY, dayModes)
  usePersistAfterChange(SELECTED_ATHLETE_STORAGE_KEY, selectedAthleteId)
  usePersistAfterChange(EVENT_STORAGE_KEY, events)

  const setSelectedAthleteId = useCallback((id: string | null) => {
    setSelectedAthleteIdState(id)
  }, [])

  const setSelectedDate = useCallback((date: DateKey) => {
    setSelectedDateState(normalizeDateKey(date, todayDateKey))
  }, [todayDateKey])

  const availableDatesForSelected = useCallback(() => availableDates, [availableDates])
  const dateSummariesForSelected = useCallback(() => dateSummaries, [dateSummaries])
  const dailyTotalsForSelected = useCallback(() => dailyTotals, [dailyTotals])
  const dailyTotalsForAthlete = useCallback((athleteId: string) => buildDailyTotalsForAthlete(athleteId), [buildDailyTotalsForAthlete])
  const recentCheckinsForSelected = useCallback(() => recentCheckins, [recentCheckins])
  const checkinForAthleteOnDate = useCallback((athleteId: string, date: DateKey) => {
    const athlete = athletes.find((item) => item.id === athleteId) ?? null
    return checkins[athleteId]?.[date] ?? defaultCheckinForAthlete(athlete)
  }, [athletes, checkins])
  const eventsForSelected = useCallback(() => selectedEvents, [selectedEvents])
  const upcomingEventForSelected = useCallback(() => upcomingEvent, [upcomingEvent])
  const plansForSelected = useCallback(() => selectedPlans, [selectedPlans])
  const totalsForSelected = useCallback(() => totals, [totals])

  const addEvent = useCallback((event: Omit<CompetitionEvent, 'id' | 'athleteId' | 'createdAt'>) => {
    if (!selectedAthleteId) return

    const normalized = normalizeStoredEvent(
      {
        ...event,
        id: createStableId('event'),
        athleteId: selectedAthleteId,
        createdAt: new Date().toISOString()
      },
      todayDateKey,
      selectedAthleteId
    )

    if (!normalized) return
    setEvents((prev) => [...prev, normalized])
  }, [selectedAthleteId, todayDateKey])

  const deleteEvent = useCallback((id: string) => {
    setEvents((prev) => prev.filter((event) => event.id !== id))
  }, [])

  const updateCheckin = useCallback((patch: Partial<DailyCheckin>) => {
    if (!selectedAthleteId) return

    setCheckins((prev) => ({
      ...prev,
      [selectedAthleteId]: {
        ...(prev[selectedAthleteId] ?? {}),
        [selectedDate]: {
          ...(prev[selectedAthleteId]?.[selectedDate] ?? defaultCheckinForAthlete(selectedAthlete)),
          ...patch
        }
      }
    }))
  }, [selectedAthlete, selectedAthleteId, selectedDate])

  const updateSelectedAthleteSport = useCallback((sportId: SportId) => {
    if (!selectedAthleteId) return

    setAthletes((prev) => prev.map((athlete) => athlete.id === selectedAthleteId ? { ...athlete, sportId } : athlete))
  }, [selectedAthleteId])

  const setDayMode = useCallback((mode: DayMode) => {
    if (!selectedAthleteId) return

    setDayModes((prev) => ({
      ...prev,
      [selectedAthleteId]: {
        ...(prev[selectedAthleteId] ?? {}),
        [selectedDate]: mode
      }
    }))
  }, [selectedAthleteId, selectedDate])

  const setDayModeForDate = useCallback((date: DateKey, mode: DayMode) => {
    if (!selectedAthleteId) return

    setDayModes((prev) => ({
      ...prev,
      [selectedAthleteId]: {
        ...(prev[selectedAthleteId] ?? {}),
        [normalizeDateKey(date, todayDateKey)]: mode
      }
    }))
  }, [selectedAthleteId, todayDateKey])

  const updatePlan = useCallback((patch: PlanPatch) => {
    setPlans((prev) => prev.map((plan) => {
      if (plan.id !== patch.id) return plan

      const normalized = normalizePlan(
        { ...plan, ...patch },
        {
          fallbackDate: patch.date ?? plan.date,
          fallbackAthleteId: plan.athleteId
        }
      )

      return normalized ?? plan
    }))
  }, [])

  const addPlanForDate = useCallback((date: DateKey, plan: Omit<Plan, 'id' | 'date'>) => {
    const normalizedDate = normalizeDateKey(date, todayDateKey)
    const newPlan = normalizePlan(
      {
        ...plan,
        id: createStableId('p'),
        date: normalizedDate
      },
      {
        fallbackDate: normalizedDate,
        fallbackAthleteId: plan.athleteId
      }
    )

    if (!newPlan) return
    setPlans((prev) => [...prev, newPlan])
  }, [todayDateKey])

  const addPlan = useCallback((plan: Omit<Plan, 'id' | 'date'>) => {
    addPlanForDate(selectedDate, plan)
  }, [addPlanForDate, selectedDate])

  const deletePlan = useCallback((id: string) => {
    setPlans((prev) => prev.filter((plan) => plan.id !== id))
  }, [])

  const setPlanStatus = useCallback((id: string, status: PlanStatus) => {
    setPlans((prev) => prev.map((plan) => plan.id === id ? { ...plan, status } : plan))
  }, [])

  const setPlanPhoto = useCallback((id: string, photoDataUrl: string | null) => {
    setPlans((prev) => prev.map((plan) => {
      if (plan.id !== id) return plan
      if (photoDataUrl) return { ...plan, photoDataUrl }

      const { photoDataUrl: _photoDataUrl, ...planWithoutPhoto } = plan
      return planWithoutPhoto
    }))
  }, [])

  const value = useMemo<ContextValue>(() => ({
    athletes,
    plans,
    selectedAthleteId,
    selectedAthlete,
    selectedSportProfile,
    selectedDate,
    todayDateKey,
    setSelectedAthleteId,
    setSelectedDate,
    availableDatesForSelected,
    dateSummariesForSelected,
    dailyTotalsForSelected,
    dailyTotalsForAthlete,
    recentCheckinsForSelected,
    checkinForAthleteOnDate,
    events,
    eventsForSelected,
    upcomingEventForSelected,
    addEvent,
    deleteEvent,
    updateSelectedAthleteSport,
    dayMode,
    setDayMode,
    setDayModeForDate,
    checkin,
    updateCheckin,
    plansForSelected,
    totalsForSelected,
    updatePlan,
    addPlan,
    addPlanForDate,
    deletePlan,
    setPlanStatus,
    setPlanPhoto
  }), [
    athletes,
    plans,
    selectedAthleteId,
    selectedAthlete,
    selectedSportProfile,
    selectedDate,
    todayDateKey,
    setSelectedAthleteId,
    setSelectedDate,
    availableDatesForSelected,
    dateSummariesForSelected,
    dailyTotalsForSelected,
    dailyTotalsForAthlete,
    recentCheckinsForSelected,
    checkinForAthleteOnDate,
    events,
    eventsForSelected,
    upcomingEventForSelected,
    addEvent,
    deleteEvent,
    updateSelectedAthleteSport,
    dayMode,
    setDayMode,
    setDayModeForDate,
    checkin,
    updateCheckin,
    plansForSelected,
    totalsForSelected,
    updatePlan,
    addPlan,
    addPlanForDate,
    deletePlan,
    setPlanStatus,
    setPlanPhoto
  ])

  return <AthleteContext.Provider value={value}>{children}</AthleteContext.Provider>
}

export function useAthlete(){
  const ctx = useContext(AthleteContext)
  if (!ctx) throw new Error('useAthlete must be used within AthleteProvider')
  return ctx
}
