import React, { useMemo, useState } from 'react'
import { Bar } from 'react-chartjs-2'
import { Chart as ChartJS, BarController, CategoryScale, LinearScale, BarElement, Tooltip, Legend } from 'chart.js'
import { useAthlete } from '../context/AthleteContext'
import { getDailyTargets } from '../lib/appModel'
import { DailyTotal } from '../types'

ChartJS.register(BarController, CategoryScale, LinearScale, BarElement, Tooltip, Legend)

type Metric = 'kcal' | 'carbs' | 'protein' | 'completion'

const metricLabels: Record<Metric, string> = {
  kcal: 'カロリー',
  carbs: '糖質',
  protein: 'たんぱく質',
  completion: '完了率'
}

function formatChartDate(dateKey: string) {
  return dateKey.slice(5)
}

function metricValue(day: DailyTotal, metric: Metric) {
  if (metric === 'kcal') return day.actualKcal
  if (metric === 'carbs') return day.totalCarbs
  if (metric === 'protein') return day.totalProtein
  return Math.round(day.completionRate * 100)
}

export default function AnalysisPanel(){
  const { plansForSelected, totalsForSelected, checkin, dayMode, selectedSportProfile, dailyTotalsForSelected } = useAthlete()
  const [metric, setMetric] = useState<Metric>('kcal')
  const plans = plansForSelected()
  const totals = totalsForSelected()
  const dailyTotals = dailyTotalsForSelected()
  const daysWithPlans = dailyTotals.filter((day) => day.planCount > 0)
  const targets = getDailyTargets(selectedSportProfile, dayMode, checkin.weight)
  const latestWeek = daysWithPlans.slice(-7)
  const weeklyCompletion = latestWeek.length === 0 ? 0 : Math.round((latestWeek.reduce((sum, day) => sum + day.completionRate, 0) / latestWeek.length) * 100)

  const data = useMemo(() => ({
    labels: dailyTotals.map((day) => formatChartDate(day.date)),
    datasets: [
      {
        label: metricLabels[metric],
        data: dailyTotals.map((day) => metricValue(day, metric)),
        backgroundColor: dailyTotals.map((day) => {
          if (day.planCount === 0) return 'rgba(148,163,184,0.22)'
          if (metric === 'completion') {
            if (day.completionRate >= 0.8) return 'rgba(52,211,153,0.75)'
            if (day.completionRate >= 0.5) return 'rgba(251,191,36,0.75)'
            return 'rgba(251,113,133,0.75)'
          }

          const dayTargets = getDailyTargets(selectedSportProfile, day.dayMode, day.bodyWeight)
          const min = metric === 'kcal' ? day.plannedKcal * 0.8 : metric === 'carbs' ? dayTargets.carbs.min : dayTargets.protein.min
          const max = metric === 'kcal' ? day.plannedKcal * 1.1 : metric === 'carbs' ? dayTargets.carbs.max : dayTargets.protein.max
          const value = metricValue(day, metric)

          if (value < min) return 'rgba(251,113,133,0.75)'
          if (value > max) return 'rgba(251,191,36,0.75)'
          return 'rgba(52,211,153,0.75)'
        })
      }
    ]
  }), [dailyTotals, metric, selectedSportProfile])

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context: { parsed: { y: number | null } }) => {
            const unit = metric === 'completion' ? '%' : metric === 'kcal' ? 'kcal' : 'g'
            return `${metricLabels[metric]}: ${context.parsed.y ?? 0}${unit}`
          }
        }
      }
    },
    scales: {
      y: { beginAtZero: true }
    }
  }

  return (
    <div className="glass p-4 rounded-xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="font-semibold">Analysis</h4>
          <div className="mt-1 text-xs text-slate-400">過去30日のトレンドを実行ベースで表示</div>
        </div>
        <div className="rounded-full border border-white/10 px-2 py-1 text-xs text-slate-300">30日</div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3">
          <div className="text-slate-400">合計kcal</div>
          <div className="mt-1 text-lg font-semibold text-neon-300">{totals.kcal}</div>
        </div>
        <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3">
          <div className="text-slate-400">糖質 / たんぱく質</div>
          <div className="mt-1 text-lg font-semibold text-neon-300">{totals.carbs}g / {totals.protein}g</div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-300">
        <span className="rounded-full bg-emerald-400/10 px-2 py-1 text-emerald-200">完了 {totals.completed}</span>
        <span className="rounded-full bg-amber-400/10 px-2 py-1 text-amber-200">一部 {totals.partial}</span>
        <span className="rounded-full bg-rose-400/10 px-2 py-1 text-rose-200">スキップ {totals.skipped}</span>
      </div>
      <div className="mt-3 grid grid-cols-1 gap-3 text-xs text-slate-300">
        <div className="rounded-lg border border-white/10 bg-[rgba(255,255,255,0.02)] p-3">
          <div className="text-slate-400">{selectedSportProfile.label} の目安</div>
          <div className="mt-2">炭水化物 {targets.carbs.min}-{targets.carbs.max}g / たんぱく質 {targets.protein.min}-{targets.protein.max}g</div>
          <div className="mt-2 text-slate-500">現在: 炭水化物 {totals.carbs}g / たんぱく質 {totals.protein}g</div>
        </div>
      </div>
      {daysWithPlans.length === 0 ? (
        <div className="mt-3 rounded-lg border border-dashed border-white/10 bg-[rgba(255,255,255,0.02)] p-4 text-sm text-slate-400">
          まだプランがありません。`Add Plan` から食事プランを追加してください。
        </div>
      ) : (
        <div className="mt-3">
          <div className="mb-3 flex flex-wrap gap-2">
            {(Object.keys(metricLabels) as Metric[]).map((item) => (
              <button
                key={item}
                className={`rounded-full border px-3 py-2 text-xs ${metric === item ? 'border-neon-500/50 bg-neon-500/10 text-neon-300' : 'border-white/10 text-slate-400'}`}
                onClick={() => setMetric(item)}
                type="button"
              >
                {metricLabels[item]}
              </button>
            ))}
          </div>
          <div
            className="h-56"
            data-testid="analysis-chart"
            data-days={dailyTotals.length}
            data-recorded-days={daysWithPlans.length}
          >
            <Bar data={data} options={options} />
          </div>
          <div className="mt-3 text-xs text-slate-500">
            過去30日中 {daysWithPlans.length}日分の記録を表示。直近7日の平均完了率は {weeklyCompletion}% です。
          </div>
        </div>
      )}
    </div>
  )
}
