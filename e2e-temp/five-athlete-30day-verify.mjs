import { chromium } from 'playwright';

function pad(n) {
  return String(n).padStart(2, '0');
}

function dateKey(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

const checks = [];

function check(label, ok, detail = '') {
  checks.push({ label, ok, detail });
  console.log(`${ok ? '✅' : '❌'} ${label}${detail ? `: ${detail}` : ''}`);
}

const ATHLETES = [
  { id: 'a1', name: 'Haruka Tanaka', sportId: 'track', focus: '400mの週末レースに向けてエネルギー切れを防ぐ', baselineWeight: 56.8 },
  { id: 'a2', name: 'Ren Ito', sportId: 'soccer', focus: '連戦でも後半のスプリント強度を落とさない', baselineWeight: 68.2 },
  { id: 'a3', name: 'Airi Nakamura', sportId: 'ballet', focus: 'リハーサル量が多い週でも回復と骨コンディションを守る', baselineWeight: 50.4 },
  { id: 'a4', name: 'Kenta Saito', sportId: 'swimming', focus: '朝練後の回復と体重維持を安定させる', baselineWeight: 72.4 },
  { id: 'a5', name: 'Mika Watanabe', sportId: 'basketball', focus: '連戦でもジャンプと切り返しの強度を落とさない', baselineWeight: 61.5 }
];

const CARB_TARGETS = {
  track: { normal: [5, 6], practice: [6, 8], pre_game: [7, 10], game: [6, 8], recovery: [5, 7], protein: [1.4, 1.8] },
  soccer: { normal: [5, 7], practice: [6, 8], pre_game: [7, 10], game: [6, 8], recovery: [5, 7], protein: [1.4, 1.8] },
  ballet: { normal: [4, 5], practice: [5, 6], pre_game: [5, 6], game: [5, 6], recovery: [4, 5], protein: [1.4, 1.8] },
  swimming: { normal: [5, 7], practice: [6, 10], pre_game: [7, 10], game: [6, 8], recovery: [5, 7], protein: [1.4, 2.0] },
  basketball: { normal: [5, 6], practice: [6, 8], pre_game: [6, 8], game: [6, 8], recovery: [5, 7], protein: [1.4, 1.8] }
};

function dayModeFor(date) {
  const day = date.getDay();
  if (day === 0) return 'game';
  if (day === 6) return 'pre_game';
  if (day === 1) return 'recovery';
  if (day === 3) return 'normal';
  return 'practice';
}

function mealTemplates(athlete) {
  const templates = [
    { timing: 'Breakfast', title: '朝食 ごはん+魚+味噌汁', ratio: 0.25 },
    { timing: 'Snack', title: '練習前補食 おにぎり+バナナ', ratio: 0.15 },
    { timing: 'Lunch', title: '昼食 親子丼+サラダ', ratio: 0.30 },
    { timing: 'Snack', title: '練習後補食 プロテイン+果物', ratio: 0.10 },
    { timing: 'Dinner', title: '夕食 ごはん+鶏+野菜', ratio: 0.20 }
  ];

  if (athlete.sportId === 'ballet') {
    templates[0].title = '朝食 シリアル+ヨーグルト+果物';
    templates[3].title = '間食 ヨーグルト+ナッツ';
  }
  if (athlete.sportId === 'swimming') {
    templates[1].title = '朝練後補食 ベーグル+ジュース';
    templates[3].title = '夕練後補食 おにぎり+プロテインドリンク';
  }
  if (athlete.sportId === 'basketball') {
    templates[1].title = '練習前補食 バナナ+ゼリー';
    templates[3].title = '練習後補食 チキンサンド+ミルク';
  }
  if (athlete.sportId === 'soccer') {
    templates[1].title = '練習前補食 あんぱん+スポーツドリンク';
  }

  return templates;
}

function generatePlansForDay(athlete, date, dayMode, dayOffset) {
  const target = CARB_TARGETS[athlete.sportId];
  const carbPerKg = (target[dayMode][0] + target[dayMode][1]) / 2;
  const proteinPerKg = (target.protein[0] + target.protein[1]) / 2;
  const dailyCarbs = Math.round(carbPerKg * athlete.baselineWeight);
  const dailyProtein = Math.round(proteinPerKg * athlete.baselineWeight);
  const dailyFat = Math.round(athlete.baselineWeight * 0.8);
  const dailyKcal = dailyCarbs * 4 + dailyProtein * 4 + dailyFat * 9;

  return mealTemplates(athlete).map((meal, mealIndex) => {
    let status = 'done';
    if ((dayOffset + mealIndex + athlete.id.length) % 13 === 0) status = 'skipped';
    else if ((dayOffset + mealIndex) % 7 === 0) status = 'partial';
    else if ((dayOffset + mealIndex) % 11 === 0) status = 'planned';

    return {
      id: `five_${athlete.id}_${dateKey(date)}_${mealIndex}`,
      athleteId: athlete.id,
      date: dateKey(date),
      title: meal.title,
      timing: meal.timing,
      kcal: Math.round(dailyKcal * meal.ratio),
      carbs: Math.round(dailyCarbs * meal.ratio),
      protein: Math.round(dailyProtein * meal.ratio),
      status
    };
  });
}

function generate30Days(today) {
  const plans = [];
  const checkins = {};
  const dayModes = {};

  for (const athlete of ATHLETES) {
    checkins[athlete.id] = {};
    dayModes[athlete.id] = {};

    for (let offset = 29; offset >= 0; offset--) {
      const date = new Date(today);
      date.setDate(today.getDate() - offset);
      const key = dateKey(date);
      const dayMode = dayModeFor(date);
      const fatigueBase = dayMode === 'recovery' ? 4 : dayMode === 'game' ? 3 : 2;
      const sleepBase = athlete.sportId === 'ballet' ? 6.7 : 7.2;

      dayModes[athlete.id][key] = dayMode;
      checkins[athlete.id][key] = {
        sleepHours: Math.round((sleepBase + ((offset % 5) - 2) * 0.18) * 10) / 10,
        fatigue: Math.max(1, Math.min(5, fatigueBase + (offset % 3 === 0 ? 1 : 0))),
        appetite: Math.max(1, Math.min(5, 4 - (dayMode === 'game' ? 1 : 0))),
        weight: athlete.baselineWeight + Math.round(((offset % 7) - 3) * 0.12 * 10) / 10,
        note: `${athlete.name} day ${30 - offset}`
      };
      plans.push(...generatePlansForDay(athlete, date, dayMode, offset));
    }
  }

  return { plans, checkins, dayModes };
}

function countNestedRecords(record) {
  return Object.values(record).reduce((sum, dates) => sum + Object.keys(dates).length, 0);
}

async function panelText(page, headingRegex) {
  return page.evaluate((source) => {
    const regex = new RegExp(source, 'i');
    const heading = Array.from(document.querySelectorAll('h3, h4')).find((node) => regex.test(node.textContent || ''));
    return heading?.closest('.glass')?.textContent || '';
  }, headingRegex.source);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 1100 } });
  const page = await ctx.newPage();
  const consoleErrors = [];
  const pageErrors = [];

  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => pageErrors.push(error.message));

  console.log('\n===== 起動確認 =====');
  await page.goto('http://127.0.0.1:5173/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(800);

  const initialText = await page.evaluate(() => document.body.textContent || '');
  check('アプリが起動し、タイトルが表示される', /Athlete Nutrition|本番逆算型スポーツ栄養/.test(initialText));
  check('初期画面で主要パネルが表示される', [
    /Calendar/,
    /Analysis/,
    /AI Coach Notes|Coach Notes MVP/,
    /Buddy Check/,
    /Reminder Scheduler/
  ].every((regex) => regex.test(initialText)));

  console.log('\n===== 5人 x 30日データ注入 =====');
  const today = new Date();
  const { plans, checkins, dayModes } = generate30Days(today);
  await page.evaluate(({ athletes, plans, checkins, dayModes }) => {
    localStorage.setItem('athletes', JSON.stringify(athletes));
    localStorage.setItem('plans', JSON.stringify(plans));
    localStorage.setItem('athlete-checkins', JSON.stringify(checkins));
    localStorage.setItem('athlete-day-modes', JSON.stringify(dayModes));
    localStorage.setItem('selected-athlete-id', JSON.stringify('a1'));
    localStorage.removeItem('ctoc-reminders');
  }, { athletes: ATHLETES, plans, checkins, dayModes });
  await page.reload();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(900);

  check('5人分のathletesを投入', ATHLETES.length === 5, `${ATHLETES.length}人`);
  check('5人 x 30日 x 5食 = 750件のplansを投入', plans.length === 750, `${plans.length}件`);
  check('5人 x 30日 = 150件のcheckinsを投入', countNestedRecords(checkins) === 150, `${countNestedRecords(checkins)}件`);
  check('5人 x 30日 = 150件のdayModesを投入', countNestedRecords(dayModes) === 150, `${countNestedRecords(dayModes)}件`);

  console.log('\n===== 選手別・項目別検証 =====');
  for (const athlete of ATHLETES) {
    await page.evaluate((id) => localStorage.setItem('selected-athlete-id', JSON.stringify(id)), athlete.id);
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(700);

    const bodyText = await page.evaluate(() => document.body.textContent || '');
    const todayKey = dateKey(today);
    const expectedTodayPlans = plans.filter((plan) => plan.athleteId === athlete.id && plan.date === todayKey);
    const expectedKcal = expectedTodayPlans.reduce((sum, plan) => sum + plan.kcal, 0);
    const expectedCarbs = expectedTodayPlans.reduce((sum, plan) => sum + plan.carbs, 0);
    const expectedProtein = expectedTodayPlans.reduce((sum, plan) => sum + plan.protein, 0);

    console.log(`\n--- ${athlete.name} (${athlete.sportId}) ---`);
    check(`${athlete.name}: 選手名とフォーカス表示`, bodyText.includes(athlete.name) && bodyText.includes(athlete.focus));
    check(`${athlete.name}: 今日の5食プラン表示`, expectedTodayPlans.every((plan) => bodyText.includes(plan.title)), `${expectedTodayPlans.length}食`);
    check(`${athlete.name}: サマリーkcal/糖質/たんぱく質表示`, bodyText.includes(String(expectedKcal)) && bodyText.includes(`${expectedCarbs}g`) && bodyText.includes(`${expectedProtein}g`), `${expectedKcal}kcal / ${expectedCarbs}g / ${expectedProtein}g`);

    const calendarStats = await page.evaluate(() => {
      const cells = document.querySelectorAll('button[aria-label^="select "]');
      let withData = 0;
      cells.forEach((cell) => {
        if (cell.querySelector('div[title]')) withData += 1;
      });
      return { total: cells.length, withData };
    });
    check(`${athlete.name}: カレンダー42セル`, calendarStats.total === 42, `${calendarStats.total}セル`);
    check(`${athlete.name}: 30日記録がカレンダーに反映`, calendarStats.withData >= 25, `${calendarStats.withData}日`);

    const analysis = await page.evaluate(() => {
      const chart = document.querySelector('[data-testid="analysis-chart"]');
      const tabs = Array.from(document.querySelectorAll('button')).map((button) => button.textContent?.trim());
      return {
        days: Number(chart?.getAttribute('data-days') || 0),
        recordedDays: Number(chart?.getAttribute('data-recorded-days') || 0),
        hasCanvas: Boolean(document.querySelector('canvas')),
        hasTabs: ['カロリー', '糖質', 'たんぱく質', '完了率'].every((label) => tabs.includes(label))
      };
    });
    check(`${athlete.name}: 分析パネル30日レンジ`, analysis.days === 30 && analysis.recordedDays === 30 && analysis.hasCanvas, `days=${analysis.days}, recorded=${analysis.recordedDays}`);
    check(`${athlete.name}: 分析4タブ`, analysis.hasTabs);

    const aiText = await panelText(page, /coach|AI/);
    check(`${athlete.name}: AIコメント表示`, aiText.length > 30, aiText.replace(/\s+/g, ' ').slice(0, 90));
    check(`${athlete.name}: AIコメントにトレンド文言`, /過去|7日|3日連続|2週間|この1週間/.test(aiText), aiText.replace(/\s+/g, ' ').slice(0, 90));

    const buddyText = await panelText(page, /Buddy Check/);
    check(`${athlete.name}: Buddy Check / Pair Score / Cheer Stamps表示`, buddyText.includes('Pair Score') && buddyText.includes('Cheer Stamps') && /%/.test(buddyText));

    const foodLogText = await panelText(page, /Team Food Log/);
    check(`${athlete.name}: Team Food Log表示`, foodLogText.includes('Team Food Log') && foodLogText.includes('真似する') && foodLogText.includes('リマインドに追加'));

    const reminderText = await panelText(page, /Reminder Scheduler/);
    check(`${athlete.name}: Reminder Scheduler表示`, reminderText.includes('リマインド予約') && reminderText.includes('予約済みリマインド'));
  }

  console.log('\n===== CtoC操作確認 =====');
  await page.evaluate(() => localStorage.setItem('selected-athlete-id', JSON.stringify('a1')));
  await page.reload();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(700);
  await page.getByRole('button', { name: 'リマインドに追加' }).first().click();
  await page.waitForTimeout(200);
  const remindersAfterFoodLog = await page.evaluate(() => JSON.parse(localStorage.getItem('ctoc-reminders') || '[]').length);
  check('Team Food Logからリマインド追加', remindersAfterFoodLog >= 1, `${remindersAfterFoodLog}件`);
  await page.getByRole('button', { name: 'リマインド予約' }).click();
  await page.waitForTimeout(200);
  const remindersAfterManual = await page.evaluate(() => JSON.parse(localStorage.getItem('ctoc-reminders') || '[]').length);
  check('Reminder Schedulerから手動予約', remindersAfterManual >= remindersAfterFoodLog + 1, `${remindersAfterManual}件`);
  await page.getByRole('button', { name: 'send ナイス補食' }).click();
  await page.waitForTimeout(100);
  const stampVisible = await page.evaluate(() => (document.body.textContent || '').includes('ナイス補食 →'));
  check('Cheer Stampsの履歴表示', stampVisible);

  console.log('\n===== エラー確認 =====');
  check('console error 0件', consoleErrors.length === 0, `${consoleErrors.length}件`);
  check('pageerror 0件', pageErrors.length === 0, `${pageErrors.length}件`);

  const pass = checks.filter((item) => item.ok).length;
  const fail = checks.filter((item) => !item.ok).length;
  console.log(`\n===== FIVE ATHLETE 30DAY VERIFY: PASS=${pass} / FAIL=${fail} =====`);
  if (fail > 0) {
    process.exitCode = 1;
  }

  await browser.close();
})();
