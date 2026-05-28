// 本番逆算 / Event Fueling パネルの動作検証
import { chromium } from 'playwright';

const APP_URL = 'http://localhost:5173/';

const results = [];
function log(category, status, msg, detail = '') {
  results.push({ category, status, msg, detail });
  const icon = status === 'PASS' ? '✅' : status === 'FAIL' ? '❌' : status === 'WARN' ? '⚠️ ' : '🔵';
  console.log(`${icon} [${category}] ${msg}${detail ? '\n   ' + detail : ''}`);
}

function pad(n) {
  return String(n).padStart(2, '0');
}

function dateKey(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function addDays(date, days) {
  const next = new Date(date);
  next.setDate(date.getDate() + days);
  return next;
}

function compact(text) {
  return (text || '').replace(/\s+/g, ' ').trim();
}

function regexSource(regex) {
  return regex.source;
}

async function firstVisible(candidates, timeout = 500) {
  for (const { label, locator } of candidates) {
    const count = await locator.count().catch(() => 0);
    for (let i = 0; i < Math.min(count, 8); i++) {
      const candidate = locator.nth(i);
      const visible = await candidate.isVisible({ timeout }).catch(() => false);
      if (visible) return { label, locator: candidate };
    }
  }
  return null;
}

async function firstVisibleEnabled(candidates, timeout = 500) {
  for (const { label, locator } of candidates) {
    const count = await locator.count().catch(() => 0);
    for (let i = 0; i < Math.min(count, 8); i++) {
      const candidate = locator.nth(i);
      const visible = await candidate.isVisible({ timeout }).catch(() => false);
      const enabled = visible && await candidate.isEnabled().catch(() => false);
      if (visible && enabled) return { label, locator: candidate };
    }
  }
  return null;
}

async function findEventFuelingScope(page) {
  const candidates = [
    { label: 'data-testid event/fuel', locator: page.locator('[data-testid*="event" i], [data-testid*="fuel" i]').filter({ hasText: /Event Fueling|本番逆算/i }) },
    { label: 'panel container', locator: page.locator('section, article, form, div.glass').filter({ hasText: /Event Fueling|本番逆算/i }) },
    { label: 'main', locator: page.locator('main').filter({ hasText: /Event Fueling|本番逆算/i }) },
    { label: 'body', locator: page.locator('body').filter({ hasText: /Event Fueling|本番逆算/i }) }
  ];
  const found = await firstVisible(candidates, 1500);
  return found?.locator ?? page.locator('body');
}

async function panelText(page) {
  return page.evaluate((headingSource) => {
    const headingRegex = new RegExp(headingSource, 'i');
    const heading = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6')).find((node) =>
      headingRegex.test(node.textContent || '')
    );
    const panel = heading?.closest('[data-testid], section, article, form, .glass, main');
    return (panel?.textContent || document.body.textContent || '').replace(/\s+/g, ' ').trim();
  }, regexSource(/Event Fueling|本番逆算/));
}

async function fillFirst(candidates, value) {
  const target = await firstVisibleEnabled(candidates, 500);
  if (!target) return null;
  await target.locator.fill(value);
  return target.label;
}

async function selectEventType(scope) {
  const select = await firstVisibleEnabled([
    { label: 'event type label', locator: scope.getByLabel(/イベント種別|本番種別|大会種別|種別|race|match|competition/i) },
    { label: 'select[name*=event/kind]', locator: scope.locator('select[name*="event" i], select[name*="kind" i], select[aria-label*="event" i], select[aria-label*="kind" i]') },
    { label: 'first select in panel', locator: scope.locator('select') }
  ]);

  if (select) {
    const option = await select.locator.evaluate((el) => {
      const options = Array.from(el.options);
      return options.find((item) => /レース|試合|大会|マラソン|endurance|race|game|match|competition/i.test(item.textContent || item.value))?.value
        || options.find((item) => item.value)?.value
        || options[0]?.value
        || '';
    });
    if (option) {
      await select.locator.selectOption(option);
      return `select: ${select.label} -> ${option}`;
    }
  }

  const typeButton = await firstVisibleEnabled([
    { label: 'race/match type button', locator: scope.getByRole('button', { name: /レース|試合|大会|マラソン|endurance|race|game|match|competition/i }) },
    { label: 'radio-like type button', locator: scope.locator('button[aria-pressed], [role="radio"], [role="option"]').filter({ hasText: /レース|試合|大会|マラソン|endurance|race|game|match|competition/i }) }
  ]);
  if (typeButton) {
    await typeButton.locator.click();
    return `button: ${typeButton.label}`;
  }

  return null;
}

async function readStorageSnapshot(page, eventName, targetDate) {
  return page.evaluate(({ eventName, targetDate }) => {
    const keys = Object.keys(localStorage);
    const entries = keys.map((key) => {
      const raw = localStorage.getItem(key) || '';
      let parsed = null;
      try {
        parsed = JSON.parse(raw);
      } catch {
        parsed = null;
      }
      return {
        key,
        raw,
        preview: raw.slice(0, 220),
        parsedType: Array.isArray(parsed) ? 'array' : typeof parsed
      };
    });

    const matches = entries.filter((entry) =>
      /event|fuel|race|competition|本番|大会/i.test(entry.key)
      || entry.raw.includes(eventName)
      || entry.raw.includes(targetDate)
    );

    return { keys, matches };
  }, { eventName, targetDate });
}

async function analyzeReversePlan(page) {
  return page.evaluate((headingSource) => {
    const headingRegex = new RegExp(headingSource, 'i');
    const heading = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6')).find((node) =>
      headingRegex.test(node.textContent || '')
    );
    const root = heading?.closest('[data-testid], section, article, form, .glass, main') || document.body;
    const text = root.textContent || '';
    const lines = text.split(/\n+/).map((line) => line.trim()).filter(Boolean);
    const dayPattern = /D\s*[-+]\s*\d|Day\s*[-+]\s*\d|本番\s*(?:前|後|当日|まで)?\s*\d*|前日|当日|翌日|土台作り|カーボローディング|\d{4}-\d{2}-\d{2}|\d{1,2}\/\d{1,2}/i;
    const dayMentionPattern = /-\d日|\+\d日|当日|翌日|前日|土台作り|カーボローディング|\d{4}-\d{2}-\d{2}/g;
    const nutritionPattern = /糖質|カーボ|carb|たんぱく質|protein|\d+\s*g|g\s*\/\s*kg|疲労|体重|kg/i;
    const rowElements = Array.from(root.querySelectorAll('tr, li, article, [data-testid*="day" i], [class*="day" i], [class*="row" i], [class*="plan" i]'));
    const rowTexts = rowElements
      .map((el) => (el.textContent || '').replace(/\s+/g, ' ').trim())
      .filter((item) => item.length > 0 && item.length < 500)
      .filter((item) => dayPattern.test(item) && nutritionPattern.test(item));
    const lineRows = lines.filter((line) => dayPattern.test(line) && nutritionPattern.test(line));
    const dayMentions = (text.match(dayMentionPattern) || []).length;
    return {
      text: text.replace(/\s+/g, ' ').trim(),
      lineRowCount: lineRows.length,
      elementRowCount: rowTexts.length,
      dayMentions,
      samples: [...rowTexts, ...lineRows].slice(0, 5)
    };
  }, regexSource(/Event Fueling|本番逆算/));
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

  const eventName = 'Codex Test Race';
  const targetDate = dateKey(addDays(new Date(), 5));

  console.log('\n===== Event Fueling 起動確認 =====');
  await page.goto(APP_URL);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);

  const initialText = await page.evaluate(() => document.body.textContent || '');
  const eventPanelVisible = /Event Fueling|本番逆算/i.test(initialText);
  log('T1', eventPanelVisible ? 'PASS' : 'FAIL', 'Event Fueling / 本番逆算 パネルが表示', compact(initialText).slice(0, 160));

  const scope = await findEventFuelingScope(page);
  const headingText = await panelText(page);
  log('T1', /Event Fueling|本番逆算/i.test(headingText) ? 'PASS' : 'FAIL', 'パネル本文を取得', headingText.slice(0, 180));

  console.log('\n===== イベント作成 =====');
  try {
    const eventNameFilledBy = await fillFirst([
      { label: 'label: event/name', locator: scope.getByLabel(/イベント名|大会名|本番名|レース名|Event name|event|name|title/i) },
      { label: 'placeholder/aria/name: event/name', locator: scope.locator('input[placeholder*="イベント"], input[placeholder*="大会"], input[placeholder*="本番"], input[placeholder*="レース"], input[placeholder*="event" i], input[placeholder*="race" i], input[aria-label*="イベント"], input[aria-label*="大会"], input[aria-label*="event" i], input[name*="event" i], input[name*="race" i], input[name*="title" i]') },
      { label: 'first text input in panel', locator: scope.locator('input[type="text"], input:not([type])') }
    ], eventName);
    log('T2', eventNameFilledBy ? 'PASS' : 'FAIL', 'イベント名を入力', eventNameFilledBy || '候補inputが見つからない');

    const dateFilledBy = await fillFirst([
      { label: 'label: date', locator: scope.getByLabel(/本番日|開催日|イベント日|日付|Event date|date/i) },
      { label: 'input[type=date]', locator: scope.locator('input[type="date"]') },
      { label: 'placeholder/aria/name: date', locator: scope.locator('input[placeholder*="YYYY" i], input[placeholder*="日付"], input[placeholder*="開催"], input[placeholder*="本番"], input[placeholder*="date" i], input[aria-label*="日付"], input[aria-label*="date" i], input[name*="date" i]') }
    ], targetDate);
    log('T2', dateFilledBy ? 'PASS' : 'FAIL', `イベント日を入力 (${targetDate})`, dateFilledBy || '候補date inputが見つからない');

    const typeResult = await selectEventType(scope);
    log('T2', typeResult ? 'PASS' : 'WARN', 'イベント種別を設定', typeResult || '種別UIが見つからないためスキップ');

    const addButton = await firstVisibleEnabled([
      { label: 'submit button', locator: scope.locator('button[type="submit"]') },
      { label: 'add/create/generate button', locator: scope.getByRole('button', { name: /追加|登録|保存|作成|生成|逆算|Add|Create|Save|Generate|Plan/i }) },
      { label: 'button text fallback', locator: scope.locator('button').filter({ hasText: /追加|登録|保存|作成|生成|逆算|Add|Create|Save|Generate|Plan/i }) }
    ], 800);

    if (addButton) {
      await addButton.locator.click();
      await page.waitForLoadState('networkidle').catch(() => {});
      await page.waitForTimeout(900);
      log('T2', 'PASS', '追加/生成ボタンを押下', addButton.label);
    } else {
      log('T2', 'FAIL', '追加/生成ボタンが見つからない');
    }
  } catch (e) {
    log('T2', 'FAIL', 'イベント作成操作で例外', e.message.slice(0, 220));
  }

  console.log('\n===== 逆算プラン表示 =====');
  const afterText = await panelText(page);
  const requiredTexts = [
    { label: 'Event Fueling または 本番逆算', regex: /Event Fueling|本番逆算/i },
    { label: '本番まで', regex: /本番まで|until\s+event|days?\s+to/i },
    { label: 'カーボローディング', regex: /カーボローディング|carb(?:ohydrate)?\s*loading/i },
    { label: 'g/kg', regex: /g\s*\/\s*kg/i },
    { label: '疲労', regex: /疲労|fatigue/i },
    { label: 'エビデンス', regex: /エビデンス|evidence/i }
  ];
  for (const item of requiredTexts) {
    log('T3', item.regex.test(afterText) ? 'PASS' : 'FAIL', `${item.label} 文言が表示`, afterText.slice(0, 220));
  }

  const planStats = await analyzeReversePlan(page);
  const rowCount = Math.max(planStats.elementRowCount, planStats.lineRowCount, planStats.dayMentions);
  log('T4', rowCount >= 5 ? 'PASS' : 'FAIL', '7日分前後の逆算プラン行が表示', `rows=${rowCount}, elementRows=${planStats.elementRowCount}, lineRows=${planStats.lineRowCount}, dayMentions=${planStats.dayMentions}`);
  if (planStats.samples.length > 0) {
    console.log('  サンプル行:');
    planStats.samples.forEach((sample, index) => console.log(`    ${index + 1}. ${sample.slice(0, 180)}`));
  }

  const hasCarbGrams = /糖質.{0,40}\d+\s*g|\d+\s*g.{0,40}(糖質|カーボ|carb)/i.test(planStats.text);
  const hasProteinGrams = /たんぱく質.{0,40}\d+\s*g|\d+\s*g.{0,40}(たんぱく質|protein)/i.test(planStats.text);
  const hasFatigueOrWeight = /疲労|fatigue|体重|weight|kg/i.test(planStats.text);
  log('T4', hasCarbGrams ? 'PASS' : 'FAIL', '糖質g が確認できる');
  log('T4', hasProteinGrams ? 'PASS' : 'FAIL', 'たんぱく質g が確認できる');
  log('T4', hasFatigueOrWeight ? 'PASS' : 'FAIL', '疲労または体重に関する文言が確認できる');

  console.log('\n===== localStorage 保存確認 =====');
  const storage = await readStorageSnapshot(page, eventName, targetDate);
  const hasSavedEvent = storage.matches.some((entry) =>
    entry.raw.includes(eventName)
    || entry.raw.includes(targetDate)
    || /event|fuel|race|competition|本番|大会/i.test(entry.key)
  );
  log('T5', hasSavedEvent ? 'PASS' : 'FAIL', 'localStorage にイベント関連データが保存', `keys=${storage.keys.join(', ') || '(empty)'}`);
  storage.matches.slice(0, 5).forEach((entry) => {
    console.log(`  storage match: ${entry.key} (${entry.parsedType}) ${entry.preview.replace(/\s+/g, ' ').slice(0, 180)}`);
  });

  console.log('\n===== コンソール/ページエラー =====');
  if (consoleErrors.length === 0) console.log('✅ コンソールエラー 0件');
  else {
    console.log(`❌ コンソールエラー ${consoleErrors.length}件`);
    consoleErrors.slice(0, 8).forEach((error) => console.log('  -', error.slice(0, 200)));
  }
  if (pageErrors.length === 0) console.log('✅ pageerror 0件');
  else {
    console.log(`❌ pageerror ${pageErrors.length}件`);
    pageErrors.slice(0, 8).forEach((error) => console.log('  -', error.slice(0, 200)));
  }

  log('TX', consoleErrors.length === 0 ? 'PASS' : 'FAIL', 'コンソールエラーなし', `${consoleErrors.length}件`);
  log('TX', pageErrors.length === 0 ? 'PASS' : 'FAIL', 'ページエラーなし', `${pageErrors.length}件`);

  const pass = results.filter((result) => result.status === 'PASS').length;
  const fail = results.filter((result) => result.status === 'FAIL').length;
  const warn = results.filter((result) => result.status === 'WARN').length;
  console.log(`\n===== EVENT FUELING TOTAL: PASS=${pass} / FAIL=${fail} / WARN=${warn} =====`);

  await browser.close();
  if (fail > 0) process.exitCode = 1;
})();
