// content-verify.mjs を3回回して結果のばらつき・安定性を見る
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import path from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const runs = [];
for (let i = 1; i <= 3; i++) {
  console.log(`\n${'='.repeat(64)}`);
  console.log(`▶ Run ${i}/3 開始`);
  console.log('='.repeat(64));

  const result = await new Promise((resolve) => {
    const out = [];
    const proc = spawn('node', ['e2e-temp/content-verify.mjs'], {
      cwd: path.resolve(__dirname, '..')
    });
    proc.stdout.on('data', (data) => { out.push(data.toString()); process.stdout.write(data); });
    proc.stderr.on('data', (data) => { out.push(data.toString()); process.stderr.write(data); });
    proc.on('close', (code) => resolve({ code, output: out.join('') }));
  });

  // PASS/FAIL を抽出
  const passMatch = result.output.match(/PASS=(\d+)/);
  const failMatch = result.output.match(/FAIL=(\d+)/);
  const trendComments = (result.output.match(/過去7日|過去14日|2週間|3日連続/g) || []).length;
  const goodComments = (result.output.match(/睡眠が安定|体重が安定|実行率が高水準|3日連続で全食/g) || []).length;

  runs.push({
    run: i,
    code: result.code,
    pass: passMatch ? parseInt(passMatch[1]) : -1,
    fail: failMatch ? parseInt(failMatch[1]) : -1,
    trendCommentMatches: trendComments,
    goodCommentMatches: goodComments
  });
}

console.log(`\n${'='.repeat(64)}`);
console.log('▶ 3回反復のサマリー');
console.log('='.repeat(64));
console.log(`| Run | PASS | FAIL | trend出現 | good出現 |`);
console.log(`|-----|------|------|-----------|----------|`);
runs.forEach(r => {
  console.log(`|  ${r.run}  |  ${r.pass}  |  ${r.fail}  |    ${r.trendCommentMatches}      |    ${r.goodCommentMatches}     |`);
});

const allPass = runs.every(r => r.fail === 0 && r.code === 0);
console.log(`\n判定: ${allPass ? '✅ 3回とも全件PASS（実装が安定）' : '⚠️  どれかの回で失敗あり（要調査）'}`);

const trendVariation = Math.max(...runs.map(r => r.trendCommentMatches)) - Math.min(...runs.map(r => r.trendCommentMatches));
console.log(`トレンドコメント出現のばらつき: ${trendVariation}（ランダム性で変動するのは自然）`);
