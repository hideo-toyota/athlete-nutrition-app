// 新機能3つ（Reminder, Buddy, TeamFoodLog）の動作検証
import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import path from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const checks = [];
function record(label, ok, detail = '') {
  checks.push({ label, ok, detail });
  console.log(`  [${ok ? '✅' : '❌'}] ${label}${detail ? `: ${detail}` : ''}`);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 1400 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGE: ' + e.message));

  await page.goto('http://localhost:5173/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);

  console.log('\n=== ① Buddy Check パネル ===');
  // 表示確認
  const buddyVisible = await page.locator('h4', { hasText: 'Buddy Check' }).isVisible({ timeout: 3000 }).catch(() => false);
  record('Buddy Check パネルが表示', buddyVisible);

  // You と Buddy の2カード
  const buddyCards = await page.locator('text=/^You$|^Buddy$/').count();
  record('You と Buddy の2カードが表示', buddyCards >= 2, `カード数=${buddyCards}`);

  // Pair Score 表示
  const pairScore = await page.locator('text=Pair Score').isVisible().catch(() => false);
  record('Pair Score 表示', pairScore);

  // 応援スタンプ
  const stampBtn = page.locator('button', { hasText: 'ナイス補食' });
  const stampVisible = await stampBtn.isVisible().catch(() => false);
  record('応援スタンプボタンが表示', stampVisible);

  // スタンプ送信動作
  if (stampVisible) {
    await stampBtn.click();
    await page.waitForTimeout(300);
    const history = await page.locator('text=/ナイス補食.*→/').first().textContent().catch(() => null);
    record('スタンプ送信で履歴に追加', !!history, history?.slice(0, 50));
  }

  console.log('\n=== ② Reminder Scheduler パネル ===');
  const remindHeading = await page.locator('h4', { hasText: 'Reminder Scheduler' }).isVisible({ timeout: 3000 }).catch(() => false);
  record('Reminder Scheduler パネルが表示', remindHeading);

  // 予約フォーム動作
  const targetSelect = page.locator('label:has-text("相手") select').first();
  const dueSelect = page.locator('label:has-text("タイミング") select').first();
  if (await targetSelect.isVisible().catch(() => false)) {
    // タイミングを変えてみる
    await dueSelect.selectOption({ label: '試合前夜' });
    await page.waitForTimeout(200);

    // 予約ボタンクリック
    const submitBtn = page.locator('button', { hasText: 'リマインド予約' });
    await submitBtn.click();
    await page.waitForTimeout(500);

    // 予約済みリストに追加されたか
    const reminderText = await page.locator('text=/試合前夜/').first().isVisible().catch(() => false);
    record('リマインダー予約が動作', reminderText);

    // localStorage に保存されたか
    const stored = await page.evaluate(() => {
      const raw = localStorage.getItem('ctoc-reminders');
      try { return JSON.parse(raw); } catch { return null; }
    });
    record('localStorage[ctoc-reminders] に保存', Array.isArray(stored) && stored.length >= 1,
      `件数=${Array.isArray(stored) ? stored.length : 'N/A'}, 中身=${JSON.stringify(stored?.[0])?.slice(0, 100)}`);

    // 削除動作
    const delBtn = page.locator('button', { hasText: '削除' }).first();
    if (await delBtn.isVisible().catch(() => false)) {
      await delBtn.click();
      await page.waitForTimeout(400);
      const afterDel = await page.evaluate(() => {
        const raw = localStorage.getItem('ctoc-reminders');
        try { return JSON.parse(raw); } catch { return []; }
      });
      record('削除でlocalStorageから消える', Array.isArray(afterDel) && afterDel.length === 0,
        `件数=${afterDel?.length}`);
    }
  }

  console.log('\n=== ③ Team Food Log パネル ===');
  const teamHeading = await page.locator('h3', { hasText: 'Team Food Log' }).isVisible({ timeout: 3000 }).catch(() => false);
  record('Team Food Log パネルが表示', teamHeading);

  // 共有された食事カードの数
  const teamItems = await page.locator('text=/真似する/').count();
  record('「真似する」ボタンが複数表示', teamItems >= 1, `件数=${teamItems}`);

  // 各カードに athlete名 / sportLabel / 栄養数値 / タグがあるか
  const teamCardSample = await page.evaluate(() => {
    const teamLogPanel = Array.from(document.querySelectorAll('div.glass')).find(d =>
      (d.querySelector('h3')?.textContent || '').includes('Team Food Log')
    );
    if (!teamLogPanel) return null;
    const article = teamLogPanel.querySelector('article');
    if (!article) return null;
    return {
      text: (article.textContent || '').replace(/\s+/g, ' ').slice(0, 300),
      hasImg: !!article.querySelector('img'),
      tagCount: article.querySelectorAll('span').length
    };
  });
  if (teamCardSample) {
    console.log(`  サンプルカード: ${teamCardSample.text}`);
    console.log(`  写真あり: ${teamCardSample.hasImg}, タグ数: ${teamCardSample.tagCount}`);
    record('Team Food Log カードに kcal/糖質/たんぱく質', /kcal|糖質|たんぱく/.test(teamCardSample.text));
    record('Team Food Log カードに選手名', /サンプル選手|Haruka|Ren|Airi|Kenta/.test(teamCardSample.text));
  }

  // 「真似する」ボタンの動作
  const copyBtn = page.locator('button', { hasText: '真似する' }).first();
  if (await copyBtn.isVisible().catch(() => false)) {
    const planCountBefore = await page.evaluate(() => {
      try { return JSON.parse(localStorage.getItem('plans') || '[]').length; } catch { return 0; }
    });
    await copyBtn.click();
    await page.waitForTimeout(500);
    const planCountAfter = await page.evaluate(() => {
      try { return JSON.parse(localStorage.getItem('plans') || '[]').length; } catch { return 0; }
    });
    record('「真似する」で自分のplansに追加される', planCountAfter > planCountBefore,
      `${planCountBefore} → ${planCountAfter}`);
  }

  // 「リマインドに追加」ボタンの動作
  const remindFromTeam = page.locator('button', { hasText: 'リマインドに追加' }).first();
  if (await remindFromTeam.isVisible().catch(() => false)) {
    const beforeR = await page.evaluate(() => {
      try { return JSON.parse(localStorage.getItem('ctoc-reminders') || '[]').length; } catch { return 0; }
    });
    await remindFromTeam.click();
    await page.waitForTimeout(500);
    const afterR = await page.evaluate(() => {
      try { return JSON.parse(localStorage.getItem('ctoc-reminders') || '[]').length; } catch { return 0; }
    });
    record('「リマインドに追加」でリマインドに反映', afterR > beforeR, `${beforeR} → ${afterR}`);
  }

  // スクリーンショット保存
  await page.screenshot({ path: path.join(__dirname, 'panels-overview.png'), fullPage: true });

  console.log('\n=== 集計 ===');
  console.log(`コンソールエラー: ${errors.length}件`);
  errors.slice(0, 5).forEach(e => console.log('  -', e.slice(0, 150)));
  const pass = checks.filter(c => c.ok).length;
  const fail = checks.filter(c => !c.ok).length;
  console.log(`\nTOTAL: PASS=${pass} / FAIL=${fail}`);
  await browser.close();
})();
