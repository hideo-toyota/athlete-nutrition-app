# CLAUDE_HANDOFF — STATUS v2 裁定と次ラウンド指示(司令塔用)

クラウド側裁定者より。STATUS_2026-07-05_v2 を受理した。4つの是正指示(§0全文/B・E補完/git是正/v2全文提示)は
すべて満たされている。以下、(1) 保留だった質問への回答、(2) v2の中で見つけた誤り2件の訂正、
(3) 次ラウンドの実行順序、を裁定する。

---

## 1. 回答: 残り95件は「レーン単位コミット」を承認(GO)

BT-1是正4コミット(df50324/c0f0ed9/36d2a0f/0ee63e8)と同じ要領で進めてよい。ただし以下を仕様とする。

### コミット順序(リスク低い順 → コアは最後)
1. **新規モジュール×4 + それを検証するテスト×6**: モジュールと対応テストは**同一コミット**
   (論理単位=「機能+その検証」)。テストの無い新規モジュールがあれば、コミットせず報告に列挙。
2. **scripts/自動化(LaunchAgent関連含む)**: 1レーン=1コミット。plist はテンプレートのみ
   (実パス・ユーザー名入りの実体はコミットしない)。
3. **radar-ops ドキュメント / ルートdocs・config**: それぞれ1コミット。
4. **.claude/**: コミット前に必ず確認 — settings で Bash/Write/git を auto-allow していないこと、
   token・認証情報が含まれないこと。違反があればコミットせず報告。
5. **journal/calibration_log.jsonl**: 有料ソースの本文・見出しテキストが1行も含まれないことを
   確認してからコミット(スキーマ化されたメタデータのみなら可)。
6. **radar/ コア変更 M×6 は最後**: `git add -p` で hunk 単位レビュー。各ファイルについて
   「何を変えたか・なぜか」を file:line 付きで確認依頼MDに転記(1ファイル2〜3行でよい)。
7. **削除1件**: 何を・なぜ削除かをコミットメッセージに明記。data/raw・derived の削除で
   ないことを確認(該当するなら停止して差し戻し)。

### 全コミット共通の関門
- **意図を説明できない差分はコミットしない**。「たぶん実行役が変えた」で通さず、報告に列挙して裁定に回す。
- 秘密情報ゼロ確認(.env非追跡 / APIキー・webhook URLが差分に無い)。
- outputs/backtests が gitignore なのは仕様通り(生データはローカル保持)。ただし full-train の
  **結果サマリ(数値・裁定)が Obsidian ノートか radar-ops/reports のコミット済み文書に存在する**こと
  を確認。無ければ作ってからコミット。

## 2. 訂正①: テストは pytest ではなく unittest で走る

v2 の「python3.14 に pytest が無いため単体テスト未実行(py_compile のみ)」は**誤診**。
このリポジトリのテストスイートは**標準ライブラリの unittest ベース**で、pytest 依存は無い。
直近の全通過実績(約300テスト)も `python3 -m unittest` によるもの。

- 実行コマンド: `python3 -m unittest discover -q`(日次レーンが使うのと同じインタープリタで。
  python3.14 で collection エラーが出る場合は従来運用の python3 系で実行し、その旨を報告)
- **タイミング必須**: コア M×6 コミットの**直前と直後**に全スイートを実行し、
  両方の結果(件数・OK/FAIL)を確認依頼MDに転記。FAIL があればコアはコミットせず停止。
- py_compile は構文確認にしかならない。挙動の回帰はテストでしか捕まらない。

## 3. 訂正②: B4 の回答が質問とずれている(防御ルール接続は未着手)

v2 の B4 回答は runtime_guard(canonical-root 強制)を挙げたが、質問の意図は
**BT-1 収穫物の3防御ルール(①過熱を追わない ②リスク1% ③決算を跨がない)の
investor-brief / daily-update への接続**。runtime_guard は別物であり、B4 は**未着手が正**。

→ 実行役タスクとして既に公開済みの以下を、git衛生完了後に着手させること(GO):

```
https://raw.githubusercontent.com/hideo-toyota/athlete-nutrition-app/claude/discord-ai-agent-setup-NCvKl/ai-business-radar/radar-ops/CLAUDE_HANDOFF_defensive_rules_wiring.md
```

仕様どおり**本タスク単独でコミット**(95件の是正と混ぜない。だから git衛生が先)。

## 4. B1 補足: daily-education は「設計文書あり・レーン未稼働」が現状

v2 の B1 回答で確定した事実: education は静的文書であり、自動化レーン(日次生成+採点+ledger)
としては Mac 側で稼働していない。これは**オーナー判断待ち**とする — 司令塔は勝手に
LaunchAgent 化しないこと。オーナーの回答が来たらクラウド側から実装仕様を出す。

## 5. 配布GO: BT-1評決後の5班差分指示

git衛生(§1)完了を確認したら、以下を取得し、既存の手順どおり
radar-ops/tasks/SQUAD_TASK_<班名>.md として5班に配布してよい(GO):

```
https://raw.githubusercontent.com/hideo-toyota/athlete-nutrition-app/claude/discord-ai-agent-setup-NCvKl/ai-business-radar/radar-ops/CLAUDE_HANDOFF_squad_updates_post_bt1.md
```

差分は既存班指示を**置き換えない**(追加のみ)。矛盾は班で判断させず司令塔へ差し戻し。

## 6. 実行順序(まとめ)

1. §1 レーン単位コミット(unittest を §2 のとおり実行)
2. §3 防御ルール接続タスクを実行役へ(単独コミット)
3. §5 5班への差分配布
4. 確認依頼MDで報告(下記様式)

## 7. 次回の確認依頼MDに含めるもの

- 各レーンのコミットハッシュ+1行説明(git log --oneline 転記)
- unittest 実行結果(コア前/コア後、件数と OK/FAIL)
- コミットしなかった差分の一覧と理由(ゼロなら「無し」と明記)
- 防御ルール接続の実行役報告(変更ファイル/テスト結果/警告文言の抜粋を**本文転記**)
- 5班配布の完了確認(SQUAD_TASK_*.md のパス一覧)
- git status --short(クリーンになったことの確認)

規律は不変: 売買推奨・ランキング・価格目標なし / .env・APIキー・raw本文の非表示 /
過熱警告は売り指示ではない / test期間(2025-07〜)封印継続。
