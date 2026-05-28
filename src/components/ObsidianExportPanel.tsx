import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useAthlete } from '../context/AthleteContext'
import { useSnackbar } from '../context/SnackbarContext'
import { getDailyTargets, getSportProfile } from '../lib/appModel'
import { formatDateLabel } from '../lib/date'
import { DAY_MODE_LABELS, MEAL_SLOT_LABELS, PLAN_STATUS_LABELS, PlanStatus } from '../types'

const OBSIDIAN_VAULT_STORAGE_KEY = 'obsidian-vault-name'

function fallbackCopy(text: string) {
  const area = document.createElement('textarea')
  area.value = text
  area.style.position = 'fixed'
  area.style.opacity = '0'
  document.body.appendChild(area)
  area.focus()
  area.select()
  const ok = document.execCommand('copy')
  document.body.removeChild(area)
  return ok
}

function statusCheckbox(status: PlanStatus) {
  if (status === 'done') return 'x'
  if (status === 'partial') return '/'
  return ' '
}

function safeFilename(value: string) {
  return value.replace(/[\\/:*?"<>|#[\]^]/g, '-').replace(/\s+/g, ' ').trim()
}

export default function ObsidianExportPanel() {
  const {
    checkin,
    dayMode,
    plansForSelected,
    selectedAthlete,
    selectedDate,
    selectedSportProfile,
    totalsForSelected
  } = useAthlete()
  const { show } = useSnackbar()
  const [vaultName, setVaultName] = useState(() => localStorage.getItem(OBSIDIAN_VAULT_STORAGE_KEY) ?? '')
  const [copied, setCopied] = useState(false)
  const copiedTimerRef = useRef<number | null>(null)

  const plans = plansForSelected()
  const totals = totalsForSelected()
  const profile = selectedSportProfile ?? getSportProfile(selectedAthlete?.sportId)
  const targets = getDailyTargets(profile, dayMode, checkin.weight)
  const noteName = `${selectedDate} ${selectedAthlete?.name ?? 'Athlete'} nutrition log`

  useEffect(() => {
    localStorage.setItem(OBSIDIAN_VAULT_STORAGE_KEY, vaultName)
  }, [vaultName])

  useEffect(() => {
    return () => {
      if (copiedTimerRef.current !== null) {
        window.clearTimeout(copiedTimerRef.current)
      }
    }
  }, [])

  const markdown = useMemo(() => {
    const planLines = plans.length === 0
      ? ['- まだ食事プランはありません。']
      : plans.map((plan) => {
          return `- [${statusCheckbox(plan.status)}] ${MEAL_SLOT_LABELS[plan.timing]}: ${plan.title} (${PLAN_STATUS_LABELS[plan.status]}) - ${plan.kcal}kcal / C${plan.carbs}g / P${plan.protein}g`
        })

    return [
      '---',
      'type: athlete-nutrition-log',
      `date: ${selectedDate}`,
      `athlete: ${selectedAthlete?.name ?? 'Athlete'}`,
      `sport: ${profile.label}`,
      `day_mode: ${DAY_MODE_LABELS[dayMode]}`,
      'tags:',
      '  - athlete-nutrition',
      `  - sport/${profile.id}`,
      '---',
      '',
      `# ${formatDateLabel(selectedDate)} ${selectedAthlete?.name ?? 'Athlete'} 栄養ログ`,
      '',
      '## Summary',
      `- 競技: ${profile.label}`,
      `- Day Mode: ${DAY_MODE_LABELS[dayMode]}`,
      `- 睡眠: ${checkin.sleepHours.toFixed(1)}時間`,
      `- 疲労: ${checkin.fatigue}/5`,
      `- 食欲: ${checkin.appetite}/5`,
      `- 体重: ${checkin.weight.toFixed(1)}kg`,
      '',
      '## Nutrition Targets',
      `- 炭水化物目安: ${targets.carbs.min}-${targets.carbs.max}g`,
      `- たんぱく質目安: ${targets.protein.min}-${targets.protein.max}g`,
      `- 重点栄養素: ${profile.focusNutrients.join('、')}`,
      '',
      '## Planned / Actual',
      `- 合計: ${totals.kcal}kcal / 炭水化物 ${totals.carbs}g / たんぱく質 ${totals.protein}g`,
      `- 完了: ${totals.completed}件 / 一部: ${totals.partial}件 / スキップ: ${totals.skipped}件`,
      '',
      '## Meal Log',
      ...planLines,
      '',
      '## Condition Note',
      checkin.note.trim() ? checkin.note.trim() : '- 体調メモなし',
      '',
      '## Reflection',
      '- 今日うまくいったこと:',
      '- 次回変えること:',
      '- コーチ/保護者に共有すること:'
    ].join('\n')
  }, [checkin, dayMode, plans, profile, selectedAthlete, selectedDate, targets, totals])

  const markCopied = () => {
    if (copiedTimerRef.current !== null) {
      window.clearTimeout(copiedTimerRef.current)
    }

    setCopied(true)
    copiedTimerRef.current = window.setTimeout(() => {
      setCopied(false)
      copiedTimerRef.current = null
    }, 2000)
  }

  const copyMarkdown = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(markdown)
        markCopied()
        show('Obsidian用Markdownをコピーしました')
        return
      }

      if (fallbackCopy(markdown)) {
        markCopied()
        show('Obsidian用Markdownをコピーしました')
        return
      }
    } catch (error) {
      if (fallbackCopy(markdown)) {
        markCopied()
        show('Obsidian用Markdownをコピーしました')
        return
      }
    }

    show('コピーに失敗しました')
  }

  const downloadMarkdown = () => {
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${safeFilename(noteName)}.md`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    show('Markdownファイルを保存しました')
  }

  const openObsidian = () => {
    const params = new URLSearchParams()
    if (vaultName.trim()) {
      params.set('vault', vaultName.trim())
    }
    params.set('name', noteName)
    params.set('content', markdown)
    window.location.href = `obsidian://new?${params.toString()}`
    show('Obsidian起動を試みました')
  }

  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="font-semibold">Obsidian Export</h4>
          <p className="mt-1 text-sm text-slate-400">日次ログをMarkdownノートとして残します。</p>
        </div>
        <div className="rounded-full border border-cyan-300/30 px-3 py-1 text-xs text-cyan-200">Markdown</div>
      </div>

      <label className="mt-4 block text-sm text-slate-300">
        Vault名（任意）
        <input
          className="mt-1 w-full rounded bg-[rgba(255,255,255,0.02)] p-2 text-slate-100"
          placeholder="例: Athlete Notes"
          value={vaultName}
          onChange={(event) => setVaultName(event.target.value)}
        />
      </label>

      <div className="mt-3 rounded-lg border border-white/10 bg-black/20 p-3 text-xs text-slate-400">
        <div className="font-medium text-slate-200">{noteName}</div>
        <div className="mt-1">コピーが最も確実です。Obsidianボタンは、端末にObsidianが入っている場合に新規ノート作成を試みます。</div>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
        <button
          className="rounded border border-white/10 px-3 py-2 text-sm text-slate-200 hover:border-cyan-300/40"
          onClick={copyMarkdown}
          type="button"
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
        <button
          className="rounded border border-white/10 px-3 py-2 text-sm text-slate-200 hover:border-cyan-300/40"
          onClick={downloadMarkdown}
          type="button"
        >
          .md保存
        </button>
        <button
          className="rounded bg-neon-500 px-3 py-2 text-sm font-medium text-black"
          onClick={openObsidian}
          type="button"
        >
          Obsidian
        </button>
      </div>

      <textarea
        className="mt-4 min-h-[150px] w-full rounded bg-[rgba(255,255,255,0.02)] p-3 text-xs text-slate-300"
        readOnly
        value={markdown}
      />
    </div>
  )
}
