// 写真削除フローのフォーカステスト
import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1024, height: 1400 } });
  const page = await ctx.newPage();

  page.on('pageerror', e => console.log('PAGE_ERROR:', e.message));

  await page.goto('http://localhost:5173/');
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(800);

  // 1. 写真を追加
  const fakePath = path.join(__dirname, 'tiny.png');
  fs.writeFileSync(fakePath, Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=', 'base64'));

  console.log('=== STEP 1: 写真追加前のlocalStorage ===');
  let plans = await page.evaluate(() => {
    const raw = localStorage.getItem('plans');
    return raw ? JSON.parse(raw) : null;
  });
  console.log('plans:', plans ? `${plans.length}件` : 'null (mockのfallback使用中)');

  const fileInput = page.locator('input[type="file"]').first();
  await fileInput.setInputFiles(fakePath);
  await page.waitForTimeout(1000);

  console.log('\n=== STEP 2: 写真追加後のlocalStorage ===');
  plans = await page.evaluate(() => JSON.parse(localStorage.getItem('plans') || '[]'));
  const withPhoto = plans.filter(p => p.photoDataUrl);
  console.log(`plans=${plans.length}件、写真あり=${withPhoto.length}件`);
  if (withPhoto[0]) console.log(`  対象ID=${withPhoto[0].id}, title=${withPhoto[0].title}`);

  // 2. 削除ボタンを探す
  console.log('\n=== STEP 3: 「写真を削除」ボタンを探す ===');
  const removeBtns = page.locator('button', { hasText: '写真を削除' });
  const count = await removeBtns.count();
  console.log(`「写真を削除」ボタン数: ${count}`);

  if (count > 0) {
    // スクロールして見える状態にする
    await removeBtns.first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(200);
    await page.screenshot({ path: path.join(__dirname, 'focus-before-delete.png') });

    console.log('\n=== STEP 4: 削除ボタン click ===');
    // 通常クリック
    await removeBtns.first().click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(__dirname, 'focus-after-delete.png') });

    console.log('\n=== STEP 5: 削除後のlocalStorage ===');
    plans = await page.evaluate(() => JSON.parse(localStorage.getItem('plans') || '[]'));
    const stillHasPhoto = plans.filter(p => p.photoDataUrl);
    console.log(`plans=${plans.length}件、写真がまだ残っている=${stillHasPhoto.length}件`);
    if (stillHasPhoto.length > 0) {
      console.log(`  ⚠️ 残っているプラン: ${JSON.stringify(stillHasPhoto.map(p => ({id: p.id, title: p.title, photoLen: p.photoDataUrl?.length})))}`);
    } else {
      console.log('  ✅ 削除成功');
    }

    // 「写真を削除」ボタンがDOMから消えたか
    const remainBtns = await page.locator('button', { hasText: '写真を削除' }).count();
    console.log(`削除後の「写真を削除」ボタン数: ${remainBtns}`);

    // 「写真を追加」ボタンに戻っているか
    const addBtns = await page.locator('button', { hasText: '写真を追加' }).count();
    console.log(`「写真を追加」ボタン数: ${addBtns}`);
  }

  fs.unlinkSync(fakePath);
  await browser.close();
})();
