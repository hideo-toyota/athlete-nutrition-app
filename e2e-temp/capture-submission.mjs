import { chromium } from 'playwright'
import { fileURLToPath, pathToFileURL } from 'url'
import path from 'path'
import fs from 'fs/promises'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..')
const distIndex = path.join(projectRoot, 'dist', 'index.html')
const outputDir = path.join(projectRoot, 'submission-assets')

function localDateKey(date) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, '0'),
    String(date.getDate()).padStart(2, '0')
  ].join('-')
}

await fs.mkdir(outputDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } })

await page.goto(pathToFileURL(distIndex).href)
await page.waitForLoadState('domcontentloaded')
await page.evaluate(() => localStorage.clear())
await page.reload()
await page.waitForLoadState('domcontentloaded')
await page.waitForTimeout(1200)
const eventDate = new Date()
eventDate.setDate(eventDate.getDate() + 5)
await page.getByLabel('event-title').fill('5日後の本番')
await page.getByLabel('event-date').fill(localDateKey(eventDate))
await page.getByRole('button', { name: '本番日を追加' }).click()
await page.waitForTimeout(800)
await page.screenshot({
  path: path.join(outputDir, 'athlete-nutrition-dashboard.png'),
  fullPage: true
})

await page.locator('button[aria-label="新しいプランを追加"]').click()
await page.waitForSelector('[role="dialog"]', { timeout: 3000 })
await page.screenshot({
  path: path.join(outputDir, 'athlete-nutrition-new-plan.png'),
  fullPage: false
})

await browser.close()

console.log(`Saved screenshots to ${outputDir}`)
