import { Athlete, Plan } from '../types'

export const ATHLETES: Athlete[] = [
  {
    id: 'a1',
    name: 'Haruka Tanaka',
    sportId: 'track',
    focus: '400mの週末レースに向けてエネルギー切れを防ぐ',
    baselineWeight: 56.8
  },
  {
    id: 'a2',
    name: 'Ren Ito',
    sportId: 'soccer',
    focus: '連戦でも後半のスプリント強度を落とさない',
    baselineWeight: 68.2
  },
  {
    id: 'a3',
    name: 'Airi Nakamura',
    sportId: 'ballet',
    focus: 'リハーサル量が多い週でも回復と骨コンディションを守る',
    baselineWeight: 50.4
  },
  {
    id: 'a4',
    name: 'Kenta Saito',
    sportId: 'swimming',
    focus: '朝練後の回復と体重維持を安定させる',
    baselineWeight: 72.4
  }
]

export const PLANS: Array<Omit<Plan, 'date'>> = [
  {
    id: 'p1',
    athleteId: 'a1',
    title: 'Morning Fuel',
    timing: 'Breakfast',
    kcal: 520,
    carbs: 78,
    protein: 32,
    status: 'done'
  },
  {
    id: 'p2',
    athleteId: 'a1',
    title: 'Pre-Workout Snack',
    timing: 'Snack',
    kcal: 320,
    carbs: 48,
    protein: 12,
    status: 'partial'
  },
  {
    id: 'p3',
    athleteId: 'a1',
    title: 'Post-Session Rice Bowl',
    timing: 'Lunch',
    kcal: 680,
    carbs: 95,
    protein: 38,
    status: 'planned'
  },
  {
    id: 'p4',
    athleteId: 'a2',
    title: 'Matchday Rice Bowl',
    timing: 'Lunch',
    kcal: 710,
    carbs: 102,
    protein: 32,
    status: 'planned'
  },
  {
    id: 'p5',
    athleteId: 'a2',
    title: 'Half-time Banana Gel',
    timing: 'Snack',
    kcal: 250,
    carbs: 54,
    protein: 4,
    status: 'done'
  },
  {
    id: 'p6',
    athleteId: 'a3',
    title: 'Studio Breakfast',
    timing: 'Breakfast',
    kcal: 420,
    carbs: 55,
    protein: 20,
    status: 'done'
  },
  {
    id: 'p7',
    athleteId: 'a3',
    title: 'Post-Rehearsal Salmon Plate',
    timing: 'Dinner',
    kcal: 560,
    carbs: 58,
    protein: 34,
    status: 'planned'
  },
  {
    id: 'p8',
    athleteId: 'a4',
    title: 'Poolside Breakfast',
    timing: 'Breakfast',
    kcal: 540,
    carbs: 72,
    protein: 30,
    status: 'planned'
  },
  {
    id: 'p9',
    athleteId: 'a4',
    title: 'Recovery Shake',
    timing: 'Snack',
    kcal: 420,
    carbs: 44,
    protein: 40,
    status: 'done'
  }
]
