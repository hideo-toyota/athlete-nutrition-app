import React from 'react'
import NutritionCard from '../components/NutritionCard'
import AthleteCard from '../components/AthleteCard'
import { useAthlete } from '../context/AthleteContext'
import { useSnackbar } from '../context/SnackbarContext'
import AnalysisPanel from '../components/AnalysisPanel'
import { EditablePlan, DAY_MODE_LABELS, MEAL_SLOT_LABELS, Plan, SnackRole } from '../types'
import { getCompletionFactor, getConvenienceSuggestions, getSportProfile } from '../lib/appModel'
import DayModeSelector from '../components/DayModeSelector'
import CheckinPanel from '../components/CheckinPanel'
import AiCoachPanel from '../components/AiCoachPanel'
import SharePanel from '../components/SharePanel'
import ObsidianExportPanel from '../components/ObsidianExportPanel'
import SportProfilePanel from '../components/SportProfilePanel'
import CalendarPanel from '../components/CalendarPanel'
import EventFuelingPanel from '../components/EventFuelingPanel'
import BootCampSubmissionPanel from '../components/BootCampSubmissionPanel'
import BuddyPanel, { BuddySnapshot, PairScore } from '../components/BuddyPanel'
import TeamFoodLogPanel, { TeamFoodLogItem } from '../components/TeamFoodLogPanel'
import ReminderPanel, { ReminderRequest, ReminderTarget, ScheduledReminder } from '../components/ReminderPanel'
import { formatDateLabel } from '../lib/date'

const REMINDER_STORAGE_KEY = 'ctoc-reminders'

function readStoredReminders(): ScheduledReminder[] {
  try {
    const raw = localStorage.getItem(REMINDER_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((item) => typeof item?.id === 'string') : []
  } catch (error) {
    return []
  }
}

export default function Home({ onEditPlan }: { onEditPlan: (plan: EditablePlan) => void }){
  const { show } = useSnackbar()
  const {
    athletes,
    plans: allPlans,
    selectedAthlete,
    selectedSportProfile,
    selectedAthleteId,
    selectedDate,
    todayDateKey,
    setSelectedAthleteId,
    setSelectedDate,
    dateSummariesForSelected,
    updateSelectedAthleteSport,
    dayMode,
    setDayMode,
    checkin,
    updateCheckin,
    plansForSelected,
    totalsForSelected,
    dailyTotalsForSelected,
    dailyTotalsForAthlete,
    checkinForAthleteOnDate,
    setPlanStatus,
    setPlanPhoto
  } = useAthlete()
  const plans = plansForSelected()
  const totals = totalsForSelected()
  const dateSummaries = dateSummariesForSelected()
  const [reminders, setReminders] = React.useState<ScheduledReminder[]>(readStoredReminders)
  const snackPlans = plans.filter((plan) => plan.timing === 'Snack')
  const selectedAthleteIndex = Math.max(0, athletes.findIndex((athlete) => athlete.id === selectedAthleteId))
  const buddyAthlete = athletes.length > 1
    ? athletes[(selectedAthleteIndex + 1) % athletes.length]
    : selectedAthlete ?? athletes[0]

  React.useEffect(() => {
    try {
      localStorage.setItem(REMINDER_STORAGE_KEY, JSON.stringify(reminders))
    } catch (error) {}
  }, [reminders])

  const snackRoleForPlan = (plan: Plan): SnackRole => {
    if (plan.timing !== 'Snack') return 'general'
    const snackIndex = snackPlans.findIndex((snack) => snack.id === plan.id)
    if (snackPlans.length >= 3 && snackIndex > 0 && snackIndex < snackPlans.length - 1) return 'between_games'
    if (snackPlans.length >= 2 && snackIndex === 0) return 'pre_workout'
    if (snackPlans.length >= 2 && snackIndex > 0) return 'post_workout'
    return 'general'
  }

  const buildBuddySnapshot = (athlete = selectedAthlete ?? athletes[0]): BuddySnapshot => {
    const athletePlans = allPlans.filter((plan) => plan.athleteId === athlete?.id && plan.date === selectedDate)
    const athleteCheckin = athlete?.id ? checkinForAthleteOnDate(athlete.id, selectedDate) : checkin
    const completedCount = athletePlans.filter((plan) => plan.status === 'done').length
    const completionRate = athletePlans.length === 0
      ? 0
      : Math.round((athletePlans.reduce((sum, plan) => sum + getCompletionFactor(plan.status), 0) / athletePlans.length) * 100)

    return {
      name: athlete?.name ?? 'Athlete',
      sportLabel: getSportProfile(athlete?.sportId).label,
      completionRate,
      completedCount,
      planCount: athletePlans.length,
      incompleteCount: athletePlans.filter((plan) => plan.status === 'planned' || plan.status === 'skipped').length,
      sleepHours: athleteCheckin.sleepHours,
      fatigue: athleteCheckin.fatigue
    }
  }

  const selfSnapshot = buildBuddySnapshot(selectedAthlete ?? athletes[0])
  const buddySnapshot = buildBuddySnapshot(buddyAthlete)
  const selfDailyTotals = dailyTotalsForSelected()
  const buddyDailyTotals = buddyAthlete?.id ? dailyTotalsForAthlete(buddyAthlete.id) : []
  const pairRates = selfDailyTotals.map((selfDay, index) => {
    const buddyDay = buddyDailyTotals[index]
    const rates = [selfDay, buddyDay].filter((day) => day?.planCount > 0).map((day) => day.completionRate)
    return rates.length === 0 ? null : rates.reduce((sum, rate) => sum + rate, 0) / rates.length
  })
  const recentPairRates = pairRates.slice(-7).filter((rate): rate is number => typeof rate === 'number')
  const pairStreakDays = [...pairRates].reverse().findIndex((rate) => rate == null || rate < 0.8)
  const focusItems = [
    selfSnapshot.incompleteCount > 0 ? `${selfSnapshot.name} あと${selfSnapshot.incompleteCount}食` : null,
    buddySnapshot.incompleteCount > 0 ? `${buddySnapshot.name} あと${buddySnapshot.incompleteCount}食` : null,
    buddySnapshot.fatigue >= 4 ? `${buddySnapshot.name} 疲労高め` : null,
    buddySnapshot.sleepHours < 6.5 ? `${buddySnapshot.name} 睡眠短め` : null
  ].filter((item): item is string => Boolean(item))
  const pairScore: PairScore = {
    weeklyCompletionRate: recentPairRates.length === 0
      ? 0
      : Math.round((recentPairRates.reduce((sum, rate) => sum + rate, 0) / recentPairRates.length) * 100),
    streakDays: pairStreakDays === -1 ? pairRates.filter((rate) => rate != null).length : pairStreakDays,
    focusItems: focusItems.length > 0 ? focusItems.slice(0, 3) : ['ペアの流れ良好']
  }
  const teamFoodLogs: TeamFoodLogItem[] = allPlans
    .filter((plan) => plan.athleteId !== selectedAthleteId && plan.date === selectedDate)
    .slice(0, 4)
    .map((plan) => {
      const athlete = athletes.find((item) => item.id === plan.athleteId)
      const profile = getSportProfile(athlete?.sportId)

      return {
        id: plan.id,
        athleteName: athlete?.name ?? 'Team mate',
        sportLabel: profile.label,
        timing: plan.timing,
        timingLabel: MEAL_SLOT_LABELS[plan.timing],
        title: plan.title,
        note: `${profile.label}の実例ログです。今日の${MEAL_SLOT_LABELS[plan.timing]}に近い形で取り入れられます。`,
        kcal: plan.kcal,
        carbs: plan.carbs,
        protein: plan.protein,
        photoDataUrl: plan.photoDataUrl,
        tags: [MEAL_SLOT_LABELS[plan.timing], profile.category, plan.status === 'done' ? '実行済み' : '参考']
      }
    })
  const reminderTargets: ReminderTarget[] = [selectedAthlete, buddyAthlete]
    .filter((athlete): athlete is NonNullable<typeof athlete> => Boolean(athlete))
    .filter((athlete, index, array) => array.findIndex((item) => item.id === athlete.id) === index)
    .map((athlete) => ({ id: athlete.id, name: athlete.name }))

  const createReminder = (request: ReminderRequest) => {
    const target = reminderTargets.find((item) => item.id === request.targetId) ?? reminderTargets[0]
    if (!target) return

    setReminders((prev) => [
      {
        id: globalThis.crypto?.randomUUID?.() ?? `reminder_${Date.now()}`,
        targetId: target.id,
        targetName: target.name,
        dueLabel: request.dueLabel,
        message: request.message,
        createdAt: new Date().toISOString()
      },
      ...prev
    ].slice(0, 8))
    show('リマインドを予約しました')
  }

  const reminderTimingForFoodLog = (item: TeamFoodLogItem) => {
    if (item.timing === 'Snack') return '練習前30分'
    if (item.timing === 'Breakfast') return '朝食後'
    if (item.timing === 'Lunch') return '昼休み'
    return '試合前夜'
  }

  const copyTeamFoodLog = (item: TeamFoodLogItem) => {
    onEditPlan({
      athleteId: selectedAthleteId,
      title: `${item.title}（共有ログ）`,
      timing: item.timing,
      kcal: item.kcal,
      carbs: item.carbs,
      protein: item.protein,
      status: 'planned'
    })
    show('共有ログを新規プランに取り込みます')
  }

  const addFoodLogReminder = (item: TeamFoodLogItem) => {
    const targetId = selectedAthleteId ?? reminderTargets[0]?.id
    if (!targetId) return

    createReminder({
      targetId,
      dueLabel: reminderTimingForFoodLog(item),
      message: `${item.timingLabel}に「${item.title}」を確認`
    })
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <section className="col-span-2 space-y-4">
        <BootCampSubmissionPanel />

        <div className="glass p-4 rounded-xl">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-lg font-semibold">{formatDateLabel(selectedDate)} のサマリー</h2>
              <p className="mt-2 text-sm text-slate-400">{selectedAthlete?.focus}</p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-300">
                <span className="rounded-full bg-[rgba(255,255,255,0.03)] px-3 py-1">{selectedSportProfile.label}</span>
                <span className="rounded-full bg-[rgba(255,255,255,0.03)] px-3 py-1">{selectedDate}</span>
                <span className="rounded-full bg-[rgba(255,255,255,0.03)] px-3 py-1">{DAY_MODE_LABELS[dayMode]}</span>
                <span className="rounded-full bg-[rgba(255,255,255,0.03)] px-3 py-1">睡眠 {checkin.sleepHours.toFixed(1)}h</span>
                <span className="rounded-full bg-[rgba(255,255,255,0.03)] px-3 py-1">疲労 {checkin.fatigue}/5</span>
                <span className="rounded-full bg-[rgba(255,255,255,0.03)] px-3 py-1">完了 {totals.completed}件</span>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3 text-center">
                <div className="text-slate-500">kcal</div>
                <div className="mt-1 font-semibold text-neon-300">{totals.kcal}</div>
              </div>
              <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3 text-center">
                <div className="text-slate-500">糖質</div>
                <div className="mt-1 font-semibold text-neon-300">{totals.carbs}g</div>
              </div>
              <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3 text-center">
                <div className="text-slate-500">たんぱく質</div>
                <div className="mt-1 font-semibold text-neon-300">{totals.protein}g</div>
              </div>
            </div>
          </div>
        </div>

        <CalendarPanel
          selectedDate={selectedDate}
          todayDateKey={todayDateKey}
          summaries={dateSummaries}
          onSelectDate={setSelectedDate}
        />

        <div className="glass rounded-xl p-4">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h3 className="font-semibold">Day Mode</h3>
              <div className="text-sm text-slate-400">試合日・練習日・回復日で食事の見方を切り替えます。</div>
            </div>
          </div>
          <DayModeSelector value={dayMode} onChange={setDayMode} />
        </div>

        <SportProfilePanel
          profile={selectedSportProfile}
          dayMode={dayMode}
          bodyWeight={checkin.weight}
          onChange={updateSelectedAthleteSport}
        />

        <EventFuelingPanel />

        <div className="flex items-center justify-between">
          <div className="text-sm text-slate-400">{formatDateLabel(selectedDate)} のプラン</div>
          <div>
            <button className="px-3 py-2 rounded bg-neon-500 text-black" onClick={() => onEditPlan({ athleteId: selectedAthleteId, timing: 'Breakfast', status: 'planned' })}>Add Plan</button>
          </div>
        </div>

        {plans.length === 0 ? (
          <div className="rounded-xl border border-dashed border-white/10 bg-[rgba(255,255,255,0.02)] p-6 text-sm text-slate-400">
            この日付にはまだプランがありません。`Add Plan` から新しい日次プランを作成してください。
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {plans.map((plan) => (
              <NutritionCard
                key={plan.id}
                title={plan.title}
                timing={plan.timing}
                kcal={plan.kcal}
                carbs={plan.carbs}
                protein={plan.protein}
                status={plan.status}
                suggestions={getConvenienceSuggestions(plan.timing, dayMode, selectedSportProfile.id, snackRoleForPlan(plan))}
                photoDataUrl={plan.photoDataUrl}
                onClick={() => onEditPlan(plan)}
                onStatusChange={(status) => setPlanStatus(plan.id, status)}
                onPhotoChange={(photoDataUrl) => setPlanPhoto(plan.id, photoDataUrl)}
              />
            ))}
          </div>
        )}

        <TeamFoodLogPanel
          items={teamFoodLogs}
          onCopyPlan={copyTeamFoodLog}
          onAddReminder={addFoodLogReminder}
        />
      </section>

      <aside className="space-y-4">
        <div className="glass p-4 rounded-xl">
          <h3 className="font-semibold">Athletes</h3>
          <div className="mt-3 space-y-2">
            {athletes.map((athlete) => {
              const athleteProfile = getSportProfile(athlete.sportId)

              return (
                <AthleteCard
                  key={athlete.id}
                  name={athlete.name}
                  sport={athleteProfile.label}
                  category={athleteProfile.category}
                  focus={athlete.focus}
                  selected={athlete.id === selectedAthleteId}
                  onClick={() => setSelectedAthleteId(athlete.id)}
                />
              )
            })}
            <div className="text-sm text-slate-400 mt-3">Selected: {selectedAthleteId}</div>
          </div>
        </div>

        <BuddyPanel
          selectedDate={selectedDate}
          self={selfSnapshot}
          buddy={buddySnapshot}
          pairScore={pairScore}
        />
        <ReminderPanel
          targets={reminderTargets}
          reminders={reminders}
          onCreate={createReminder}
          onDelete={(id) => setReminders((prev) => prev.filter((reminder) => reminder.id !== id))}
        />
        <CheckinPanel checkin={checkin} onChange={updateCheckin} />
        <AnalysisPanel />
        <AiCoachPanel />
        <SharePanel />
        <ObsidianExportPanel />
      </aside>
    </div>
  )
}
