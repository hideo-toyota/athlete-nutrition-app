import React from 'react'
import { useAthlete } from '../context/AthleteContext'
import { buildCoachComments, buildEventFuelingPlan } from '../lib/appModel'

const toneStyles = {
  info: 'border-white/10 bg-[rgba(255,255,255,0.03)]',
  warn: 'border-amber-400/30 bg-amber-400/10',
  good: 'border-emerald-400/30 bg-emerald-400/10'
}

export default function AiCoachPanel(){
  const {
    checkin,
    dayMode,
    plansForSelected,
    selectedAthlete,
    selectedAthleteId,
    selectedSportProfile,
    todayDateKey,
    dailyTotalsForSelected,
    recentCheckinsForSelected,
    upcomingEventForSelected,
    checkinForAthleteOnDate
  } = useAthlete()
  const plans = plansForSelected()
  const upcomingEvent = upcomingEventForSelected()
  const eventFuelingDays = upcomingEvent
    ? buildEventFuelingPlan({
      event: upcomingEvent,
      athlete: selectedAthlete,
      profile: selectedSportProfile,
      todayDateKey,
      fallbackCheckin: checkin,
      getCheckinForDate: (date) => selectedAthleteId ? checkinForAthleteOnDate(selectedAthleteId, date) : checkin
    })
    : []
  const comments = buildCoachComments({
    athlete: selectedAthlete,
    dayMode,
    plans,
    checkin,
    todayDateKey,
    upcomingEvent,
    eventFuelingDays,
    recentDailyTotals: dailyTotalsForSelected().slice(-14),
    recentCheckins: recentCheckinsForSelected().slice(-14)
  })

  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold">AI Coach Notes</h4>
        <div className="text-xs text-neon-300">Rule-based MVP</div>
      </div>
      {plans.length === 0 && comments.length === 0 ? (
        <div className="mt-4 rounded-lg border border-dashed border-white/10 bg-[rgba(255,255,255,0.02)] p-4 text-sm text-slate-400">
          プランがまだ無いため、AI コメントは表示されません。まずは `Add Plan` から食事プランを作成してください。
        </div>
      ) : comments.length === 0 ? (
        <div className="mt-4 rounded-lg border border-dashed border-white/10 bg-[rgba(255,255,255,0.02)] p-4 text-sm text-slate-400">
          コメントはまだありません。体調ログや実行チェックを更新すると分析が表示されます。
        </div>
      ) : (
        <div className="mt-4 space-y-3">
          {comments.map((comment) => (
            <div key={comment.title} className={`rounded-lg border p-3 ${toneStyles[comment.tone]}`}>
              <div className="font-medium text-slate-100">{comment.title}</div>
              <div className="mt-2 text-sm text-slate-300">{comment.body}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
