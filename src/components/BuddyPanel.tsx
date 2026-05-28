import React, { useState } from 'react'

export type BuddySnapshot = {
  name: string
  sportLabel: string
  completionRate: number
  completedCount: number
  planCount: number
  incompleteCount: number
  sleepHours: number
  fatigue: number
}

export type PairScore = {
  weeklyCompletionRate: number
  streakDays: number
  focusItems: string[]
}

export type BuddyPanelProps = {
  selectedDate: string
  self: BuddySnapshot
  buddy: BuddySnapshot
  pairScore: PairScore
}

const stampLabels = ['ナイス補食', '水分OK', '回復優先', '試合前いい感じ', 'あと1食']

function completionTone(rate: number) {
  if (rate >= 80) return 'text-emerald-300'
  if (rate >= 50) return 'text-amber-200'
  return 'text-rose-200'
}

function BuddyCard({ label, snapshot }: { label: string; snapshot: BuddySnapshot }) {
  return (
    <div className="rounded-lg border border-white/10 bg-[rgba(255,255,255,0.03)] p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</div>
          <div className="mt-1 font-semibold text-slate-100">{snapshot.name}</div>
          <div className="text-xs text-slate-500">{snapshot.sportLabel}</div>
        </div>
        <div className={`text-right text-xl font-semibold ${completionTone(snapshot.completionRate)}`}>
          {snapshot.completionRate}%
        </div>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
        <div className="rounded bg-black/20 p-2">
          <div className="text-slate-500">完了</div>
          <div className="mt-1 text-slate-200">{snapshot.completedCount}/{snapshot.planCount}</div>
        </div>
        <div className="rounded bg-black/20 p-2">
          <div className="text-slate-500">睡眠</div>
          <div className="mt-1 text-slate-200">{snapshot.sleepHours.toFixed(1)}h</div>
        </div>
        <div className="rounded bg-black/20 p-2">
          <div className="text-slate-500">疲労</div>
          <div className="mt-1 text-slate-200">{snapshot.fatigue}/5</div>
        </div>
      </div>
      {snapshot.incompleteCount > 0 && (
        <div className="mt-3 rounded border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-xs text-amber-100">
          未実施が {snapshot.incompleteCount} 件あります。軽く声かけすると続きやすい日です。
        </div>
      )}
    </div>
  )
}

export default function BuddyPanel({ selectedDate, self, buddy, pairScore }: BuddyPanelProps) {
  const [stampHistory, setStampHistory] = useState<string[]>([])

  const sendStamp = (label: string) => {
    setStampHistory((prev) => [`${label} → ${buddy.name}`, ...prev].slice(0, 4))
  }

  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="font-semibold">Buddy Check</h4>
          <div className="mt-1 text-sm text-slate-400">{selectedDate} の相互チェック</div>
        </div>
        <div className="rounded-full border border-neon-500/30 px-3 py-1 text-xs text-neon-300">CtoC</div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
        <BuddyCard label="You" snapshot={self} />
        <BuddyCard label="Buddy" snapshot={buddy} />
      </div>

      <div className="mt-4 rounded-lg border border-white/10 bg-[rgba(255,255,255,0.02)] p-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h5 className="font-medium text-slate-100">Pair Score</h5>
            <div className="mt-1 text-xs text-slate-500">直近7日のペア継続率</div>
          </div>
          <div className={`text-2xl font-semibold ${completionTone(pairScore.weeklyCompletionRate)}`}>
            {pairScore.weeklyCompletionRate}%
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-emerald-200">連続 {pairScore.streakDays} 日</span>
          {pairScore.focusItems.map((item) => (
            <span key={item} className="rounded-full bg-white/5 px-3 py-1 text-slate-300">{item}</span>
          ))}
        </div>
      </div>

      <div className="mt-4">
        <h5 className="font-medium text-slate-100">Cheer Stamps</h5>
        <div className="mt-2 flex flex-wrap gap-2">
          {stampLabels.map((label) => (
            <button
              key={label}
              aria-label={`send ${label}`}
              className="rounded-full border border-white/10 px-3 py-2 text-xs text-slate-300 hover:border-neon-500/40 hover:text-neon-300"
              onClick={() => sendStamp(label)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
        <div className="mt-3 rounded-lg bg-black/20 p-3 text-xs text-slate-400">
          {stampHistory.length === 0 ? (
            <div>応援スタンプを送ると、ここに履歴が残ります。</div>
          ) : (
            <div className="space-y-1">
              {stampHistory.map((stamp, index) => (
                <div key={`${stamp}-${index}`}>{stamp}</div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
