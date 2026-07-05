# CLAUDE_HANDOFF — daily-education の自動化(実行役用)

オーナー判断(2026-07-05)確定: **daily-education を自動化する(GO)**。
根拠となる設計は `CLAUDE_HANDOFF_daily_education.md`(既に取込済のはず。未取込なら先にそれを読む)。
本タスクはその設計を「手動依頼」から「LaunchAgent による毎日自動実行」に変える。

着手タイミング: **STATUS v2 裁定(§6)の git 衛生完了後**。本タスクは単独コミット。

## 自動化の分担(ここを間違えない)
- **生成・リマインド・月次集計 = 自動**(本タスクで実装)
- **採点 = 回答が来た時に Discord 窓口が実施**(既存フローのまま。自動化しない —
  回答は人間の自由文であり、来ない日もあるため)

## 実装内容

### E1. LaunchAgent `com.radar.daily-education`
- 毎日 19:00 JST(夕方スロット後)。WorkingDirectory = canonical root(runtime_guard 対象)。
- 実行内容: headless Claude 呼び出しで `CLAUDE_HANDOFF_daily_education.md` の手順を実行し、
  `outputs/obsidian/education/<YYYY-MM-DD>-判断力トレーニング.md` を生成。
- モデル: 既存 orchestrator-analysis レーンと同方式・**Sonnet 系で十分**(仕様に従う仕事)。
- plist は**テンプレートのみコミット**(auto_pull と同方式。実パス・ユーザー名入り実体は非コミット)。
- ログはリポジトリ外(auto_pull と同じ場所の流儀)。

### E2. Discord 投稿
- 生成後、「題材+教養+3問」のみを Discord に投稿(解答・解説部は貼らない。既存設計どおり)。
- 投稿の冒頭に通し番号と分野を明記: 「判断力トレーニング #NN(分野C: 行動バイアス)」。

### E3. 未回答リマインド(「忘れてはいけない」対策 — 本タスクの核心)
- 生成時に `journal/education_ledger.jsonl` を読み、**前日以前の未採点(=未回答)分**を検出:
  education ノートが存在するのに対応する ledger 行が無い日 = 未回答。
- 当日の Discord 投稿の先頭に1行:
  「⏰ 未回答: 7/04 の3問が未回答です(回答をこのチャンネルに返信すれば窓口が採点します)」
- 未回答が3日以上溜まったら件数を明示(「未回答3日分」)。**責めない・甘くしない・事実だけ**。
- 回答済みの日は何も出さない(ノイズを増やさない)。

### E4. 月次弱点マップ
- 毎月最終日の実行時、当月の ledger から誤答の多い分野(A〜F)を集計し、
  当日の education ノート末尾に「今月の弱点マップ」節を追記。
- サンプルが少ない月は少ないと正直に書く(<10問なら「集計に足りない」)。

### E5. ローテーション状態
- 分野ローテ(A〜F)の現在位置を `journal/education_state.json` に保持
  (次の分野・通し番号)。壊れていたら A から再開し、その旨をノートに1行記録。

## テスト要件(合成データ)
- ledger に 7/03 の行が無く education/7/03 ノートが存在する場合、リマインド行が出る
- 全日回答済みならリマインド行が出ない
- ローテが A→B→…→F→A と循環する / state 破損時に A から再開する
- 生成物に FORBIDDEN_OUTPUT_TOKENS(売買推奨・価格目標等)が含まれない
- 月次集計が <10問 で「集計に足りない」を出す

## DoD
- LaunchAgent が登録され、1回の実手動発火で education ノート生成+Discord 投稿を目視確認
- 全テスト通過(`python3 -m unittest discover -q`)
- 本タスク単独でコミット / Obsidian 記録: outputs/obsidian/YYYY-MM-DD-education自動化.md
- 報告: plist テンプレ path / 生成ノート冒頭の抜粋 / テスト結果 → radar-ops/reports/ へ

## 禁止(既存規律の再掲+本タスク固有)
- 教材に売買推奨・買い候補・価格目標・ランキング・将来断定を書かない(問うのは常にプロセス)。
- 有料ソースの本文・見出し一覧の転載禁止。public リポに push してよいのは自作教材文のみ。
- APIキー・.env・raw本文を読まない・書かない。headless 呼び出しの認証情報をログに残さない。
- 採点の自動化・成績による教材の難易度調整はしない(別途裁定が要る)。
- 未回答でも教材生成を止めない(積み残しの可視化が目的で、罰ではない)。
