# CLAUDE_HANDOFF — 報告専用プライベートリポによる Mac→クラウド配送(司令塔用)

クラウド側裁定者より。オーナー承認済み。Mac→裁定者方向の報告運搬(現状オーナーの手動コピペ)を
自動化する。**指示の方向(裁定者→Mac)は従来どおりオーナーが貼るURL+sha256のまま変えない。**

## 0. 全体像
- オーナーが**非公開**リポ `equity-radar-reports`(仮名)を GitHub に新設。
- Mac側は canonical root とは**別のローカルクローン**(例: ~/equity-radar-reports)を持ち、
  報告ファイルだけをコピー→コミット→push する。
  (mac/live 本体は今後も一切 push しない。no_push 維持。コード・journal・観測データは
   報告リポに入らない)
- 裁定者はそのリポを直接読む(オーナーは「報告が上がった」と一言伝えるだけ)。

## 1. オーナーの作業(3ステップ・10分)
1. GitHub で **Private** リポを新規作成(名前は `equity-radar-reports` を推奨。READMEなしで可)
2. Claude(クラウドセッション)の GitHub 連携にこのリポへのアクセス権を付与
   (Claude GitHub App の対象リポに追加)
3. リポのURLを司令塔に伝える(下のプロンプト内の placeholder を置換)

## 2. 司令塔の実装(単独コミット・[writer: commander])
### 2-1. セットアップ
- `git clone <private-repo-url> ~/equity-radar-reports`(認証はオーナーの既存git認証を使用。
  トークン等を新規に作る場合はオーナーがターミナルで直接設定。チャットに貼らせない)
- canonical root 側には **remote を追加しない**(器を完全分離するのが本設計の要点)。
### 2-2. 配送スクリプト `scripts/publish_reports.sh`
1. 対象: `radar-ops/reports/*.md` と `radar-ops/CONFIRM_*.md` / `STATUS_*.md`(新規・更新分)
2. **秘密スキャン(必須・push前)**: 以下のパターンにヒットしたら**中断して報告**
   - `discord.com/api/webhooks` / `x-api-key` に続く実値 / `JQUANTS_API_KEY=` の実値 /
     40字以上の連続hex・base64塊 / `BEGIN.*PRIVATE KEY`
3. ~/equity-radar-reports/reports/ へコピー → `git add -A` → コミット
   (メッセージ: `reports: <日付> <件数>件 [writer: commander]`)→ push
4. 出力: push した一覧を1行表示(オーナーがDiscord/チャットで私に伝える用)
### 2-3. 運用ルール
- **pushできるのは司令塔のみ**(検証役・Codexはreports/にファイルを書くまで。配送は司令塔)。
- 入れてよいもの: 報告MD(CONFIRM_/VERIFY_/STATUS_/CODEX_)のみ。
  **禁止**: コード・journal・data/・outputs/・有料ソース本文・秘密値。
- 報告MD内の銘柄コード・数値は従来の報告と同じ基準(既にチャットで運搬していた内容と同等)。
- 万一秘密が入った場合: 即時ローテート+該当ファイル削除+履歴からのpurgeを裁定者に報告。
- リポを Public に変更しない(恒久)。
### 2-4. テスト・DoD
- 秘密スキャンのテスト(合成の偽webhook URL入りMD→中断)/ 正常系1回の実push
- 初回push後、オーナー経由で裁定者に「配送テスト完了」を伝え、裁定者が読めることを確認して完了

## 3. 以後の報告フロー(確定)
1. Mac側が報告MDを書く → 司令塔が `publish_reports.sh` 実行
2. オーナーは私に「**報告◯◯が上がった**」と一言(コピペ不要)
3. 裁定者が直接読んで裁定 → 指示は従来どおりオーナー経由(URL+sha256)
※ オーナーの関与は「報告が上がった事実の通知」と「指示の貼り付け」に縮小される。
  AI間の直接指示経路は今までどおり存在しない。

規律不変: 指示は必ずオーナーの手を通る / 秘密・raw本文はどの経路にも載せない /
mac/live本体のpush禁止は不変 / append-only。
