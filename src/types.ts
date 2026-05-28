export type Athlete = {
  id: string
  name: string
  sportId: SportId
  focus: string
  baselineWeight: number
}

export type SportId =
  | 'track'
  | 'baseball'
  | 'soccer'
  | 'ballet'
  | 'basketball'
  | 'golf'
  | 'swimming'
  | 'table_tennis'

export type DayMode = 'normal' | 'practice' | 'pre_game' | 'game' | 'recovery'
export type DateKey = string

export type CompetitionEventKind = 'race' | 'match' | 'tournament' | 'performance'
export type EventDuration = 'short' | 'medium' | 'long'
export type EventPriority = 'normal' | 'key'

export type CompetitionEvent = {
  id: string
  athleteId: string
  date: DateKey
  title: string
  kind: CompetitionEventKind
  duration: EventDuration
  priority: EventPriority
  createdAt: string
}

export type MealSlot = 'Breakfast' | 'Lunch' | 'Snack' | 'Dinner'

export type PlanStatus = 'planned' | 'partial' | 'done' | 'skipped'

export type Plan = {
  id: string
  athleteId: string
  date: DateKey
  title: string
  timing: MealSlot
  kcal: number
  carbs: number
  protein: number
  status: PlanStatus
  photoDataUrl?: string
}

export type PlanPatch = Pick<Plan, 'id'> & Partial<Omit<Plan, 'id'>>
export type SnackRole = 'pre_workout' | 'post_workout' | 'between_games' | 'general'

export type DailyTotal = {
  date: DateKey
  dayMode: DayMode
  planCount: number
  completedCount: number
  skippedSnackCount: number
  plannedKcal: number
  actualKcal: number
  totalCarbs: number
  totalProtein: number
  completionRate: number
  bodyWeight: number
  sleepHours: number
  fatigue: number
  appetite: number
}

export type DatedCheckin = {
  date: DateKey
  checkin: DailyCheckin
}

export type EventFuelingDay = {
  date: DateKey
  offset: number
  label: string
  dayMode: DayMode
  carbsPerKg: MacroRange
  proteinPerKg: MacroRange
  carbs: MacroRange
  protein: MacroRange
  fatigue: number
  sleepHours: number
  appetite: number
  focus: string
  hydration: string
  timing: string
  evidence: string[]
  adjustments: string[]
}

export type EditablePlan = Omit<Partial<Plan>, 'athleteId'> & {
  athleteId?: string | null
}

export type DailyCheckin = {
  sleepHours: number
  fatigue: number
  appetite: number
  weight: number
  note: string
}

export type AthleteDateMap<T> = Record<string, Record<DateKey, T>>

export type MacroRange = {
  min: number
  max: number
}

export type EvidenceSource = {
  label: string
  title: string
  url: string
}

export type SportProfile = {
  id: SportId
  label: string
  category: string
  summary: string
  carbTargets: Record<DayMode, MacroRange>
  proteinTarget: MacroRange
  focusNutrients: string[]
  hydrationNote: string
  cautionNote: string
  fuelingNote: string
  references: EvidenceSource[]
}

export const DAY_MODES: DayMode[] = ['normal', 'practice', 'pre_game', 'game', 'recovery']

export const DAY_MODE_LABELS: Record<DayMode, string> = {
  normal: '通常日',
  practice: '練習日',
  pre_game: '試合前日',
  game: '試合当日',
  recovery: '回復日'
}

export const DAY_MODE_HINTS: Record<DayMode, string> = {
  normal: '普段のバランスを整える日',
  practice: '練習量に合わせて補食を厚くする日',
  pre_game: '消化に配慮しつつエネルギーをためる日',
  game: '本番前後の補給を外さない日',
  recovery: '疲労回復を優先する日'
}

export const MEAL_SLOTS: MealSlot[] = ['Breakfast', 'Lunch', 'Snack', 'Dinner']

export const MEAL_SLOT_LABELS: Record<MealSlot, string> = {
  Breakfast: '朝食',
  Lunch: '昼食',
  Snack: '補食',
  Dinner: '夕食'
}

export const PLAN_STATUSES: PlanStatus[] = ['planned', 'partial', 'done', 'skipped']

export const PLAN_STATUS_LABELS: Record<PlanStatus, string> = {
  planned: '未実施',
  partial: '一部だけ',
  done: '完了',
  skipped: 'スキップ'
}

export const COMPETITION_EVENT_KIND_LABELS: Record<CompetitionEventKind, string> = {
  race: 'レース',
  match: '試合',
  tournament: '大会',
  performance: '本番'
}

export const EVENT_DURATION_LABELS: Record<EventDuration, string> = {
  short: '60分未満',
  medium: '60-90分',
  long: '90分以上'
}

export const EVENT_PRIORITY_LABELS: Record<EventPriority, string> = {
  normal: '通常',
  key: '重要'
}
