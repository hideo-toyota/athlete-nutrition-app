import React, { useEffect, useRef, useState } from 'react'
import { useSnackbar } from '../context/SnackbarContext'
import { buildGuardianShareText } from '../lib/appModel'
import { useAthlete } from '../context/AthleteContext'

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

export default function SharePanel(){
  const { checkin, dayMode, plansForSelected, selectedAthlete, selectedDate } = useAthlete()
  const { show } = useSnackbar()
  const [copied, setCopied] = useState(false)
  const copiedTimerRef = useRef<number | null>(null)

  const shareText = buildGuardianShareText({
    athlete: selectedAthlete,
    selectedDate,
    dayMode,
    checkin,
    plans: plansForSelected()
  })

  useEffect(() => {
    return () => {
      if (copiedTimerRef.current !== null) {
        window.clearTimeout(copiedTimerRef.current)
      }
    }
  }, [])

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

  const handleCopy = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareText)
        markCopied()
        show('共有メモをコピーしました')
        return
      }

      const copiedWithFallback = fallbackCopy(shareText)
      if (copiedWithFallback) {
        markCopied()
        show('共有メモをコピーしました')
        return
      }
    } catch (error) {
      const copiedWithFallback = fallbackCopy(shareText)
      if (copiedWithFallback) {
        markCopied()
        show('共有メモをコピーしました')
        return
      }
    }

    show('コピーに失敗しました')
  }

  return (
    <div className="glass rounded-xl p-4">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold">Guardian Share Mode</h4>
        <button className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300" onClick={handleCopy} type="button">
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <p className="mt-2 text-sm text-slate-400">保護者やコーチに、そのまま送れる日次メモです。</p>
      <textarea className="mt-4 min-h-[180px] w-full rounded bg-[rgba(255,255,255,0.02)] p-3 text-sm text-slate-300" readOnly value={shareText} />
    </div>
  )
}
