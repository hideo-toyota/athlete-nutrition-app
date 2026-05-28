// 30日分のリアルなデータをシミュレートして、各スポーツの内容妥当性を検証
import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const checks = [];

function recordCheck(label, ok, detail = '') {
  checks.push({ label, ok, detail });
  console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${label}${detail ? `: ${detail}` : ''}`);
}

// ===== 30日データ生成ロジック =====
function pad(n) { return String(n).padStart(2, '0'); }
function dateKey(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

// 各スポーツの実存ATHLETES（mock.tsと一致）
const ATHLETES = [
  { id: 'a1', name: 'Haruka Tanaka', sportId: 'track', focus: '400mの週末レースに向けてエネルギー切れを防ぐ', baselineWeight: 56.8 },
  { id: 'a2', name: 'Ren Ito', sportId: 'soccer', focus: '連戦でも後半のスプリント強度を落とさない', baselineWeight: 68.2 },
  { id: 'a3', name: 'Airi Nakamura', sportId: 'ballet', focus: 'リハーサル量が多い週でも回復と骨コンディションを守る', baselineWeight: 50.4 },
  { id: 'a4', name: 'Kenta Saito', sportId: 'swimming', focus: '朝練後の回復と体重維持を安定させる', baselineWeight: 72.4 }
];

// 各スポーツの「典型的な食事プラン」テンプレート（ターゲットに合わせた現実的な数値）
function generatePlansForDay(athlete, date, dayMode) {
  // 体重ベースのkcal/carbs/protein
  const w = athlete.baselineWeight;
  const carbsPerKg = { practice: 7, pre_game: 8, game: 7, recovery: 6, normal: 5 }[dayMode];
  const proteinPerKg = 1.6;
  const dailyCarbs = Math.round(carbsPerKg * w);
  const dailyProtein = Math.round(proteinPerKg * w);
  const dailyKcal = dailyCarbs * 4 + dailyProtein * 4 + Math.round(w * 0.8) * 9; // 脂質も込み

  // 4-5食配分
  const meals = [
    { timing: 'Breakfast', title: '朝食 ごはん+魚+味噌汁', ratio: 0.25 },
    { timing: 'Snack', title: '練習前補食 おにぎり+バナナ', ratio: 0.15 },
    { timing: 'Lunch', title: '昼食 親子丼+サラダ', ratio: 0.30 },
    { timing: 'Snack', title: '練習後補食 プロテイン+果物', ratio: 0.10 },
    { timing: 'Dinner', title: '夕食 ごはん+鶏+野菜', ratio: 0.20 }
  ];

  // スポーツ別の調整
  if (athlete.sportId === 'ballet') {
    meals[3].title = '間食 ヨーグルト+ナッツ';
    meals[0].title = '朝食 シリアル+ヨーグルト+果物';
  } else if (athlete.sportId === 'swimming') {
    meals[1].title = '朝練後補食 ベーグル+ジュース';
    meals[3].title = '夕練後補食 おにぎり+プロテインドリンク';
  } else if (athlete.sportId === 'soccer') {
    meals[1].title = '練習前補食 あんぱん+スポーツドリンク';
  } else if (athlete.sportId === 'track') {
    meals[3].title = '練習後補食 鶏むね+おにぎり';
  }

  // ステータスの確率（30日中、運用が育つにつれ完了率が上がるシミュ）
  const dayIndex = Math.floor((Date.now() - date.getTime()) / (24 * 3600 * 1000));
  const completionRate = dayMode === 'recovery' ? 0.7 : (dayMode === 'game' ? 0.85 : 0.9);

  return meals.map((meal, i) => {
    const kcal = Math.round(dailyKcal * meal.ratio);
    const carbs = Math.round(dailyCarbs * meal.ratio);
    const protein = Math.round(dailyProtein * meal.ratio);
    // 実行ステータス
    const r = Math.random();
    let status = 'done';
    if (r < (1 - completionRate)) status = 'planned';
    else if (r < (1 - completionRate) + 0.05) status = 'skipped';
    else if (r < (1 - completionRate) + 0.10) status = 'partial';
    return {
      id: `gen_${athlete.id}_${dateKey(date)}_${i}`,
      athleteId: athlete.id,
      date: dateKey(date),
      title: meal.title,
      timing: meal.timing,
      kcal, carbs, protein, status
    };
  });
}

// 30日分のサイクル（typicalな週: Mon-Tue練習, Wed normal, Thu-Fri練習, Sat pre_game, Sun game, 翌Mon recovery）
function generateDayMode(date) {
  const day = date.getDay(); // 0=Sun
  if (day === 0) return 'game';
  if (day === 6) return 'pre_game';
  if (day === 1) return 'recovery';
  if (day === 3) return 'normal';
  return 'practice'; // Tue, Thu, Fri
}

function generate30DaysData(today) {
  const plans = [];
  const checkins = {}; // athleteId -> dateKey -> checkin
  const dayModes = {}; // athleteId -> dateKey -> dayMode

  for (const athlete of ATHLETES) {
    checkins[athlete.id] = {};
    dayModes[athlete.id] = {};
    for (let i = 29; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      const dk = dateKey(date);
      const dayMode = generateDayMode(date);

      // チェックイン
      const sleepBase = athlete.sportId === 'ballet' ? 6.5 : 7.0;
      const fatigueBase = dayMode === 'recovery' ? 4 : (dayMode === 'game' ? 3 : 2);
      const appetiteBase = dayMode === 'game' ? 2 : 3;

      checkins[athlete.id][dk] = {
        sleepHours: Math.round((sleepBase + (Math.random() - 0.5) * 1.5) * 10) / 10,
        fatigue: Math.max(1, Math.min(5, fatigueBase + Math.floor((Math.random() - 0.5) * 2))),
        appetite: Math.max(1, Math.min(5, appetiteBase + Math.floor((Math.random() - 0.5) * 2))),
        weight: athlete.baselineWeight + Math.round((Math.random() - 0.5) * 0.8 * 10) / 10,
        note: ''
      };

      dayModes[athlete.id][dk] = dayMode;

      // プラン
      plans.push(...generatePlansForDay(athlete, date, dayMode));
    }
  }

  return { plans, checkins, dayModes };
}

// 期待される栄養目標（科学的妥当性チェック用）
function expectedTargets(athlete, dayMode) {
  const targets = {
    track: { normal: [5,6], practice: [6,8], pre_game: [7,10], game: [6,8], recovery: [5,7], protein: [1.4, 1.8] },
    soccer: { normal: [5,7], practice: [6,8], pre_game: [7,10], game: [6,8], recovery: [5,7], protein: [1.4, 1.8] },
    ballet: { normal: [4,5], practice: [5,6], pre_game: [5,6], game: [5,6], recovery: [4,5], protein: [1.4, 1.8] },
    swimming: { normal: [5,7], practice: [6,10], pre_game: [7,10], game: [6,8], recovery: [5,7], protein: [1.4, 2.0] }
  };
  const t = targets[athlete.sportId];
  const w = athlete.baselineWeight;
  return {
    carbs: { min: Math.round(t[dayMode][0] * w), max: Math.round(t[dayMode][1] * w) },
    protein: { min: Math.round(t.protein[0] * w), max: Math.round(t.protein[1] * w) }
  };
}

// ===== 実行 =====
(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();

  const consoleErrors = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => consoleErrors.push('PAGE: ' + e.message));

  await page.goto('http://localhost:5173/');
  await page.evaluate(() => localStorage.clear());

  // 30日データを生成して localStorage に注入
  const today = new Date();
  const { plans, checkins, dayModes } = generate30DaysData(today);

  await page.evaluate(({ athletes, plans, checkins, dayModes }) => {
    localStorage.setItem('athletes', JSON.stringify(athletes));
    localStorage.setItem('plans', JSON.stringify(plans));
    localStorage.setItem('athlete-checkins', JSON.stringify(checkins));
    localStorage.setItem('athlete-day-modes', JSON.stringify(dayModes));
  }, { athletes: ATHLETES, plans, checkins, dayModes });

  console.log(`\n${'='.repeat(60)}\n30日データ注入完了`);
  console.log(`  - athletes: ${ATHLETES.length}名`);
  console.log(`  - plans: ${plans.length}件（4名 × 30日 × 5食 = ${4*30*5}件想定）`);
  console.log(`  - checkins: ${Object.keys(checkins).map(a => Object.keys(checkins[a]).length).reduce((a,b)=>a+b,0)}件`);
  console.log(`${'='.repeat(60)}\n`);

  await page.reload();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);

  // ===== Phase 1: 各スポーツの今日のサマリーとAIコメントを検証 =====
  for (const athlete of ATHLETES) {
    console.log(`\n${'━'.repeat(60)}`);
    console.log(`■ ${athlete.name} (${athlete.sportId}, ${athlete.baselineWeight}kg)`);
    console.log(`  Focus: ${athlete.focus}`);
    console.log('━'.repeat(60));

    // 選手を選択
    await page.evaluate((id) => localStorage.setItem('selected-athlete-id', JSON.stringify(id)), athlete.id);
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(800);

    const todayDk = dateKey(today);
    const todayMode = dayModes[athlete.id][todayDk];
    const expected = expectedTargets(athlete, todayMode);
    console.log(`\n  [今日の Day Mode] ${todayMode}`);
    console.log(`  [科学的目標値] 糖質 ${expected.carbs.min}-${expected.carbs.max}g, たんぱく質 ${expected.protein.min}-${expected.protein.max}g`);

    // 画面の数値をスクレイプ
    const summary = await page.evaluate(() => {
      const labels = ['kcal', '糖質', 'たんぱく質'];
      const ret = {};
      // サマリーカード内の数値抽出
      const cards = document.querySelectorAll('.glass');
      for (const card of cards) {
        const t = card.textContent || '';
        const k = t.match(/kcal\s*(\d+)/);
        const c = t.match(/糖質\s*(\d+)g/);
        const p = t.match(/たんぱく質\s*(\d+)g/);
        if (k && !ret.kcal) ret.kcal = parseInt(k[1]);
        if (c && !ret.carbs) ret.carbs = parseInt(c[1]);
        if (p && !ret.protein) ret.protein = parseInt(p[1]);
      }
      return ret;
    });
    console.log(`  [画面表示] kcal=${summary.kcal}, 糖質=${summary.carbs}g, たんぱく質=${summary.protein}g`);

    // 妥当性判定
    const carbsInRange = summary.carbs >= expected.carbs.min * 0.7 && summary.carbs <= expected.carbs.max * 1.3;
    const proteinInRange = summary.protein >= expected.protein.min * 0.7 && summary.protein <= expected.protein.max * 1.3;
    console.log(`  [判定] 糖質範囲: ${carbsInRange ? '✅ 妥当' : '⚠️  ターゲット外'}, たんぱく質: ${proteinInRange ? '✅ 妥当' : '⚠️  ターゲット外'}`);

    // AI コーチコメントを取得
    const coachComments = await page.evaluate(() => {
      const heading = Array.from(document.querySelectorAll('h3, h4')).find(h => /coach|AI/i.test(h.textContent || ''));
      if (!heading) return null;
      const panel = heading.closest('.glass');
      if (!panel) return null;
      const items = panel.querySelectorAll('div[class*="rounded"]');
      const result = [];
      items.forEach(item => {
        const text = (item.textContent || '').trim();
        if (text.length > 10 && text.length < 300) result.push(text);
      });
      return result.slice(0, 5);
    });
    if (coachComments && coachComments.length > 0) {
      console.log(`  [AIコメント]`);
      coachComments.forEach((c, i) => console.log(`    ${i+1}. ${c.replace(/\s+/g, ' ').slice(0, 120)}`));
      const trendText = coachComments.join(' ');
      recordCheck(`${athlete.name} AIコメントにトレンド文言`, /過去|7日|14日|3日連続|2週間|この1週間/.test(trendText), trendText.replace(/\s+/g, ' ').slice(0, 120));
    } else {
      console.log(`  [AIコメント] 取得できず`);
      recordCheck(`${athlete.name} AIコメント取得`, false);
    }

    // コンビニ代替案（NutritionCard 内）
    const suggestions = await page.evaluate(() => {
      const cards = document.querySelectorAll('div.glass');
      const list = [];
      cards.forEach(card => {
        const text = card.textContent || '';
        const m = text.match(/コンビニ代替案([^\.]{5,200})/);
        if (m) {
          const meal = text.match(/(朝食|昼食|補食|夕食)/)?.[1] ?? '不明';
          const options = m[1].trim().split('/').map(s => s.trim()).filter(Boolean);
          list.push({ meal, first: options[0] ?? '', text: m[1].trim().slice(0, 150) });
        }
      });
      return list.slice(0, 4);
    });
    console.log(`  [コンビニ代替案 サンプル]`);
    suggestions.forEach((s, i) => console.log(`    ${i+1}. ${s.meal}: ${s.text.replace(/\s+/g, ' ')}`));
    const nonSnackSuggestions = suggestions.filter(s => ['朝食', '昼食', '夕食'].includes(s.meal));
    const hasSportsDrinkAtMealHead = nonSnackSuggestions.some(s => /スポーツドリンク|スポドリ/.test(s.first));
    recordCheck(`${athlete.name} 朝昼夕の代替案先頭にスポドリなし`, !hasSportsDrinkAtMealHead, nonSnackSuggestions.map(s => `${s.meal}:${s.first}`).join(' / '));

    // スクリーンショット
    await page.screenshot({ path: path.join(__dirname, `content-${athlete.sportId}-today.png`), fullPage: true });
  }

  // ===== Phase 2: 30日カレンダーが正しく描画されるか =====
  console.log(`\n${'━'.repeat(60)}`);
  console.log('■ 30日カレンダー検証 (Haruka)');
  console.log('━'.repeat(60));
  await page.evaluate(() => localStorage.setItem('selected-athlete-id', JSON.stringify('a1')));
  await page.reload();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(800);

  const calendarStats = await page.evaluate(() => {
    const cells = document.querySelectorAll('button[aria-label^="select "]');
    let withData = 0, total = 0, withDot = 0;
    cells.forEach(cell => {
      total++;
      if (cell.querySelector('div[title]')) withData++;  // dayMode bar
      if (cell.querySelector('span.bg-neon-500')) withDot++; // today
    });
    return { total, withData, withDot };
  });
  console.log(`  カレンダーセル総数: ${calendarStats.total}`);
  console.log(`  Day Mode バーがあるセル: ${calendarStats.withData}件 (= 30日分の記録)`);
  console.log(`  今日マーク(青ドット)があるセル: ${calendarStats.withDot}件`);
  console.log(`  [判定] ${calendarStats.withData >= 25 && calendarStats.withDot === 1 ? '✅ 妥当' : '⚠️  数値が想定外'}`);
  await page.screenshot({ path: path.join(__dirname, 'content-calendar.png'), fullPage: true });

  // ===== Phase 3: 分析グラフで30日のデータが反映されているか =====
  console.log(`\n${'━'.repeat(60)}`);
  console.log('■ 分析パネル (Bar Chart)');
  console.log('━'.repeat(60));
  const chartInfo = await page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    if (!canvas) return null;
    return { width: canvas.width, height: canvas.height };
  });
  console.log(`  Canvas: ${chartInfo?.width}x${chartInfo?.height}`);
  console.log(`  [判定] ${chartInfo && chartInfo.width > 100 ? '✅ 描画OK' : '⚠️  未描画'}`);
  recordCheck('分析グラフcanvas描画', !!chartInfo && chartInfo.width > 100, chartInfo ? `${chartInfo.width}x${chartInfo.height}` : 'canvasなし');

  const analysisMeta = await page.evaluate(() => {
    const chart = document.querySelector('[data-testid="analysis-chart"]');
    const tabs = Array.from(document.querySelectorAll('button')).map(button => button.textContent?.trim()).filter(text => ['カロリー', '糖質', 'たんぱく質', '完了率'].includes(text || ''));
    return {
      days: Number(chart?.getAttribute('data-days') ?? 0),
      recordedDays: Number(chart?.getAttribute('data-recorded-days') ?? 0),
      tabs
    };
  });
  recordCheck('分析グラフが30日レンジを持つ', analysisMeta.days === 30 && analysisMeta.recordedDays >= 20, `days=${analysisMeta.days}, recorded=${analysisMeta.recordedDays}`);
  recordCheck('分析グラフ4タブ表示', analysisMeta.tabs.length >= 4, analysisMeta.tabs.join(', '));

  // ===== Phase 4: 過去日付（5日前など）にカレンダーから遷移してプランが表示されるか =====
  console.log(`\n${'━'.repeat(60)}`);
  console.log('■ 過去日付の閲覧');
  console.log('━'.repeat(60));
  const fiveDaysAgo = new Date(today);
  fiveDaysAgo.setDate(today.getDate() - 5);
  const pastKey = dateKey(fiveDaysAgo);
  console.log(`  対象日: ${pastKey} (5日前)`);

  const pastCell = page.locator(`button[aria-label="select ${pastKey}"]`);
  const found = await pastCell.isVisible({ timeout: 2000 }).catch(() => false);
  if (found) {
    await pastCell.click();
    await page.waitForTimeout(500);
    const summary = await page.evaluate(() => {
      const cards = document.querySelectorAll('.glass');
      for (const card of cards) {
        const t = card.textContent || '';
        const k = t.match(/kcal\s*(\d+)/);
        const c = t.match(/糖質\s*(\d+)g/);
        if (k && c) return { kcal: parseInt(k[1]), carbs: parseInt(c[1]) };
      }
      return null;
    });
    console.log(`  ${pastKey} のサマリー: kcal=${summary?.kcal}, 糖質=${summary?.carbs}g`);
    console.log(`  [判定] ${summary && summary.kcal > 0 ? '✅ 過去日のデータが表示' : '⚠️  データなし'}`);
    await page.screenshot({ path: path.join(__dirname, 'content-past-day.png'), fullPage: true });
  } else {
    console.log(`  [判定] ⚠️  5日前のセルがカレンダーに見えない`);
  }

  // ===== 終了 =====
  console.log(`\n${'━'.repeat(60)}`);
  console.log(`コンソールエラー: ${consoleErrors.length}件`);
  consoleErrors.slice(0, 5).forEach(e => console.log('  -', e.slice(0, 150)));
  recordCheck('コンソールエラーなし', consoleErrors.length === 0, `${consoleErrors.length}件`);
  const pass = checks.filter(check => check.ok).length;
  const fail = checks.filter(check => !check.ok).length;
  console.log(`\n===== CONTENT VERIFY TOTAL: PASS=${pass} / FAIL=${fail} =====`);
  if (fail > 0) {
    process.exitCode = 1;
  }
  console.log('━'.repeat(60));

  await browser.close();
})();
