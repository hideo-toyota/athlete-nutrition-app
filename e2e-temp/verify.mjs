import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import path from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_URL = 'http://localhost:5173/';

const results = [];
function log(category, status, msg, detail) {
  results.push({ category, status, msg, detail });
  const icon = status === 'PASS' ? '✅' : status === 'FAIL' ? '❌' : status === 'WARN' ? '⚠️ ' : '🔵';
  console.log(`${icon} [${category}] ${msg}${detail ? '\n   ' + detail : ''}`);
}

async function ss(page, name) {
  const p = path.join(__dirname, `shot-${name}.png`);
  await page.screenshot({ path: p, fullPage: false });
  return p;
}

const consoleErrors = [];
const pageErrors = [];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();

  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => pageErrors.push(e.message));

  // Clear localStorage before each test
  await page.goto(APP_URL);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForLoadState('networkidle');

  // ===== TEST 1: 初期表示が崩れていないか =====
  await page.waitForTimeout(1000);
  const title = await page.title();
  log('T1', title.includes('Athlete') ? 'PASS' : 'FAIL', `タイトル: ${title}`);
  const rootHasChildren = await page.evaluate(() => document.getElementById('root')?.children?.length > 0);
  log('T1', rootHasChildren ? 'PASS' : 'FAIL', `Reactルートにコンポーネントがマウントされた`);
  await ss(page, '01-initial');

  // ===== TEST 2: 「+ New Plan」ボタンで新規プラン保存（前回の致命バグ#1）=====
  try {
    const newPlanBtn = page.locator('button', { hasText: /new plan|新しい|追加/i }).first();
    const visible = await newPlanBtn.isVisible({ timeout: 3000 }).catch(() => false);
    log('T2', visible ? 'PASS' : 'FAIL', `「New Plan」ボタンの存在`);
    if (visible) {
      await newPlanBtn.click();
      await page.waitForTimeout(500);
      await ss(page, '02-newplan-modal');

      // モーダル内のタイトル入力を探す
      const titleInput = page.locator('input').first();
      await titleInput.fill('テスト朝食');

      // 数値入力を全部埋める
      const numberInputs = page.locator('input[type="number"]');
      const numCount = await numberInputs.count();
      log('T2', 'INFO', `数値input数: ${numCount}`);
      for (let i = 0; i < numCount; i++) {
        await numberInputs.nth(i).fill(String(100 + i * 50));
      }

      // 保存ボタン
      const saveBtn = page.locator('button', { hasText: /save|保存/i }).first();
      await saveBtn.click();
      await page.waitForTimeout(800);
      await ss(page, '03-after-save');

      // モーダルが閉じたか
      const modalGone = !(await page.locator('[role="dialog"]').isVisible({ timeout: 1500 }).catch(() => false));
      log('T2', modalGone ? 'PASS' : 'FAIL', `保存後モーダルが閉じた`);

      // 一覧に追加されたか
      const planTextExists = await page.locator('text=テスト朝食').isVisible({ timeout: 2000 }).catch(() => false);
      log('T2', planTextExists ? 'PASS' : 'FAIL', `「テスト朝食」が一覧に表示された`);

      // localStorage に保存されたか
      const stored = await page.evaluate(() => {
        const raw = localStorage.getItem('plans');
        if (!raw) return null;
        try { return JSON.parse(raw); } catch { return 'parse-error'; }
      });
      const hasTestPlan = Array.isArray(stored) && stored.some(p => p.title === 'テスト朝食');
      log('T2', hasTestPlan ? 'PASS' : 'FAIL',
        `localStorage の plans に「テスト朝食」が含まれる`,
        `件数=${Array.isArray(stored) ? stored.length : 'N/A'}`);
    }
  } catch (e) {
    log('T2', 'FAIL', '新規プラン保存テストで例外', e.message);
  }

  // ===== TEST 3: NaN混入対策（前回の致命バグ#2）=====
  try {
    const newPlanBtn = page.locator('button', { hasText: /new plan|新しい|追加/i }).first();
    await newPlanBtn.click();
    await page.waitForTimeout(500);
    const titleInput = page.locator('input[type="text"]').first();
    await titleInput.fill('NaNテスト');

    // 数値欄を全部空にする
    const numberInputs = page.locator('input[type="number"]');
    const numCount = await numberInputs.count();
    for (let i = 0; i < numCount; i++) {
      await numberInputs.nth(i).fill('');
    }

    const saveBtn = page.locator('button', { hasText: /save|保存/i }).first();
    await saveBtn.click();
    await page.waitForTimeout(500);

    // バリデーションエラーが出るはず
    const errorText = await page.locator('text=/kcal|0 より大きい|必須|エラー/i').first().textContent({ timeout: 2000 }).catch(() => null);
    log('T3', errorText ? 'PASS' : 'FAIL', `空欄保存時にバリデーションエラーが表示される`, errorText || 'メッセージ無し');
    await ss(page, '04-nan-validation');

    // localStorage に NaN が混入していないか
    const noNaN = await page.evaluate(() => {
      const raw = localStorage.getItem('plans');
      if (!raw) return true;
      try {
        const plans = JSON.parse(raw);
        return !plans.some(p => Number.isNaN(p.kcal) || Number.isNaN(p.carbs) || Number.isNaN(p.protein));
      } catch { return false; }
    });
    log('T3', noNaN ? 'PASS' : 'FAIL', `localStorage に NaN が混入していない`);

    // モーダルを閉じる（Cancel）
    const cancelBtn = page.locator('button', { hasText: /cancel|キャンセル/i }).first();
    const cancelVisible = await cancelBtn.isVisible().catch(() => false);
    if (cancelVisible) {
      await cancelBtn.click();
      // dirty confirm が出るかも
      page.once('dialog', async d => { await d.accept(); });
      await page.waitForTimeout(500);
    }
  } catch (e) {
    log('T3', 'FAIL', 'NaN混入テストで例外', e.message);
  }

  // ===== TEST 4: Chart.js BarController（前回の致命バグ#3）=====
  // 分析パネルが落ちずに描画できるか
  try {
    await page.waitForTimeout(500);
    // canvas が存在するか
    const canvasCount = await page.locator('canvas').count();
    log('T4', canvasCount > 0 ? 'PASS' : 'WARN', `分析グラフ用canvasが存在: ${canvasCount}個`);

    // Chart.jsエラーが pageErrors にないか
    const chartErrs = [...consoleErrors, ...pageErrors].filter(e =>
      /chart|controller|registered/i.test(e));
    log('T4', chartErrs.length === 0 ? 'PASS' : 'FAIL',
      `Chart.js エラー無し`,
      chartErrs.join('\n   '));
    await ss(page, '05-chart');
  } catch (e) {
    log('T4', 'FAIL', 'Chart.jsテストで例外', e.message);
  }

  // ===== TEST 5: ID衝突対策（前回の致命バグ#4）=====
  // 連続でプランを5個作って ID 重複がないか
  try {
    const ids = [];
    for (let i = 0; i < 3; i++) {
      const newPlanBtn = page.locator('button', { hasText: /new plan|新しい|追加/i }).first();
      await newPlanBtn.click();
      await page.waitForTimeout(150);
      await page.locator('input[type="text"]').first().fill(`連打${i}`);
      const numberInputs = page.locator('input[type="number"]');
      const numCount = await numberInputs.count();
      for (let j = 0; j < numCount; j++) {
        await numberInputs.nth(j).fill(String(200));
      }
      await page.locator('button', { hasText: /save|保存/i }).first().click();
      await page.waitForTimeout(80); // 同一ミリ秒近接
    }
    const allIds = await page.evaluate(() => {
      const raw = localStorage.getItem('plans');
      if (!raw) return [];
      try { return JSON.parse(raw).map(p => p.id); } catch { return []; }
    });
    const unique = new Set(allIds);
    log('T5', allIds.length === unique.size ? 'PASS' : 'FAIL',
      `Plan ID重複なし`,
      `件数=${allIds.length}, ユニーク=${unique.size}, サンプル=${allIds.slice(0,3).join(',')}`);
  } catch (e) {
    log('T5', 'FAIL', 'ID衝突テストで例外', e.message);
  }

  // ===== TEST 6: selectedAthleteId 永続化（前回の致命バグ#5）=====
  try {
    // 選手リストがあれば2人目をクリック
    const athleteCards = page.locator('[role="button"]:has-text("kg")').or(page.locator('article')).or(page.locator('[data-athlete]'));
    const count = await athleteCards.count().catch(() => 0);
    log('T6', 'INFO', `選手カード候補: ${count}`);

    // とりあえず localStorage の selected-athlete-id を直接書き換えて検証
    const athletes = await page.evaluate(() => {
      const raw = localStorage.getItem('athletes');
      return raw ? JSON.parse(raw) : null;
    });
    log('T6', athletes && athletes.length >= 2 ? 'PASS' : 'INFO',
      `選手データ件数: ${athletes?.length || 0}`);

    if (athletes && athletes.length >= 2) {
      const secondId = athletes[1].id;
      await page.evaluate((id) => localStorage.setItem('selected-athlete-id', JSON.stringify(id)), secondId);
      await page.reload();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(800);
      const after = await page.evaluate(() => {
        const raw = localStorage.getItem('selected-athlete-id');
        return raw ? JSON.parse(raw) : null;
      });
      log('T6', after === secondId ? 'PASS' : 'FAIL',
        `リロード後も selected-athlete-id が保持される`,
        `期待=${secondId}, 実際=${after}`);
    }
  } catch (e) {
    log('T6', 'FAIL', '選手永続化テストで例外', e.message);
  }

  // ===== TEST 7: A-1 新規バグ - mock.tsのTODAY定数固定問題 =====
  // 起動直後、初期プランのdateフィールドが今日になっているか
  try {
    const todayKey = await page.evaluate(() => {
      const d = new Date();
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
    });
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(800);
    const initPlans = await page.evaluate(() => {
      const raw = localStorage.getItem('plans');
      return raw ? JSON.parse(raw) : null;
    });
    const allToday = initPlans && initPlans.every(p => p.date === todayKey);
    log('T7', allToday ? 'PASS' : 'WARN',
      `初期プランの date が全て今日(${todayKey})`,
      `実際の日付サンプル: ${initPlans ? [...new Set(initPlans.map(p => p.date))].join(',') : 'N/A'}`);
  } catch (e) {
    log('T7', 'FAIL', '日付テストで例外', e.message);
  }

  // ===== TEST 8: A-4 新規バグ - athleteId=null で 'unknown' に書き換わるか =====
  try {
    await page.evaluate(() => {
      const plans = JSON.parse(localStorage.getItem('plans') || '[]');
      if (plans.length > 0) {
        // 既存プランの athleteId を null に書き換えて、再ロード後 normalizePlan で何になるか
        plans[0].athleteId = null;
        localStorage.setItem('plans', JSON.stringify(plans));
      }
    });
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    const after = await page.evaluate(() => {
      const plans = JSON.parse(localStorage.getItem('plans') || '[]');
      return plans[0]?.athleteId;
    });
    log('T8', after === 'unknown' ? 'FAIL' : 'PASS',
      `athleteId=null → 'unknown' 孤児化バグ`,
      `結果: athleteId="${after}"  (FAIL=孤児化発生 / PASS=元のまま保持)`);
  } catch (e) {
    log('T8', 'FAIL', '孤児化テストで例外', e.message);
  }

  // ===== TEST 9: B-1 新規バグ - 破損データで初回mount書き込みが起こるか =====
  try {
    await page.evaluate(() => {
      localStorage.setItem('plans', '{"this":"is-corrupt-not-array"}');
    });
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(800);
    const after = await page.evaluate(() => localStorage.getItem('plans'));
    const overwritten = after && after.startsWith('[');
    log('T9', overwritten ? 'FAIL' : 'PASS',
      `破損localStorage がデフォルト値で上書きされる退行`,
      `localStorage[plans] の冒頭: ${after?.slice(0, 50)}  (FAIL=破損データを退避なく上書き / PASS=保持)`);
  } catch (e) {
    log('T9', 'FAIL', '破損データテストで例外', e.message);
  }

  // ===== TEST 10: モーダルがモバイル(390x844)でSaveボタンに届くか =====
  try {
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    const newPlanBtn = page.locator('button', { hasText: /new plan|新しい|追加/i }).first();
    await newPlanBtn.click();
    await page.waitForTimeout(500);
    const saveBtn = page.locator('button', { hasText: /save|保存/i }).first();
    const inView = await saveBtn.isVisible().catch(() => false);
    const box = await saveBtn.boundingBox().catch(() => null);
    log('T10', inView && box && box.y < 844 ? 'PASS' : 'WARN',
      `モバイル390x844 でSaveボタンが画面内にある`,
      `見える=${inView}, y=${box?.y}, height=${box?.height}`);
    await ss(page, '06-mobile-modal');
  } catch (e) {
    log('T10', 'FAIL', 'モバイルモーダルテストで例外', e.message);
  }

  // ===== コンソールエラー集計 =====
  console.log('\n===== コンソールエラー集計 =====');
  if (consoleErrors.length === 0) {
    console.log('✅ コンソールエラー: 0件');
  } else {
    console.log(`❌ コンソールエラー: ${consoleErrors.length}件`);
    consoleErrors.slice(0, 10).forEach(e => console.log('   -', e.slice(0, 200)));
  }
  if (pageErrors.length === 0) {
    console.log('✅ ページエラー (uncaught): 0件');
  } else {
    console.log(`❌ ページエラー: ${pageErrors.length}件`);
    pageErrors.slice(0, 10).forEach(e => console.log('   -', e.slice(0, 200)));
  }

  // ===== 集計 =====
  const pass = results.filter(r => r.status === 'PASS').length;
  const fail = results.filter(r => r.status === 'FAIL').length;
  const warn = results.filter(r => r.status === 'WARN').length;
  console.log(`\n===== TOTAL: PASS=${pass} / FAIL=${fail} / WARN=${warn} =====`);

  await browser.close();
})();
