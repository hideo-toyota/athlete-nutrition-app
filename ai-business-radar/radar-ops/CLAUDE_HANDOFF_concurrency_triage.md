# CLAUDE_HANDOFF — 緊急対処: 並行コミッタの停止と配送機構の再設計(司令塔用)

クラウド側裁定者より。緊急停止報告を受理した。**両事象とも停止判断は正しい**。
git書き込み凍結を維持したまま、以下を順に実行する。

## A. 事象A(並行コミッタ)の対処 — 最優先

### A-1. 特定(読み取りのみ)
- `ps -o pid,ppid,lstart,command -p 67872` と親プロセスの遡上(何が起動したか:
  ターミナルの対話セッションか、launchd 配下か)。
- `launchctl list | grep radar` と各レーンのログの 12:10〜12:20 の活動照合。
- radar-ops/tasks/ と ops_queue に、レーンコミットを指示する内容が存在するか確認
  (存在するなら誰が書いたかを stat とログで確認)。

### A-2. 停止(強制killはしない)
- **対話セッション由来なら**: オーナーに閉じてもらう(クラウド側からオーナーへ確認済み。
  オーナーの回答を待って進める)。
- **LaunchAgent由来なら**: 実行中の書き込みが終わるのを待ち(COMMIT_EDITMSG の mtime が
  60秒以上安定してから)、該当エージェントを `launchctl bootout gui/$(id -u)/<label>` で停止。
- 停止確認: プロセス消滅+ .git/index.lock 不在+ COMMIT_EDITMSG mtime 安定。

### A-3. 健全性確認と 145006c の裁定
- `git fsck --no-dangling` / `git status --short` / 145006c 以降に増えたコミットの全列挙。
- 145006c(kabutan lane)の扱い: **中身で判定**する。adj.md §1 と同じ関門
  (単一レーン・全hunkの意図説明可能・秘密情報ゼロ・unittest通過)を満たすなら
  事後採用してよい(確認依頼MDに「並行コミッタ由来・事後監査で採用」と明記)。
  満たさないなら `git revert`(reset --hard で消さない。履歴は append-only の正直さを保つ)。

### A-4. 恒久ルール(single-writer)
- **canonical root で git 書き込み(add/commit/branch/checkout/merge)を行えるのは
  司令塔セッションただ1つ**。headless/LaunchAgent レーンは出力ファイル生成のみで、
  git 書き込みを恒久禁止。
- 全 plist / レーンスクリプトを監査し、git 書き込みを行うものがあれば除去して報告。
- 着手時に `.git-writer.lock`(pid+開始時刻)を作り、終了時に消す。レーンスクリプトは
  ロック存在時に git を触らない(そもそも触らないが二重の防御)。

## B. 事象B(無関係履歴)— 裁定§2の merge 指示を撤回し、配送を再設計

### B-0. 裁定者の訂正(本日2件目・正直な記録)
「clone構成」も誤りだった。実態は**独立に init されたリポに origin が後付けされた無関係履歴**。
よって ff-pull も merge も最初から構造的に不可能で、配送は実質 raw-URL だった。
今後、私はリポ構成を FACT として扱う前に必ず転記された `git remote -v` / `git merge-base` を
要求する(推測で前提を書かない)。

### B-1. merge はしない。ローカルの配送ブランチ・ラベルを撤去
- `git merge --allow-unrelated-histories` は**恒久禁止**(クラウド文書ツリーがコードベースに
  流れ込む)。
- §2 で作ったローカルブランチ `claude/discord-ai-agent-setup-NCvKl` が origin 側 DAG を
  指しているなら **`git branch -D claude/discord-ai-agent-setup-NCvKl` で削除**
  (誤って checkout すると作業ツリー全体が別リポの内容に入れ替わるため。参照は
  `origin/claude/discord-ai-agent-setup-NCvKl` だけで足りる)。
- mac/live が唯一のローカル作業ブランチ。以後もそこにのみコミット。

### B-2. 新しい配送手順(fetch + git show。curl/urllib 不要になる)
```
git fetch origin   # 無関係履歴でも fetch は正常に機能する
git show origin/claude/discord-ai-agent-setup-NCvKl:ai-business-radar/radar-ops/<FILE>.md \
  > radar-ops/incoming/<FILE>.md
shasum -a 256 radar-ops/incoming/<FILE>.md   # オーナー提示のハッシュと照合
```
- radar-ops/incoming/ は gitignore(取り込みの一時置き場)。
- auto_pull.sh は `git fetch origin` のみ+新着コミットのログ通知に修正(§1レーンに含めてよい)。
- 正規指示の形式は不変: オーナーが貼る「ファイル名(またはURL)+sha256」の組のみ。

## C. 再開条件と順序
1. A-2 完了(single-writer 確定)→ 2. A-3(145006c 裁定)→ 3. B-1/B-2 →
4. adj.md §6 の残り(レーン単位コミット→防御ルール接続→5班配布。すべて mac/live 上)→
5. 確認依頼MD: adj.md §7 様式+ A(並行コミッタの正体・停止方法・145006c の裁定結果)+
   B(branch -D と incoming 方式の実施結果)+ `git remote -v` / `git branch -a` 転記。

規律は不変: push しない(no_push 維持)/ 秘密・raw本文非表示 / 履歴 append-only /
売買推奨・ランキング・価格目標なし。
