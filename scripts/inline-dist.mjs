import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(scriptDir, '..')
const distDir = path.join(projectRoot, 'dist')
const indexPath = path.join(distDir, 'index.html')

function escapeInlineScript(source) {
  return source.replace(/<\/script/gi, '<\\/script')
}

function escapeInlineStyle(source) {
  return source.replace(/<\/style/gi, '<\\/style')
}

async function main() {
  let html = await readFile(indexPath, 'utf8')

  const cssMatch = html.match(/<link rel="stylesheet"[^>]*href="([^"]+)"[^>]*>/i)
  if (cssMatch) {
    const cssPath = path.resolve(distDir, cssMatch[1])
    const css = await readFile(cssPath, 'utf8')
    html = html.replace(cssMatch[0], () => `<style>\n${escapeInlineStyle(css)}\n</style>`)
  }

  const scriptMatch = html.match(/<script type="module"[^>]*src="([^"]+)"[^>]*><\/script>/i)
  if (scriptMatch) {
    const jsPath = path.resolve(distDir, scriptMatch[1])
    const js = await readFile(jsPath, 'utf8')
    html = html.replace(scriptMatch[0], () => `<script type="module">\n${escapeInlineScript(js)}\n</script>`)
  }

  await writeFile(indexPath, html)
  console.log('Inlined dist/index.html for direct file opening')
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
