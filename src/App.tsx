import React, { useState } from 'react'
import Header from './components/Header'
import Home from './pages/Home'
import PlanModal from './components/PlanModal'
import { useAthlete } from './context/AthleteContext'
import { EditablePlan } from './types'

export default function App(){
  const { dayMode, selectedAthlete, selectedAthleteId, selectedSportProfile } = useAthlete()
  const [editingPlan, setEditingPlan] = useState<EditablePlan | null>(null)

  const openNewPlan = () => {
    setEditingPlan({
      athleteId: selectedAthleteId,
      timing: 'Breakfast',
      status: 'planned'
    })
  }

  return (
    <div className="min-h-screen p-6">
      <Header
        athleteName={selectedAthlete?.name ?? 'Athlete'}
        sportLabel={selectedSportProfile.label}
        dayMode={dayMode}
        onNewPlan={openNewPlan}
      />
      <main className="mt-6">
        <Home onEditPlan={setEditingPlan} />
      </main>
      {editingPlan && <PlanModal plan={editingPlan} onClose={() => setEditingPlan(null)} />}
    </div>
  )
}
