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
  const p = path.join(__dirname, `v2-shot-${name}.png`);
  await page.screenshot({ path: p, fullPage: false });
  return p;
}

const consoleErrors = [];
const pageErrors = [];

async function openNewPlan(page) {
  await page.locator('button[aria-label="新しいプランを追加"]').click();
  await page.waitForSelector('[role="dialog"]', { timeout: 3000 });
  await page.waitForTimeout(200);
}

async function closeModalIfOpen(page) {
  const open = await page.locator('[role="dialog"]').isVisible().catch(() => false);
  if (open) {
    page.once('dialog', d => d.accept().catch(()=>{}));
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    // 念のためdialog残ってたら再Escape
    const stillOpen = await page.locator('[role="dialog"]').isVisible().catch(() => false);
    if (stillOpen) {
      page.once('dialog', d => d.accept().catch(()=>{}));
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    }
  }
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();

  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => pageErrors.push(e.message));

  await page.goto(APP_URL);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(800);

  // ===== T2 修正版: 新規プラン保存 =====
  try {
    await openNewPlan(page);
    const dialog = page.locator('[role="dialog"]');
    // モーダル内のTitle欄
    await dialog.locator('input[aria-label="plan-title"]').fill('テスト朝食');
    log('T2', 'INFO', `モーダル内入力欄使用: aria-label`);
    await dialog.locator('input[aria-label="plan-kcal"]').fill('500');
    await dialog.locator('input[aria-label="plan-carbs"]').fill('60');
    await dialog.locator('input[aria-label="plan-protein"]').fill('25');
    await ss(page, '01-modal-filled');

    await dialog.locator('button', { hasText: /save|保存/i }).click();
    await page.waitForTimeout(800);
    await ss(page, '02-after-save');

    const modalGone = !(await page.locator('[role="dialog"]').isVisible().catch(() => false));
    log('T2', modalGone ? 'PASS' : 'FAIL', `保存後モーダルが閉じる`);

    const hasPlan = await page.locator('text=テスト朝食').first().isVisible().catch(() => false);
    log('T2', hasPlan ? 'PASS' : 'FAIL', `「テスト朝食」が画面に表示`);

    const stored = await page.evaluate(() => {
      const raw = localStorage.getItem('plans');
      try { return JSON.parse(raw); } catch { return null; }
    });
    const inStorage = Array.isArray(stored) && stored.some(p => p.title === 'テスト朝食');
    const planData = Array.isArray(stored) ? stored.find(p => p.title === 'テスト朝食') : null;
    log('T2', inStorage ? 'PASS' : 'FAIL',
      `localStorage[plans] に保存`,
      `件数=${stored?.length}, 保存内容=${JSON.stringify(planData)}`);
  } catch (e) {
    log('T2', 'FAIL', '新規プラン保存テストで例外', e.message.slice(0, 150));
  }

  // ===== T3: NaNテスト（数値欄を空欄で保存しようとする）=====
  try {
    await closeModalIfOpen(page);
    await openNewPlan(page);
    const dialog = page.locator('[role="dialog"]');
    await dialog.locator('input[aria-label="plan-title"]').fill('NaNテスト');
    await dialog.locator('input[aria-label="plan-kcal"]').fill('');
    await dialog.locator('input[aria-label="plan-carbs"]').fill('');
    await dialog.locator('input[aria-label="plan-protein"]').fill('');
    await ss(page, '03-nan-empty');

    await dialog.locator('button', { hasText: /save|保存/i }).click();
    await page.waitForTimeout(400);

    // モーダルが閉じないはず（バリデーション失敗）
    const stillOpen = await page.locator('[role="dialog"]').isVisible().catch(() => false);
    log('T3', stillOpen ? 'PASS' : 'FAIL', `空欄保存でモーダルが閉じない（バリデーション動作）`);

    // エラーメッセージが出ているか
    const errVisible = await page.locator('text=/0 より大きい|必須|0 以上/').first().isVisible().catch(() => false);
    log('T3', errVisible ? 'PASS' : 'FAIL', `バリデーションエラー表示`);

    // localStorage に NaN プランが混入していないか
    const noNaN = await page.evaluate(() => {
      const raw = localStorage.getItem('plans');
      try {
        const plans = JSON.parse(raw);
        return !plans.some(p => p.title === 'NaNテスト') &&
               !plans.some(p => Number.isNaN(p.kcal) || Number.isNaN(p.carbs) || Number.isNaN(p.protein));
      } catch { return false; }
    });
    log('T3', noNaN ? 'PASS' : 'FAIL', `NaN/未バリデーションデータが永続化されていない`);

    await ss(page, '04-nan-error');

    // モーダル閉じる（dirty確認はaccept）
    page.on('dialog', async d => { try { await d.accept(); } catch{} });
    await dialog.locator('button', { hasText: /cancel|キャンセル/i }).click();
    await page.waitForTimeout(500);
  } catch (e) {
    log('T3', 'FAIL', 'NaNテストで例外', e.message.slice(0, 150));
  }

  // ===== T5: ID衝突テスト（3個連続作成）=====
  try {
    await closeModalIfOpen(page);
    for (let i = 0; i < 3; i++) {
      await openNewPlan(page);
      const dialog = page.locator('[role="dialog"]');
      await dialog.locator('input[aria-label="plan-title"]').fill(`連打${i}`);
      await dialog.locator('input[aria-label="plan-kcal"]').fill('200');
      await dialog.locator('input[aria-label="plan-carbs"]').fill('30');
      await dialog.locator('input[aria-label="plan-protein"]').fill('10');
      await dialog.locator('button', { hasText: /save|保存/i }).click();
      await page.waitForTimeout(60);
    }
    await page.waitForTimeout(500);
    const ids = await page.evaluate(() => {
      const raw = localStorage.getItem('plans');
      try { return JSON.parse(raw).map(p => p.id); } catch { return []; }
    });
    const unique = new Set(ids);
    log('T5', ids.length === unique.size && ids.length >= 3 ? 'PASS' : 'FAIL',
      `連続3個追加でID衝突なし`,
      `件数=${ids.length}, ユニーク=${unique.size}, サンプル=${ids.slice(0,3).join(' | ')}`);
  } catch (e) {
    log('T5', 'FAIL', 'ID衝突テストで例外', e.message.slice(0, 150));
  }

  // ===== T8: athleteId=null → 'unknown' 孤児化 =====
  try {
    await closeModalIfOpen(page);
    await page.evaluate(() => {
      const plans = JSON.parse(localStorage.getItem('plans') || '[]');
      const target = plans[0];
      if (target) {
        target.athleteId = null;
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
      `athleteId=null → '${after}' 化バグ`,
      `結果: athleteId="${after}"  (期待: 'unknown' にならない / 実際: ${after === 'unknown' ? '孤児化発生!' : 'OK'})`);
  } catch (e) {
    log('T8', 'FAIL', '孤児化テストで例外', e.message.slice(0, 150));
  }

  // ===== T9: 破損データで上書きされるか =====
  try {
    await page.evaluate(() => {
      // 配列でない壊れた形を入れる
      localStorage.setItem('plans', JSON.stringify({ broken: 'object-not-array' }));
    });
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(800);
    const after = await page.evaluate(() => localStorage.getItem('plans'));
    const overwritten = after && after.startsWith('[');
    log('T9', !overwritten ? 'PASS' : 'FAIL',
      `破損データが silent にデフォルトで上書きされる退行（REVIEW#11意図への反映）`,
      `localStorage[plans]の冒頭60文字: ${after?.slice(0,60)}\n  (FAIL=破損を保持せず上書き / PASS=何らかの形で温存)`);
  } catch (e) {
    log('T9', 'FAIL', '破損データテストで例外', e.message.slice(0, 150));
  }

  // ===== T11: チェックイン入力中に疲労ボタン押すと体重が巻き戻る（新規バグB-3）=====
  try {
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(800);

    // 体重入力欄を探す（label "体重" 等）
    // CheckinPanel の数値input。"weight" や "kg" 関連を探す
    const weightInput = page.locator('input[type="number"]').filter({ hasNot: page.locator('[role="dialog"]') }).last();
    const beforeFatigueButton = page.locator('button').filter({ hasText: /^[1-5]$/ }).nth(2); // 疲労3など
    const exists = await weightInput.count() > 0 && await beforeFatigueButton.count() > 0;
    log('T11', 'INFO', `体重欄・疲労ボタン候補が見える: ${exists}`);
    if (exists) {
      await weightInput.focus();
      await weightInput.fill('65');
      // onBlurさせずに疲労ボタンを押す
      await beforeFatigueButton.click();
      await page.waitForTimeout(400);
      // 体重欄の現在値
      const valueAfter = await weightInput.inputValue();
      log('T11', valueAfter === '65' ? 'PASS' : 'FAIL',
        `体重欄に65入力 → 疲労ボタン押下後も65のまま`,
        `実際の値: "${valueAfter}"`);
    } else {
      log('T11', 'WARN', `テストUIが見つけられず、検証スキップ`);
    }
  } catch (e) {
    log('T11', 'FAIL', 'B-3テストで例外', e.message.slice(0, 150));
  }

  // ===== TX: 全体のコンソール/ページエラー =====
  console.log('\n===== コンソールエラー =====');
  if (consoleErrors.length === 0) console.log('✅ 0件');
  else { console.log(`❌ ${consoleErrors.length}件`); consoleErrors.slice(0,8).forEach(e => console.log('  -', e.slice(0,200))); }
  if (pageErrors.length === 0) console.log('✅ pageerror 0件');
  else { console.log(`❌ pageerror ${pageErrors.length}件`); pageErrors.slice(0,8).forEach(e => console.log('  -', e.slice(0,200))); }

  const pass = results.filter(r => r.status === 'PASS').length;
  const fail = results.filter(r => r.status === 'FAIL').length;
  const warn = results.filter(r => r.status === 'WARN').length;
  console.log(`\n===== TOTAL: PASS=${pass} / FAIL=${fail} / WARN=${warn} =====`);

  await browser.close();
})();
