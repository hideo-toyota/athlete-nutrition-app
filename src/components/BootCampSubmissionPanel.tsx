import React from 'react'

const proofItems = [
  'React / TypeScript / Vite で実装した動作プロトタイプ',
  '本番日から逆算するカーボローディングと回復栄養を体重ベースで計算',
  '疲労、睡眠、食欲を使って当日の実行しやすさを補正',
  '保護者、コーチ、バディへ支援ポイントを共有できる設計',
  'Playwright E2E と TypeScript / production build で検証済み'
]

const featureItems = [
  'Event Fueling',
  'g/kg Targets',
  'Condition Modifiers',
  'Coach Notes MVP',
  'Guardian Share',
  'Buddy Support'
]

export default function BootCampSubmissionPanel() {
  return (
    <div className="glass overflow-hidden rounded-xl border border-amber-300/20">
      <div className="relative p-5">
        <div className="absolute right-0 top-0 h-24 w-24 rounded-bl-full bg-amber-300/10" />
        <div className="relative">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.24em] text-amber-200">SS BootCamp #4 Submission</div>
              <h2 className="mt-2 text-2xl font-semibold text-slate-50">本番逆算型スポーツ栄養コンディショニング</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
                試合・大会・バレエ発表会から逆算し、競技・体重・疲労・睡眠・食欲に合わせて、今日の食事目標と支援ポイントを出す
                Vibe Coding プロトタイプです。
              </p>
            </div>
            <div className="rounded-full border border-emerald-300/30 bg-emerald-300/10 px-3 py-1 text-xs text-emerald-100">
              提出用URL対応プロダクト
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-3">
            <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Proof</div>
              <div className="mt-2 text-lg font-semibold text-amber-200">本番逆算デモ</div>
              <div className="mt-1 text-xs text-slate-400">5日後の試合登録から、日別の糖質・回復目標まで提示</div>
            </div>
            <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Scope</div>
              <div className="mt-2 text-lg font-semibold text-emerald-200">スポーツ栄養 x 体調補正</div>
              <div className="mt-1 text-xs text-slate-400">体重あたり目標を、疲労・睡眠・食欲で現場向けに調整</div>
            </div>
            <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Status</div>
              <div className="mt-2 text-lg font-semibold text-neon-300">Build / E2E PASS</div>
              <div className="mt-1 text-xs text-slate-400">提出用の説明文と検証結果をREADMEに整理済み</div>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div>
              <div className="text-sm font-medium text-slate-100">実績として見せられる内容</div>
              <div className="mt-3 space-y-2">
                {proofItems.map((item) => (
                  <div className="flex gap-2 text-sm text-slate-300" key={item}>
                    <span className="mt-1 h-2 w-2 rounded-full bg-amber-300" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="text-sm font-medium text-slate-100">デモで伝える主要機能</div>
              <div className="mt-3 flex flex-wrap gap-2">
                {featureItems.map((item) => (
                  <span className="rounded-full border border-white/10 bg-[rgba(255,255,255,0.03)] px-3 py-1 text-xs text-slate-300" key={item}>
                    {item}
                  </span>
                ))}
              </div>
              <div className="mt-4 rounded-lg border border-amber-300/20 bg-amber-300/10 p-3 text-xs leading-5 text-amber-100">
                デモでは、機能一覧ではなく「5日後の本番を登録して、今日から何を食べるかを逆算する」流れを最初に見せると伝わりやすくなります。
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
