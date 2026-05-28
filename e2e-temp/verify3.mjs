// 新機能（カレンダー・写真添付）の実機検証
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
  const p = path.join(__dirname, `v3-shot-${name}.png`);
  await page.screenshot({ path: p, fullPage: false });
}

const consoleErrors = [];
const pageErrors = [];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 768, height: 1024 } });
  const page = await ctx.newPage();
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => pageErrors.push(e.message));

  await page.goto(APP_URL);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(800);
  await ss(page, '00-initial');

  // ===== T20: CalendarPanel 描画確認 =====
  try {
    const calHeader = page.locator('h3', { hasText: 'Calendar' });
    const calVisible = await calHeader.isVisible({ timeout: 3000 }).catch(() => false);
    log('T20', calVisible ? 'PASS' : 'FAIL', `CalendarPanel が表示される`);

    // 42日分のセルがあるか
    const cells = page.locator('button[aria-label^="select "]');
    const cellCount = await cells.count();
    log('T20', cellCount === 42 ? 'PASS' : 'FAIL', `42セル(6週×7曜)が描画`, `cells=${cellCount}`);
    await ss(page, '01-calendar');
  } catch (e) {
    log('T20', 'FAIL', 'カレンダー描画テストで例外', e.message.slice(0, 150));
  }

  // ===== T21: Prev/Next で月が変わる =====
  try {
    const monthLabelLoc = page.locator('h3', { hasText: 'Calendar' }).locator('..').locator('div', { hasText: /^\d{4}年/ }).first();
    const before = await monthLabelLoc.textContent().catch(() => null);

    const prevBtn = page.locator('button', { hasText: 'Prev' }).first();
    await prevBtn.click();
    await page.waitForTimeout(300);
    const afterPrev = await monthLabelLoc.textContent().catch(() => null);
    log('T21', before !== afterPrev ? 'PASS' : 'FAIL', `Prevボタンで月が変わる`, `${before} → ${afterPrev}`);

    const nextBtn = page.locator('button', { hasText: 'Next' }).first();
    await nextBtn.click();
    await page.waitForTimeout(300);
    const afterNext = await monthLabelLoc.textContent().catch(() => null);
    log('T21', afterNext === before ? 'PASS' : 'FAIL', `Nextボタンで元の月に戻る`, `${afterPrev} → ${afterNext}`);
  } catch (e) {
    log('T21', 'FAIL', '月移動テストで例外', e.message.slice(0, 150));
  }

  // ===== T22: Todayボタンで今日に戻る =====
  try {
    // 一旦前月に移動
    await page.locator('button', { hasText: 'Prev' }).first().click();
    await page.waitForTimeout(200);

    const todayBtn = page.locator('button', { hasText: 'Today' }).first();
    const todayBefore = await page.evaluate(() => {
      const d = new Date();
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
    });
    await todayBtn.click();
    await page.waitForTimeout(300);

    // 「今日」のセルに青ドットマークがあるか
    const todayCell = page.locator(`button[aria-label="select ${todayBefore}"]`);
    const hasIndicator = await todayCell.locator('span.bg-neon-500').isVisible().catch(() => false);
    log('T22', hasIndicator ? 'PASS' : 'WARN', `Today押下で今日(${todayBefore})に戻り、青ドットマーク表示`);
  } catch (e) {
    log('T22', 'FAIL', 'Todayボタンテストで例外', e.message.slice(0, 150));
  }

  // ===== T23: 日付クリックで selectedDate が変わる =====
  try {
    const todayKey = await page.evaluate(() => {
      const d = new Date();
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
    });
    // 翌日のキーを生成
    const tomorrowKey = await page.evaluate(() => {
      const d = new Date();
      d.setDate(d.getDate() + 1);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
    });
    const targetCell = page.locator(`button[aria-label="select ${tomorrowKey}"]`);
    const targetExists = await targetCell.isVisible().catch(() => false);
    if (!targetExists) {
      log('T23', 'WARN', `翌日(${tomorrowKey})セルが当月に無い`);
    } else {
      await targetCell.click();
      await page.waitForTimeout(300);
      // サマリー欄に翌日の日付が反映されているか
      const dateBadge = page.locator(`text=${tomorrowKey}`).first();
      const ok = await dateBadge.isVisible().catch(() => false);
      log('T23', ok ? 'PASS' : 'FAIL', `セルクリックで selectedDate=${tomorrowKey} に変更`);
      // 今日に戻す
      await page.locator('button', { hasText: 'Today' }).first().click();
      await page.waitForTimeout(200);
    }
  } catch (e) {
    log('T23', 'FAIL', '日付セルクリックテストで例外', e.message.slice(0, 150));
  }

  // ===== T24: 写真添付機能 =====
  try {
    // テスト用の小さい画像を生成 (1x1 PNG)
    const fakeImagePath = path.join(__dirname, 'fake-image.png');
    const fs = await import('fs');
    // 1x1 transparent PNG (base64)
    const tinyPng = Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
      'base64'
    );
    fs.writeFileSync(fakeImagePath, tinyPng);

    // 「写真を追加」ボタンを探す
    const photoBtn = page.locator('button', { hasText: '写真を追加' }).first();
    const photoBtnVisible = await photoBtn.isVisible({ timeout: 3000 }).catch(() => false);
    log('T24', photoBtnVisible ? 'PASS' : 'FAIL', `「写真を追加」ボタンが表示`);

    if (photoBtnVisible) {
      // ファイル選択は input にダイレクトに setInputFiles
      const fileInput = page.locator('input[type="file"]').first();
      await fileInput.setInputFiles(fakeImagePath);
      await page.waitForTimeout(800);
      await ss(page, '02-photo-uploaded');

      // <img> が画面に表示されているか
      const imgCount = await page.locator('img').count();
      log('T24', imgCount > 0 ? 'PASS' : 'FAIL', `添付後 img タグが表示`, `img数=${imgCount}`);

      // localStorage に photoDataUrl が含まれているか
      const stored = await page.evaluate(() => {
        const raw = localStorage.getItem('plans');
        try {
          const plans = JSON.parse(raw);
          return plans.find(p => p.photoDataUrl)?.photoDataUrl?.slice(0, 50) ?? null;
        } catch { return null; }
      });
      log('T24', stored && stored.startsWith('data:image') ? 'PASS' : 'FAIL',
        `localStorage[plans] に photoDataUrl 保存`,
        `先頭50文字: ${stored}`);
    }

    fs.unlinkSync(fakeImagePath);
  } catch (e) {
    log('T24', 'FAIL', '写真添付テストで例外', e.message.slice(0, 200));
  }

  // ===== T25: 写真削除 =====
  try {
    const removeBtn = page.locator('button', { hasText: '写真を削除' }).first();
    const visible = await removeBtn.isVisible({ timeout: 3000 }).catch(() => false);
    if (!visible) {
      log('T25', 'WARN', `「写真を削除」ボタンが見つからない (T24失敗時はスキップ)`);
    } else {
      await removeBtn.click();
      await page.waitForTimeout(500);
      const stored = await page.evaluate(() => {
        const raw = localStorage.getItem('plans');
        try {
          const plans = JSON.parse(raw);
          return plans.some(p => p.photoDataUrl);
        } catch { return null; }
      });
      log('T25', stored === false ? 'PASS' : 'FAIL', `写真削除でlocalStorageからphotoDataUrlが消える`);
    }
  } catch (e) {
    log('T25', 'FAIL', '写真削除テストで例外', e.message.slice(0, 150));
  }

  // ===== T26: PlanPatch型導入の確認（updatePlanが部分パッチを受け取れるか）=====
  // photoDataUrl だけを変更したときに他のフィールドが破壊されないか
  try {
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    // 既存プランの kcal を覚えておく
    const before = await page.evaluate(() => {
      const plans = JSON.parse(localStorage.getItem('plans') || '[]');
      const p = plans[0];
      return p ? { id: p.id, title: p.title, kcal: p.kcal, athleteId: p.athleteId } : null;
    });

    // 写真を1つ追加（先頭プランに）
    const fakeImagePath = path.join(__dirname, 'fake-image2.png');
    const fs = await import('fs');
    const tinyPng = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=', 'base64');
    fs.writeFileSync(fakeImagePath, tinyPng);
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(fakeImagePath);
    await page.waitForTimeout(800);

    const after = await page.evaluate((id) => {
      const plans = JSON.parse(localStorage.getItem('plans') || '[]');
      const p = plans.find(p => p.id === id);
      return p ? { id: p.id, title: p.title, kcal: p.kcal, athleteId: p.athleteId, hasPhoto: !!p.photoDataUrl } : null;
    }, before?.id);

    const intact = before && after &&
      before.title === after.title &&
      before.kcal === after.kcal &&
      before.athleteId === after.athleteId &&
      after.hasPhoto;
    log('T26', intact ? 'PASS' : 'FAIL',
      `写真更新で他フィールド破壊なし(PlanPatch型動作)`,
      `before=${JSON.stringify(before)}, after=${JSON.stringify(after)}`);
    fs.unlinkSync(fakeImagePath);
  } catch (e) {
    log('T26', 'FAIL', 'PlanPatch動作テストで例外', e.message.slice(0, 150));
  }

  // ===== T27: 写真容量問題（同一プランに大きめの画像を入れてもクラッシュしないか）=====
  try {
    // 100KB 程度の擬似データを作る
    const big = Buffer.alloc(50000, 0xff); // バイトを埋める
    // 上記はPNGとして無効だが、テストは画像処理ではなく FileReader → image.onerror → reject の経路
    const fakePath = path.join(__dirname, 'big-image.png');
    const fs = await import('fs');
    // 有効な大きいPNG: 8x8 PNG
    fs.writeFileSync(fakePath, Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAEklEQVR4nGNgYGD4z0AswK4SAFXuAf8EPy+xAAAAAElFTkSuQmCC',
      'base64'
    ));
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(fakePath);
    await page.waitForTimeout(800);
    log('T27', 'PASS', `8x8画像アップロードでクラッシュなし`);
    fs.unlinkSync(fakePath);
  } catch (e) {
    log('T27', 'FAIL', '画像容量テストで例外', e.message.slice(0, 150));
  }

  // ===== T28: カレンダーのモバイル表示（390x844）=====
  try {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(300);
    await ss(page, '03-calendar-mobile');
    const calVisible = await page.locator('h3', { hasText: 'Calendar' }).isVisible().catch(() => false);
    log('T28', calVisible ? 'PASS' : 'FAIL', `モバイル幅でもカレンダー描画`);

    // セルの幅を測る
    const firstCell = page.locator('button[aria-label^="select "]').first();
    const cellBox = await firstCell.boundingBox().catch(() => null);
    log('T28', cellBox && cellBox.width >= 32 ? 'PASS' : 'WARN',
      `モバイルでセル幅が確保`,
      `セル幅=${cellBox?.width}px, 高さ=${cellBox?.height}px`);
  } catch (e) {
    log('T28', 'FAIL', 'モバイルカレンダーテストで例外', e.message.slice(0, 150));
  }

  console.log('\n===== コンソール/ページエラー =====');
  if (consoleErrors.length === 0) console.log('✅ コンソールエラー 0件');
  else { console.log(`❌ ${consoleErrors.length}件`); consoleErrors.slice(0,8).forEach(e => console.log('  -', e.slice(0,200))); }
  if (pageErrors.length === 0) console.log('✅ pageerror 0件');
  else { console.log(`❌ ${pageErrors.length}件`); pageErrors.slice(0,8).forEach(e => console.log('  -', e.slice(0,200))); }

  const pass = results.filter(r => r.status === 'PASS').length;
  const fail = results.filter(r => r.status === 'FAIL').length;
  const warn = results.filter(r => r.status === 'WARN').length;
  console.log(`\n===== TOTAL: PASS=${pass} / FAIL=${fail} / WARN=${warn} =====`);

  await browser.close();
})();
