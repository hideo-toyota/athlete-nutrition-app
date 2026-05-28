import { SPORT_PROFILES } from '../data/sportProfiles'
import {
  Athlete,
  CompetitionEvent,
  DateKey,
  DailyCheckin,
  DailyTotal,
  DatedCheckin,
  DayMode,
  DAY_MODE_LABELS,
  EventFuelingDay,
  MacroRange,
  MealSlot,
  MEAL_SLOT_LABELS,
  Plan,
  PlanStatus,
  PLAN_STATUS_LABELS,
  SnackRole,
  SportId,
  SportProfile
} from '../types'
import { normalizeDateKey } from './date'

type CoachComment = {
  title: string
  body: string
  tone: 'info' | 'warn' | 'good'
}

type NormalizePlanOptions = {
  fallbackDate?: DateKey
  fallbackAthleteId?: string | null
}

let localIdCounter = 0

function getRandomHex(bytes = 16) {
  if (!globalThis.crypto?.getRandomValues) return null

  const buffer = new Uint8Array(bytes)
  globalThis.crypto.getRandomValues(buffer)
  return Array.from(buffer, (value) => value.toString(16).padStart(2, '0')).join('')
}

export function createStableId(prefix: string) {
  const uuid = globalThis.crypto?.randomUUID?.()
  if (uuid) return `${prefix}_${uuid}`

  const randomHex = getRandomHex(16)
  if (randomHex) return `${prefix}_${randomHex}`

  localIdCounter += 1
  return `${prefix}_${Date.now().toString(36)}_${localIdCounter.toString(36)}`
}

export function defaultCheckinForAthlete(athlete?: Athlete | null): DailyCheckin {
  return {
    sleepHours: 7.5,
    fatigue: 2,
    appetite: 4,
    weight: athlete?.baselineWeight ?? 60,
    note: ''
  }
}

const SPORT_ALIASES: Record<string, SportId> = {
  track: 'track',
  running: 'track',
  baseball: 'baseball',
  soccer: 'soccer',
  football: 'soccer',
  ballet: 'ballet',
  basketball: 'basketball',
  golf: 'golf',
  swimming: 'swimming',
  table_tennis: 'table_tennis',
  'table tennis': 'table_tennis',
  pingpong: 'table_tennis'
}

export function getSportProfile(sportId?: SportId | null): SportProfile {
  return SPORT_PROFILES.find((profile) => profile.id === sportId) ?? SPORT_PROFILES[0]
}

export function normalizeAthlete(raw: Partial<Athlete> & { sport?: string; sportId?: SportId }): Athlete {
  const rawSport = raw.sportId ?? SPORT_ALIASES[String(raw.sport ?? '').toLowerCase()] ?? 'track'
  const profile = getSportProfile(rawSport)

  return {
    id: raw.id ?? createStableId('a'),
    name: raw.name ?? 'Athlete',
    sportId: rawSport,
    focus: raw.focus ?? profile.summary,
    baselineWeight: Number(raw.baselineWeight ?? 60)
  }
}

function guessTimingFromTitle(title: string): MealSlot {
  const lower = title.toLowerCase()

  if (lower.includes('morning') || lower.includes('breakfast')) return 'Breakfast'
  if (lower.includes('lunch') || lower.includes('bowl')) return 'Lunch'
  if (lower.includes('recovery') || lower.includes('pre-workout') || lower.includes('snack')) return 'Snack'
  return 'Dinner'
}

function normalizeAthleteId(value: unknown, fallback?: string | null) {
  if (typeof value === 'string' && value.trim()) return value.trim()
  if (typeof fallback === 'string' && fallback.trim()) return fallback.trim()
  return null
}

export function normalizePlan(
  raw: Partial<Plan> & { athleteId?: string | null; title?: string; date?: string },
  options: NormalizePlanOptions = {}
): Plan | null {
  const athleteId = normalizeAthleteId(raw.athleteId, options.fallbackAthleteId)
  if (!athleteId) return null

  const kcal = Number(raw.kcal ?? 0)

  return {
    id: raw.id ?? createStableId('p'),
    athleteId,
    date: normalizeDateKey(raw.date, options.fallbackDate),
    title: raw.title ?? 'Untitled Plan',
    timing: raw.timing ?? guessTimingFromTitle(raw.title ?? ''),
    kcal,
    carbs: Number(raw.carbs ?? Math.max(20, Math.round(kcal / 10))),
    protein: Number(raw.protein ?? 0),
    status: raw.status ?? 'planned',
    photoDataUrl: typeof raw.photoDataUrl === 'string' ? raw.photoDataUrl : undefined
  }
}

export function getCompletionFactor(status: PlanStatus): number {
  if (status === 'done') return 1
  if (status === 'partial') return 0.5
  return 0
}

export function getDailyTargets(profile: SportProfile, dayMode: DayMode, bodyWeight: number) {
  const safeWeight = Number.isFinite(bodyWeight) && bodyWeight > 0 ? bodyWeight : 60
  const carbs = profile.carbTargets[dayMode]

  return {
    carbs: {
      min: Math.round(carbs.min * safeWeight),
      max: Math.round(carbs.max * safeWeight)
    },
    protein: {
      min: Math.round(profile.proteinTarget.min * safeWeight),
      max: Math.round(profile.proteinTarget.max * safeWeight)
    }
  }
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

export function addDaysToDateKey(dateKey: DateKey, days: number): DateKey {
  const date = parseDateKey(dateKey)
  date.setDate(date.getDate() + days)
  return toDateKey(date)
}

export function getDaysBetweenDateKeys(fromDateKey: DateKey, toDateKey: DateKey) {
  const from = parseDateKey(fromDateKey)
  const to = parseDateKey(toDateKey)
  const msPerDay = 24 * 60 * 60 * 1000
  return Math.round((to.getTime() - from.getTime()) / msPerDay)
}

function clampRange(range: MacroRange, minFloor: number, maxCeiling = 12): MacroRange {
  return {
    min: Math.min(maxCeiling, Math.max(range.min, minFloor)),
    max: Math.min(maxCeiling, Math.max(range.max, minFloor))
  }
}

function rangeToGrams(range: MacroRange, bodyWeight: number): MacroRange {
  return {
    min: Math.round(range.min * bodyWeight),
    max: Math.round(range.max * bodyWeight)
  }
}

function eventDayMode(offset: number): DayMode {
  if (offset === 0) return 'game'
  if (offset === 1) return 'recovery'
  if (offset >= -3 && offset <= -1) return 'pre_game'
  return 'practice'
}

function eventFuelingLabel(offset: number) {
  if (offset === 0) return '本番当日'
  if (offset === 1) return '翌日回復'
  if (offset === -1) return '前日調整'
  if (offset >= -3) return 'カーボローディング'
  return '土台作り'
}

function eventCarbRange(profile: SportProfile, event: CompetitionEvent, dayMode: DayMode, offset: number): MacroRange {
  const sportRange = profile.carbTargets[dayMode]

  if (offset >= -3 && offset <= -1) {
    if (event.duration === 'long') return { min: Math.max(sportRange.min, 7), max: Math.max(sportRange.max, 12) }
    if (event.duration === 'medium') return { min: Math.max(sportRange.min, 6), max: Math.max(sportRange.max, 10) }
    return clampRange(sportRange, profile.carbTargets.pre_game.min, 8)
  }

  if (offset === 0) {
    if (event.duration === 'long') return clampRange(sportRange, 6, 10)
    if (event.duration === 'medium') return clampRange(sportRange, 5, 8)
  }

  return sportRange
}

function eventProteinRange(profile: SportProfile, dayMode: DayMode, checkin: DailyCheckin): MacroRange {
  const recoveryFloor = dayMode === 'recovery' || checkin.fatigue >= 4 ? 1.6 : profile.proteinTarget.min

  return {
    min: Math.max(profile.proteinTarget.min, recoveryFloor),
    max: profile.proteinTarget.max
  }
}

function buildEventFocus({
  profile,
  event,
  offset,
  checkin
}: {
  profile: SportProfile
  event: CompetitionEvent
  offset: number
  checkin: DailyCheckin
}) {
  if (offset === 0) {
    return event.duration === 'long'
      ? '本番1-4時間前に消化の軽い糖質を入れ、60分を超える場合は競技中も30-60g/hを目安に補給します。'
      : '本番1-4時間前に食べ慣れた糖質を入れ、胃腸の不安が出る新しい食品は避けます。'
  }

  if (offset === 1) {
    return '糖質とたんぱく質を戻し、体重減少がある場合は水分を段階的に補います。'
  }

  if (offset >= -3 && offset <= -1) {
    return event.duration === 'short'
      ? '満腹で動きが重くならない範囲で、主食を少し厚くして本番前のエネルギー切れを防ぎます。'
      : '練習量を落としながら主食を増やし、脂質と食物繊維は控えめにして筋グリコーゲンを高めます。'
  }

  if (checkin.fatigue >= 4) {
    return '疲労感が高いので、練習前後の糖質を分割し、回復食を先に固定します。'
  }

  return `${profile.label}の通常練習を支える日です。体重あたりの糖質・たんぱく質を外さず、補食の時間を固定します。`
}

function buildEventHydration(offset: number, checkin: DailyCheckin, profile: SportProfile) {
  if (offset === 1) {
    return '本番後は体重減少1kgあたり1.25-1.5Lを目安に、ナトリウムを含む飲料や食事で戻します。'
  }

  if (offset === 0) {
    return `${profile.hydrationNote} のどの渇きだけでなく、尿色や体重変化も確認します。`
  }

  if (checkin.fatigue >= 4 || checkin.sleepHours < 6.5) {
    return '疲労・睡眠不足がある日は、脱水で体感負荷が上がりやすいため、朝から少量ずつ補水します。'
  }

  return profile.hydrationNote
}

export function buildEventFuelingPlan({
  event,
  athlete,
  profile,
  todayDateKey,
  fallbackCheckin,
  getCheckinForDate
}: {
  event: CompetitionEvent
  athlete: Athlete | null
  profile: SportProfile
  todayDateKey: DateKey
  fallbackCheckin: DailyCheckin
  getCheckinForDate?: (date: DateKey) => DailyCheckin
}): EventFuelingDay[] {
  const baseWeight = Number.isFinite(fallbackCheckin.weight) && fallbackCheckin.weight > 0
    ? fallbackCheckin.weight
    : athlete?.baselineWeight ?? 60

  return Array.from({ length: 8 }, (_, index) => index - 6).map((offset) => {
    const date = addDaysToDateKey(event.date, offset)
    const dayMode = eventDayMode(offset)
    const checkin = getCheckinForDate?.(date) ?? fallbackCheckin
    const safeWeight = Number.isFinite(checkin.weight) && checkin.weight > 0 ? checkin.weight : baseWeight
    const fatigueBoost = checkin.fatigue >= 4 ? (checkin.appetite <= 2 ? 0.25 : 0.5) : checkin.fatigue >= 3 ? 0.25 : 0
    const baseCarbs = eventCarbRange(profile, event, dayMode, offset)
    const carbsPerKg = {
      min: Math.min(12, Number((baseCarbs.min + fatigueBoost).toFixed(1))),
      max: Math.min(12, Number((baseCarbs.max + (checkin.fatigue >= 4 ? 0.5 : 0)).toFixed(1)))
    }
    const proteinPerKg = eventProteinRange(profile, dayMode, checkin)
    const adjustments = [
      checkin.fatigue >= 4 ? `疲労 ${checkin.fatigue}/5: 糖質下限を+${fatigueBoost}g/kg補正` : null,
      checkin.sleepHours < 6.5 ? `睡眠 ${checkin.sleepHours.toFixed(1)}h: 補食を小分けにして回復優先` : null,
      checkin.appetite <= 2 ? `食欲 ${checkin.appetite}/5: ゼリー・ヨーグルト・おにぎりなど軽い形で達成` : null
    ].filter((item): item is string => Boolean(item))

    return {
      date,
      offset,
      label: eventFuelingLabel(offset),
      dayMode,
      carbsPerKg,
      proteinPerKg,
      carbs: rangeToGrams(carbsPerKg, safeWeight),
      protein: rangeToGrams(proteinPerKg, safeWeight),
      fatigue: checkin.fatigue,
      sleepHours: checkin.sleepHours,
      appetite: checkin.appetite,
      focus: buildEventFocus({ profile, event, offset, checkin }),
      hydration: buildEventHydration(offset, checkin, profile),
      timing: offset === 0 ? '1-4時間前 + 必要なら競技中' : offset >= -3 && offset <= -1 ? '3食 + 補食で分割' : '練習前後を固定',
      adjustments,
      evidence: [
        'ACSM/AND/DC 2016',
        '体重 x g/kg/day',
        event.duration === 'long' && offset >= -3 && offset <= -1 ? '7-12g/kg カーボローディング' : '競技別糖質レンジ',
        '疲労・睡眠・食欲で補正'
      ]
    }
  })
}

export function getConvenienceSuggestions(timing: MealSlot, dayMode: DayMode, sportId: SportId, snackRole: SnackRole = 'general'): string[] {
  const base: Record<MealSlot, string[]> = {
    Breakfast: ['おにぎり + ギリシャヨーグルト', '全粒粉サンド + バナナ', '豆乳 + ゆで卵 + カステラ'],
    Lunch: ['サラダチキン丼 + 味噌汁', '鮭おにぎり2個 + 野菜スープ', 'そば + 豆腐バー'],
    Snack: ['エネルギーゼリー + バナナ', 'どら焼き + プロテインドリンク', 'あんぱん + 飲むヨーグルト'],
    Dinner: ['焼き魚弁当 + 具沢山スープ', 'チキンパスタ + サラダ', '親子丼 + カップ味噌汁']
  }

  const modeBoost: Record<DayMode, string | null> = {
    normal: null,
    practice: 'スポーツドリンク 500ml',
    pre_game: '塩むすび + 経口補水ドリンク',
    game: '吸収の早いゼリー飲料',
    recovery: '高たんぱくミルク'
  }

  const snackRoleBoost: Record<SnackRole, string[]> = {
    pre_workout: ['バナナ + エネルギーゼリー', '塩むすび + 水'],
    post_workout: ['プロテインドリンク + おにぎり', 'リカバリーゼリー + 飲むヨーグルト'],
    between_games: ['ミニ羊羹 + 経口補水ドリンク', 'カステラ + 水'],
    general: []
  }

  const sportBoost: Record<SportId, Partial<Record<MealSlot, string[]>>> = {
    track: {
      Snack: ['おにぎり + スポーツドリンク', 'バナナ + エネルギーゼリー'],
      Dinner: ['鶏むねパスタ + オレンジジュース']
    },
    baseball: {
      Snack: ['ツナおにぎり + 塩タブレット', 'バナナ + プロテインミルク'],
      Lunch: ['そぼろ丼 + カップ味噌汁']
    },
    soccer: {
      Breakfast: ['白米おにぎり + ヨーグルト + 果汁100%ジュース'],
      Snack: ['バナナ + ゼリー飲料', 'あんぱん + スポーツドリンク']
    },
    ballet: {
      Breakfast: ['ヨーグルト + バナナ + シリアル', '鮭おにぎり + 豆乳'],
      Dinner: ['鮭弁当 + 牛乳', '鶏そぼろ丼 + 小松菜サラダ']
    },
    basketball: {
      Snack: ['どら焼き + スポーツドリンク', 'ゼリー飲料 + バナナ'],
      Dinner: ['チキンオーバーライス + スープ']
    },
    golf: {
      Breakfast: ['サンドイッチ + バナナ', 'おにぎり2個 + ヨーグルト'],
      Snack: ['ミニ羊羹 + 水', 'バナナ + 小型ゼリー']
    },
    swimming: {
      Breakfast: ['ベーグル + ミルク + バナナ', 'おにぎり2個 + 飲むヨーグルト'],
      Snack: ['リカバリーゼリー + プロテインドリンク']
    },
    table_tennis: {
      Snack: ['一口ゼリー + バナナ', '飲むヨーグルト + カステラ'],
      Lunch: ['鮭おにぎり + サラダチキン']
    }
  }

  const options = [
    ...(timing === 'Snack' ? snackRoleBoost[snackRole] : []),
    ...(sportBoost[sportId][timing] ?? []),
    ...base[timing]
  ]

  if (timing === 'Snack' && modeBoost[dayMode]) {
    options.unshift(modeBoost[dayMode] as string)
  }

  return Array.from(new Set(options)).slice(0, 3)
}

function average(values: number[]) {
  if (values.length === 0) return 0
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

function allMealsDone(day: DailyTotal) {
  return day.planCount > 0 && day.completedCount === day.planCount
}

function buildSportIncompleteMessage(sportId: SportId) {
  const messages: Record<SportId, string> = {
    track: '持久・スピード系では実行率の低下がエネルギー切れに直結します。',
    soccer: '高強度反復系では後半のスプリント維持に影響します。',
    ballet: 'リハーサル前後の補食が抜けると、後半のテクニカル精度が落ちやすいです。',
    basketball: '連戦や高強度練習ではグリコーゲン回復の窓を逃しやすいです。',
    swimming: '二部練の間隔が短い日は、補給の遅れが回復に響きます。',
    golf: '長時間ラウンドでは血糖の落ち込みが集中力に直結します。',
    table_tennis: '複数試合の間に補食を入れる方が、終盤の判断が安定します。',
    baseball: 'ベンチでの少量補食を入れる癖をつけると、長い試合でも崩れにくいです。'
  }

  return messages[sportId]
}

export function buildCoachComments({
  athlete,
  dayMode,
  plans,
  checkin,
  todayDateKey,
  upcomingEvent = null,
  eventFuelingDays = [],
  recentDailyTotals = [],
  recentCheckins = []
}: {
  athlete: Athlete | null
  dayMode: DayMode
  plans: Plan[]
  checkin: DailyCheckin
  todayDateKey?: DateKey
  upcomingEvent?: CompetitionEvent | null
  eventFuelingDays?: EventFuelingDay[]
  recentDailyTotals?: DailyTotal[]
  recentCheckins?: DatedCheckin[]
}): CoachComment[] {
  const profile = getSportProfile(athlete?.sportId)
  const targets = getDailyTargets(profile, dayMode, checkin.weight)
  const comments: CoachComment[] = []
  const plannedKcal = plans.reduce((sum, plan) => sum + plan.kcal, 0)
  const actualKcal = plans.reduce((sum, plan) => sum + plan.kcal * getCompletionFactor(plan.status), 0)
  const totalProtein = plans.reduce((sum, plan) => sum + plan.protein, 0)
  const totalCarbs = plans.reduce((sum, plan) => sum + plan.carbs, 0)
  const incomplete = plans.filter((plan) => plan.status === 'planned' || plan.status === 'skipped')
  const skippedSnack = plans.some((plan) => plan.timing === 'Snack' && plan.status === 'skipped')
  const recentWithPlans = recentDailyTotals.filter((day) => day.planCount > 0)
  const recent7 = recentWithPlans.slice(-7)
  const recent14 = recentWithPlans.slice(-14)
  const recent5 = recentWithPlans.slice(-5)
  const last3 = recentWithPlans.slice(-3)
  const checkins7 = recentCheckins.slice(-7)
  const checkins14 = recentCheckins.slice(-14)
  const fatigueAverage7 = average(checkins7.map(({ checkin: item }) => item.fatigue))
  const sleepAverage7 = average(checkins7.map(({ checkin: item }) => item.sleepHours))
  const completionAverage7 = average(recent7.map((day) => day.completionRate))
  const skippedSnacks5 = recent5.reduce((sum, day) => sum + day.skippedSnackCount, 0)
  const firstWeight14 = checkins14[0]?.checkin.weight
  const latestWeight14 = checkins14[checkins14.length - 1]?.checkin.weight
  const weightDiff14 = typeof firstWeight14 === 'number' && typeof latestWeight14 === 'number' && Number.isFinite(firstWeight14) && Number.isFinite(latestWeight14)
    ? Number((latestWeight14 - firstWeight14).toFixed(1))
    : 0
  const threeDayCarbShortfall = last3.length === 3 && last3.every((day) => {
    const dayTargets = getDailyTargets(profile, day.dayMode, day.bodyWeight)
    return day.totalCarbs < dayTargets.carbs.min
  })
  const threeDayAllDone = last3.length === 3 && last3.every(allMealsDone)

  if (upcomingEvent && todayDateKey && eventFuelingDays.length > 0) {
    const daysUntil = getDaysBetweenDateKeys(todayDateKey, upcomingEvent.date)
    const todayFueling = eventFuelingDays.find((day) => day.date === todayDateKey)
      ?? eventFuelingDays.find((day) => day.offset <= 0)
      ?? eventFuelingDays[0]
    const isLoadingWindow = daysUntil >= 1 && daysUntil <= 3

    comments.push({
      title: `本番まであと${daysUntil}日`,
      body: `${upcomingEvent.title}に向けて、今日の目安は糖質 ${todayFueling.carbs.min}-${todayFueling.carbs.max}g（${todayFueling.carbsPerKg.min}-${todayFueling.carbsPerKg.max}g/kg）、たんぱく質 ${todayFueling.protein.min}-${todayFueling.protein.max}g です。${isLoadingWindow ? 'カーボローディング期なので、主食を分割して増やし、脂質と食物繊維は控えめにします。' : '体重・疲労感・食欲を見ながら、練習前後の補給を固定しましょう。'}`,
      tone: isLoadingWindow || checkin.fatigue >= 4 ? 'warn' : 'info'
    })
  }

  if (plans.length === 0) return comments.slice(0, 4)

  if (recent7.length >= 5) {
    comments.push({
      title: '過去7日の流れ',
      body: `過去7日の実行率は平均 ${Math.round(completionAverage7 * 100)}%、疲労平均は ${fatigueAverage7.toFixed(1)}/5 です。今日だけでなく、この1週間の傾向を見ながら補食と回復を調整しましょう。`,
      tone: completionAverage7 >= 0.8 ? 'good' : fatigueAverage7 >= 3.5 ? 'warn' : 'info'
    })
  }

  if (fatigueAverage7 >= 3.5) {
    comments.push({
      title: 'この1週間、疲労感が高めです',
      body: '過去7日の疲労感が高い状態です。回復日の補食・水分・睡眠時間を優先し、練習日は消化の軽い補給に寄せましょう。',
      tone: 'warn'
    })
  }

  if (threeDayCarbShortfall) {
    comments.push({
      title: '3日連続で糖質が不足しています',
      body: '3日連続で糖質ターゲットを下回っています。主食量と練習前後の補食を見直すタイミングです。',
      tone: 'warn'
    })
  }

  if (checkins14.length >= 10 && weightDiff14 <= -1) {
    comments.push({
      title: '2週間で体重が落ちています',
      body: `過去2週間で体重が ${weightDiff14.toFixed(1)}kg 変化しています。意図的なものでなければ、総エネルギー量を上げる時期です。`,
      tone: 'warn'
    })
  }

  if (skippedSnacks5 >= 3) {
    comments.push({
      title: '補食のスキップが続いています',
      body: '過去5日で補食抜けが目立ちます。練習前にゼリー1本だけでも入れる方が、後半の安定感を作りやすいです。',
      tone: 'warn'
    })
  }

  if (threeDayAllDone) {
    comments.push({
      title: '3日連続で全食実行できています',
      body: '3日連続で全食実行できています。この勢いを保ち、補食の時間帯まで固定できると再現性がさらに上がります。',
      tone: 'good'
    })
  }

  if (checkins7.length >= 5 && sleepAverage7 >= 7) {
    comments.push({
      title: '睡眠が安定しています',
      body: `過去7日の睡眠平均は ${sleepAverage7.toFixed(1)}時間です。コンディションの土台ができているので、練習前後の補給を固定していきましょう。`,
      tone: 'good'
    })
  }

  if (checkins14.length >= 10 && Math.abs(weightDiff14) <= 0.3) {
    comments.push({
      title: '体重が安定しています',
      body: '過去2週間の体重変動が小さく、エネルギー収支の見通しが立っています。今の食事リズムを基準に微調整できます。',
      tone: 'good'
    })
  }

  if (checkin.sleepHours < 6) {
    comments.push({
      title: '睡眠が短めです',
      body: `${profile.label}では集中力と技術再現性が落ちやすいので、今日は消化の軽い補食を早めに入れて午後のエネルギー切れを防ぎます。`,
      tone: 'warn'
    })
  }

  if (totalCarbs < targets.carbs.min) {
    comments.push({
      title: '糖質ターゲットに届いていません',
      body: `${profile.label}の${DAY_MODE_LABELS[dayMode]}では、目安は ${targets.carbs.min}-${targets.carbs.max}g/日です。主食を1-2回足し、補食も炭水化物中心にすると近づけやすいです。`,
      tone: 'warn'
    })
  }

  if ((dayMode === 'game' || dayMode === 'practice' || dayMode === 'pre_game') && skippedSnack) {
    comments.push({
      title: '補食が抜けています',
      body: `${profile.label}は短時間でも炭水化物の切れ方がパフォーマンスに響きます。ゼリー、バナナ、おにぎりなど短時間で入るものへ置き換えると崩れにくいです。`,
      tone: 'warn'
    })
  }

  if (checkin.fatigue >= 4) {
    comments.push({
      title: '疲労感が高めです',
      body: '回復を優先して、たんぱく質と水分を切らさない構成に寄せましょう。消化に重い食事より、分割して入れる方が無理がありません。',
      tone: 'info'
    })
  }

  if (checkin.appetite <= 2) {
    comments.push({
      title: '食欲が落ちています',
      body: '量で押すより、飲めるものと柔らかい炭水化物へ寄せる方が続きます。代替案のゼリー・ヨーグルト系を優先してください。',
      tone: 'info'
    })
  }

  if (plannedKcal > 0 && actualKcal < plannedKcal * 0.7) {
    comments.push({
      title: '実行率が落ちています',
      body: `未実施の食事が多いので、まずは${profile.focusNutrients[0]}を入れる1食をコンビニ代替で固定化すると改善しやすいです。`,
      tone: 'warn'
    })
  }

  if (totalProtein < targets.protein.min) {
    comments.push({
      title: 'たんぱく質ターゲットが不足しています',
      body: `体重 ${checkin.weight.toFixed(1)}kg なら目安は ${targets.protein.min}-${targets.protein.max}g/日です。夕食か補食に乳製品、大豆、魚、鶏肉を1回足すと近づけやすいです。`,
      tone: 'info'
    })
  }

  if (profile.id === 'ballet' && (checkin.appetite <= 2 || totalCarbs < targets.carbs.min)) {
    comments.push({
      title: 'バレエでは低エネルギー状態に注意です',
      body: '体重だけでなく、総エネルギー量・鉄・カルシウム・ビタミンDを切らさないことが回復と骨コンディションに重要です。',
      tone: 'warn'
    })
  }

  if ((profile.id === 'golf' || profile.id === 'table_tennis') && checkin.sleepHours < 6.5) {
    comments.push({
      title: '判断系スポーツなので血糖の落ち込みを避けます',
      body: '長時間の集中が必要なので、軽い糖質補食を前半から入れて反応速度の落ち込みを防ぐ設計が向いています。',
      tone: 'info'
    })
  }

  if (comments.length === 0 && incomplete.length === 0) {
    comments.push({
      title: `${athlete?.name ?? '選手'}の流れは良好です`,
      body: `${profile.label}の${DAY_MODE_LABELS[dayMode]}としてはかなり安定しています。このまま補食の時間だけ固定すると再現性が上がります。`,
      tone: 'good'
    })
  }

  if (comments.length === 0 && incomplete.length > 0) {
    comments.push({
      title: '未実施の食事が残っています',
      body: `${MEAL_SLOT_LABELS[plans[0]?.timing ?? 'Snack']}を含めて、未実施またはスキップの食事があります。${buildSportIncompleteMessage(profile.id)} 代替案を使って、まずは1食でも実行率を上げるのが近道です。`,
      tone: 'info'
    })
  }

  return comments.slice(0, 4)
}

export function buildGuardianShareText({
  athlete,
  selectedDate,
  dayMode,
  checkin,
  plans
}: {
  athlete: Athlete | null
  selectedDate: DateKey
  dayMode: DayMode
  checkin: DailyCheckin
  plans: Plan[]
}): string {
  const profile = getSportProfile(athlete?.sportId)
  const targets = getDailyTargets(profile, dayMode, checkin.weight)
  const planLines = plans.map((plan) => {
    return `- ${MEAL_SLOT_LABELS[plan.timing]} | ${plan.title} | ${PLAN_STATUS_LABELS[plan.status]}`
  })

  const rescuePlan = plans
    .filter((plan) => plan.status === 'planned' || plan.status === 'skipped')
    .slice(0, 2)
    .map((plan) => {
      const suggestions = getConvenienceSuggestions(plan.timing, dayMode, athlete?.sportId ?? 'track').join(' / ')
      return `- ${MEAL_SLOT_LABELS[plan.timing]}の代替候補: ${suggestions}`
    })

  return [
    `${athlete?.name ?? '選手'}の共有メモ`,
    `日付: ${selectedDate}`,
    `競技: ${profile.label}`,
    `モード: ${DAY_MODE_LABELS[dayMode]}`,
    `睡眠: ${checkin.sleepHours.toFixed(1)}時間 / 疲労: ${checkin.fatigue} / 食欲: ${checkin.appetite} / 体重: ${checkin.weight.toFixed(1)}kg`,
    `目安: 炭水化物 ${targets.carbs.min}-${targets.carbs.max}g / たんぱく質 ${targets.protein.min}-${targets.protein.max}g`,
    '',
    '食事の進捗',
    ...planLines,
    '',
    'サポートしてほしいこと',
    ...(rescuePlan.length > 0 ? rescuePlan : ['- 今のところ大きな補助は不要です'])
  ].join('\n')
}
