import React, { createContext, useContext, useState, ReactNode, useCallback, useEffect, useRef } from 'react'

type SnackbarContextValue = {
  show: (msg: string) => void
}

const SnackbarContext = createContext<SnackbarContextValue | undefined>(undefined)

export function SnackbarProvider({ children }: { children: ReactNode }){
  const [message, setMessage] = useState<string | null>(null)
  const timerRef = useRef<number | null>(null)

  const show = useCallback((msg: string) => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current)
    }

    setMessage(msg)
    timerRef.current = window.setTimeout(() => {
      setMessage(null)
      timerRef.current = null
    }, 3000)
  }, [])

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current)
      }
    }
  }, [])

  return (
    <SnackbarContext.Provider value={{ show }}>
      {children}
      {message && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 px-4 py-2 bg-neon-500 text-black rounded shadow-neon-lg">
          {message}
        </div>
      )}
    </SnackbarContext.Provider>
  )
}

export function useSnackbar(){
  const ctx = useContext(SnackbarContext)
  if (!ctx) throw new Error('useSnackbar must be used within SnackbarProvider')
  return ctx
}
