import React, { useState } from 'react'

export type ReminderTarget = {
  id: string
  name: string
}

export type ScheduledReminder = {
  id: string
  targetId: string
  targetName: string
  dueLabel: string
  message: string
  createdAt: string
}

export type ReminderRequest = {
  targetId: string
  dueLabel: string
  message: string
}

type Props = {
  targets: ReminderTarget[]
  reminders: ScheduledReminder[]
  onCreate: (request: ReminderRequest) => void
  onDelete: (id: string) => void
}

const dueOptions = ['練習前30分', '朝食後', '昼休み', '試合前夜', '回復日の朝']
const messageOptions = ['補食そろそろ？', '水分取った？', 'あと1食だけ確認しよう', '今日は回復優先でいこう']

export default function ReminderPanel({ targets, reminders, onCreate, onDelete }: Props) {
  const [targetId, setTargetId] = useState(() => targets[0]?.id ?? '')
  const [dueLabel, setDueLabel] = useState(dueOptions[0])
  const [message, setMessage] = useState(messageOptions[0])

  const submit = () => {
    if (!targetId || !message.trim()) return

    onCreate({
      targetId,
      dueLabel,
      message: message.trim()
    })
  }

  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="font-semibold">Reminder Scheduler</h4>
          <div className="mt-1 text-sm text-slate-400">自分やバディに、補食・水分・回復の声かけを予約</div>
        </div>
        <div className="rounded-full border border-amber-300/30 px-3 py-1 text-xs text-amber-200">予約</div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3">
        <label className="text-sm text-slate-300">
          相手
          <select
            className="mt-1 w-full rounded bg-[rgba(255,255,255,0.02)] p-2 text-slate-100"
            value={targetId}
            onChange={(event) => setTargetId(event.target.value)}
          >
            {targets.map((target) => (
              <option key={target.id} value={target.id}>{target.name}</option>
            ))}
          </select>
        </label>
        <label className="text-sm text-slate-300">
          タイミング
          <select
            className="mt-1 w-full rounded bg-[rgba(255,255,255,0.02)] p-2 text-slate-100"
            value={dueLabel}
            onChange={(event) => setDueLabel(event.target.value)}
          >
            {dueOptions.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </label>
        <label className="text-sm text-slate-300">
          メッセージ
          <input
            className="mt-1 w-full rounded bg-[rgba(255,255,255,0.02)] p-2 text-slate-100"
            list="reminder-message-options"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
          />
          <datalist id="reminder-message-options">
            {messageOptions.map((option) => (
              <option key={option} value={option} />
            ))}
          </datalist>
        </label>
        <button
          className="rounded bg-neon-500 px-3 py-2 text-sm font-medium text-black"
          onClick={submit}
          type="button"
        >
          リマインド予約
        </button>
      </div>

      <div className="mt-4">
        <div className="mb-2 text-sm font-medium text-slate-200">予約済みリマインド</div>
        {reminders.length === 0 ? (
          <div className="rounded-lg border border-dashed border-white/10 bg-[rgba(255,255,255,0.02)] p-3 text-xs text-slate-400">
            まだ予約はありません。補食や水分の声かけを先に置いておくと、当日の抜け漏れを減らせます。
          </div>
        ) : (
          <div className="space-y-2">
            {reminders.map((reminder) => (
              <div key={reminder.id} className="rounded-lg border border-white/10 bg-black/20 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium text-slate-100">{reminder.targetName} / {reminder.dueLabel}</div>
                    <div className="mt-1 text-xs text-slate-400">{reminder.message}</div>
                  </div>
                  <button
                    className="rounded-full border border-white/10 px-2 py-1 text-[11px] text-slate-400 hover:border-rose-400/40 hover:text-rose-200"
                    onClick={() => onDelete(reminder.id)}
                    type="button"
                  >
                    削除
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
