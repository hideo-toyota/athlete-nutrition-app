import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'
import { AthleteProvider } from './context/AthleteContext'
import { SnackbarProvider } from './context/SnackbarContext'

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
      <AthleteProvider>
        <SnackbarProvider>
          <App />
        </SnackbarProvider>
      </AthleteProvider>
  </React.StrictMode>
)
