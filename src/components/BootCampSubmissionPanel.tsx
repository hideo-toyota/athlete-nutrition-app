import React from 'react'

const proofItems = [
  'React / TypeScript / Vite で実装した動作プロトタイプ',
  '競技別の栄養目標、体調ログ、写真、カレンダー、CtoC支援を統合',
  '本番日から逆算するカーボローディングと回復栄養を体重ベースで計算',
  'Playwright E2E と TypeScript / production build で検証済み'
]

const featureItems = [
  'Sport Profile',
  'Event Fueling',
  'AI Coach Notes',
  'Buddy Check',
  'Team Food Log',
  'Reminder'
]

export default function BootCampSubmissionPanel() {
  return (
    <div className="glass overflow-hidden rounded-xl border border-neon-500/20">
      <div className="relative p-5">
        <div className="absolute right-0 top-0 h-24 w-24 rounded-bl-full bg-neon-500/10" />
        <div className="relative">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.24em] text-neon-300">SS BootCamp #4 Submission</div>
              <h2 className="mt-2 text-2xl font-semibold text-slate-50">Athlete Nutrition App</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
                競技・本番日・体調に合わせて、食事計画、実行チェック、振り返り、仲間や保護者との共有までを1画面で支援する
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
              <div className="mt-2 text-lg font-semibold text-neon-300">中身のある成果物</div>
              <div className="mt-1 text-xs text-slate-400">公開GitHub / 公開Web / デモ動画のURLで提示可能</div>
            </div>
            <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Scope</div>
              <div className="mt-2 text-lg font-semibold text-neon-300">スポーツ栄養 x 行動継続</div>
              <div className="mt-1 text-xs text-slate-400">記録だけでなく、本番前後の実行支援まで扱います。</div>
            </div>
            <div className="rounded-lg bg-[rgba(255,255,255,0.03)] p-3">
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Status</div>
              <div className="mt-2 text-lg font-semibold text-neon-300">Build / E2E PASS</div>
              <div className="mt-1 text-xs text-slate-400">応募フォームに貼る説明文は SUBMISSION.md に整理済みです。</div>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div>
              <div className="text-sm font-medium text-slate-100">実績として見せられる内容</div>
              <div className="mt-3 space-y-2">
                {proofItems.map((item) => (
                  <div className="flex gap-2 text-sm text-slate-300" key={item}>
                    <span className="mt-1 h-2 w-2 rounded-full bg-neon-400" />
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
                応募時は、GitHubリポジトリ、公開デモURL、デモ動画URLのうち1つ以上をフォームに貼ってください。
                ローカルファイルだけでは応募条件を満たしにくいため、公開URL化が最後の仕上げです。
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
