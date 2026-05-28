// 極端シナリオでAIコーチが正しく反応するか検証
import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import path from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function pad(n) { return String(n).padStart(2, '0'); }
function dateKey(d) { return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`; }

const ATHLETES = [
  { id: 'a1', name: 'Haruka Tanaka', sportId: 'track', focus: '400m', baselineWeight: 56.8 },
  { id: 'a2', name: 'Ren Ito', sportId: 'soccer', focus: '連戦スプリント', baselineWeight: 68.2 },
  { id: 'a3', name: 'Airi Nakamura', sportId: 'ballet', focus: 'リハーサル', baselineWeight: 50.4 },
  { id: 'a4', name: 'Kenta Saito', sportId: 'swimming', focus: '朝練後の回復', baselineWeight: 72.4 }
];

const results = [];
function record(scenario, label, ok, detail = '') {
  results.push({ scenario, label, ok, detail });
  console.log(`  [${ok ? '✅' : '❌'}] ${label}${detail ? `: ${detail}` : ''}`);
}

// シナリオ別データ生成
function buildScenario(scenarioId, today) {
  const plans = [];
  const checkins = {};
  const dayModes = {};

  for (const athlete of ATHLETES) {
    checkins[athlete.id] = {};
    dayModes[athlete.id] = {};

    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      const dk = dateKey(date);
      const dayMode = i % 7 === 0 ? 'game' : (i % 7 === 6 ? 'pre_game' : 'practice');

      let checkin;
      let mealStatusPattern;

      // シナリオ別
      switch (scenarioId) {
        case 'zero_completion': // 完了率0% (全部未実施)
          checkin = { sleepHours: 7, fatigue: 3, appetite: 3, weight: athlete.baselineWeight, note: '' };
          mealStatusPattern = ['planned', 'planned', 'planned', 'planned', 'planned'];
          break;
        case 'perfect_streak': // 30日全食完了
          checkin = { sleepHours: 7.5, fatigue: 2, appetite: 4, weight: athlete.baselineWeight, note: '' };
          mealStatusPattern = ['done', 'done', 'done', 'done', 'done'];
          break;
        case 'weight_drop': // 14日で体重-2kg
          const dropFactor = i < 14 ? (i / 14) * 2 : 0;
          checkin = { sleepHours: 6.5, fatigue: 3, appetite: 2, weight: athlete.baselineWeight - 2 + dropFactor, note: '' };
          mealStatusPattern = ['done', 'partial', 'planned', 'partial', 'done'];
          break;
        case 'fatigue_accumulation': // 疲労が4-5で蓄積
          checkin = { sleepHours: 5.5, fatigue: i < 7 ? 5 : 4, appetite: 2, weight: athlete.baselineWeight, note: '' };
          mealStatusPattern = ['done', 'planned', 'done', 'planned', 'partial'];
          break;
        case 'snack_skip': // 補食ばかり抜く
          checkin = { sleepHours: 7, fatigue: 3, appetite: 3, weight: athlete.baselineWeight, note: '' };
          mealStatusPattern = ['done', 'skipped', 'done', 'skipped', 'done'];
          break;
        case 'low_carb': // 糖質目標を大幅に下回る
          checkin = { sleepHours: 7, fatigue: 3, appetite: 3, weight: athlete.baselineWeight, note: '' };
          mealStatusPattern = ['done', 'done', 'done', 'done', 'done'];
          break;
        default:
          checkin = { sleepHours: 7, fatigue: 3, appetite: 3, weight: athlete.baselineWeight, note: '' };
          mealStatusPattern = ['done', 'done', 'done', 'done', 'done'];
      }
      checkins[athlete.id][dk] = checkin;
      dayModes[athlete.id][dk] = dayMode;

      const w = athlete.baselineWeight;
      const carbsBase = scenarioId === 'low_carb' ? 2 : 7;
      const proteinBase = scenarioId === 'low_carb' ? 0.8 : 1.6;

      const meals = [
        { timing: 'Breakfast', title: '朝食', ratio: 0.25 },
        { timing: 'Snack', title: '練習前補食', ratio: 0.15 },
        { timing: 'Lunch', title: '昼食', ratio: 0.30 },
        { timing: 'Snack', title: '練習後補食', ratio: 0.10 },
        { timing: 'Dinner', title: '夕食', ratio: 0.20 }
      ];
      meals.forEach((meal, idx) => {
        const dailyCarbs = Math.round(carbsBase * w);
        const dailyProtein = Math.round(proteinBase * w);
        plans.push({
          id: `${scenarioId}_${athlete.id}_${dk}_${idx}`,
          athleteId: athlete.id,
          date: dk,
          title: `${meal.title} ${scenarioId}`,
          timing: meal.timing,
          kcal: Math.round(dailyCarbs * 4 * meal.ratio + 200),
          carbs: Math.round(dailyCarbs * meal.ratio),
          protein: Math.round(dailyProtein * meal.ratio),
          status: mealStatusPattern[idx]
        });
      });
    }
  }

  return { plans, checkins, dayModes };
}

async function getAIComments(page) {
  return await page.evaluate(() => {
    const heading = Array.from(document.querySelectorAll('h3, h4')).find(h => /coach|AI/i.test(h.textContent || ''));
    if (!heading) return [];
    const panel = heading.closest('.glass');
    if (!panel) return [];
    const items = panel.querySelectorAll('div[class*="rounded"]');
    return Array.from(items).map(i => (i.textContent || '').trim()).filter(t => t.length > 10 && t.length < 400);
  });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  page.on('pageerror', e => console.log('PAGE_ERROR:', e.message));

  await page.goto('http://localhost:5173/');
  const today = new Date();

  const scenarios = [
    { id: 'zero_completion', name: '完了率0% (全食未実施)', expect: '実行率低下 or 未実施警告' },
    { id: 'perfect_streak',  name: '30日完璧 (全食完了)', expect: 'ポジティブ強化コメント (good tone)' },
    { id: 'weight_drop',     name: '14日で体重-2kg', expect: '体重減少警告 or 低エネルギー警告' },
    { id: 'fatigue_accumulation', name: '疲労4-5蓄積', expect: '疲労警告 + 睡眠警告' },
    { id: 'snack_skip',      name: '補食ばかり抜く', expect: '補食抜け警告' },
    { id: 'low_carb',        name: '糖質目標大幅未達', expect: '糖質ターゲット警告' }
  ];

  for (const scenario of scenarios) {
    console.log(`\n${'━'.repeat(64)}`);
    console.log(`▶ シナリオ: ${scenario.name}`);
    console.log(`  期待: ${scenario.expect}`);
    console.log('━'.repeat(64));

    await page.evaluate(() => localStorage.clear());
    const { plans, checkins, dayModes } = buildScenario(scenario.id, today);

    await page.evaluate(({ athletes, plans, checkins, dayModes }) => {
      localStorage.setItem('athletes', JSON.stringify(athletes));
      localStorage.setItem('plans', JSON.stringify(plans));
      localStorage.setItem('athlete-checkins', JSON.stringify(checkins));
      localStorage.setItem('athlete-day-modes', JSON.stringify(dayModes));
      localStorage.setItem('selected-athlete-id', JSON.stringify('a1'));
    }, { athletes: ATHLETES, plans, checkins, dayModes });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1200);

    const comments = await getAIComments(page);
    const joined = comments.join(' ');
    console.log(`  取得したAIコメント数: ${comments.length}`);
    comments.slice(0, 5).forEach((c, i) => console.log(`    ${i+1}. ${c.replace(/\s+/g, ' ').slice(0, 140)}`));

    // シナリオ別期待文言検証
    const checks = {
      zero_completion: /実行率|未実施/,
      perfect_streak: /安定|高水準|連続|問題ない|流れは良好/,
      weight_drop: /体重|落ちて|減って|エネルギー量を上げる|低エネルギー/,
      fatigue_accumulation: /疲労|睡眠|回復/,
      snack_skip: /補食|スキップ|抜けて/,
      low_carb: /糖質|主食|炭水化物/
    };
    const matched = checks[scenario.id].test(joined);
    record(scenario.name, `AIが期待文言で反応`, matched, matched ? '反応OK' : `期待: ${scenario.expect}`);

    await page.screenshot({ path: path.join(__dirname, `edge-${scenario.id}.png`) });
  }

  console.log(`\n${'━'.repeat(64)}`);
  const pass = results.filter(r => r.ok).length;
  const fail = results.filter(r => !r.ok).length;
  console.log(`▶ 極端シナリオ検証 結果: PASS=${pass} / FAIL=${fail}`);
  console.log('━'.repeat(64));

  await browser.close();
  if (fail > 0) process.exitCode = 1;
})();
