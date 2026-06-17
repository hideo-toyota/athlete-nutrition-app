# RUNBOOK — 実運用の立ち上げ手順(Mac)

> ゼロから「Discordで規律ある投資判断を回す」までの実行チェックリスト。
> 設計の“なぜ”は [DESIGN_PRINCIPLES.md](DESIGN_PRINCIPLES.md)。ここは“どうやって動かすか”。
> 追加費用は不要(既存の Claude Pro/Max サブスク + 無料ツールのみ)。

---

## 0. 前提(一度だけ)
- [ ] **Claude Code** を導入し、**Pro/Max でログイン**(`claude --version` が 2.1.80+)
- [ ] `echo $ANTHROPIC_API_KEY` が**空**(従量課金に化けないよう未設定に)
- [ ] `python3 --version`(3.10+) / `git` / `bun --version`(無ければ `curl -fsSL https://bun.sh/install | bash`)

## 1. コードを入れる
```bash
git clone <このリポジトリ> && cd <repo>/ai-business-radar
# 既にあれば: git pull
```

## 2. まず“正直な鏡”を見る(サンプルで動作確認)
```bash
python3 -m radar mirror
```
→ `outputs/honest_mirror.md` に look-through 集中度が出る(サンプルで一度確認)。

## 3. 自分の実データに差し替える
- [ ] `portfolio.json` を**実保有**に(個別株は `cost_basis_jpy` も。`kind`/`sleeve` を正しく)
- [ ] `indices/acwi.json` を**保有インデックスの月次レポート**から概算で埋める(国・セクター・上位銘柄)
- [ ] `config.json` の上限(2.5%/5%/10%)・通貨(JPY)を確認
```bash
python3 -m radar mirror     # 自分の本当の集中度(例: 実質US-Tech◯%・USD◯%)を確認
```

## 4. 規律ゲートを使う(買う前に必ず)
```bash
python3 -m radar check buy 7203 100000 Financials      # 上限/過熱/ナンピンに照らす
python3 -m radar check add NVDA 100000                 # 例: 既に上限 → 却下
```
- 過熱なら `--overheated`、ナンピンは `--thesis-intact --powder` を明示(無ければ却下)。

## 5. 閉ループ(判断→採点→較正)
```bash
cp journal/decision_input.example.json journal/decision_input.json   # 判断ごとに編集
python3 -m radar log         # 反証可能な予測(claim+horizon)必須・override理由必須
# 期日が来たら、journal/prices.json に horizon の終値を入れて:
python3 -m radar score       # DCAインデックス比で機械採点(未来不参照)
python3 -m radar review      # outputs/journal_review.md(裁量 vs 規律)
```
- `decision_log.jsonl` は**追記専用・個人データ**(.gitignore済)。手で書き換えない。

## 6. Discord で操作する(① 1セッション + サブエージェント)
1. [ ] [Discord Developer Portal](https://discord.com/developers/applications) で Bot 作成 → **トークン**取得、**Message Content Intent** ON
2. [ ] OAuth2 → URL Generator(scope `bot`、権限: メッセージ送受信・履歴・添付)で**自分のサーバーに招待**
3. [ ] Claude Code 内で:
   ```
   /plugin install discord@claude-plugins-official
   /reload-plugins
   /discord:configure <トークン>
   ```
4. [ ] **常駐起動**(スリープ防止):
   ```bash
   tmux new -s claude
   caffeinate -i claude --channels plugin:discord@claude-plugins-official
   # Ctrl+b → d でデタッチ(裏で動き続ける)
   ```
5. [ ] Bot に DM → 返ったコードで `/discord:access pair <code>` → `/discord:access policy allowlist`(**自分だけ**)
6. [ ] スマホの Discord から動作テスト:「**今の市況は?**」(market-pulse)、「**NVDA を点検して**」(equity-analysis)

> このプロジェクトを開いた状態で起動すれば、`CLAUDE.md`・`.claude/agents`・`.claude/skills` が読まれ、
> 規律ゲートを通す“分析チーム”として動く。**買い候補は discipline-auditor を通すまで出さない。**

## 7. Obsidian(記録の置き場)
- [ ] Obsidian Vault を用意。当面は `outputs/journal_review.md` と判断メモを**手動で取り込む**
- [ ] (任意・今後)`mcp-obsidian` を繋げば `recorder`/`logbook-keeper` が直接書き込み

---

## 日々のループ(実運用)
```
朝/必要時: 「市況は?」(market-pulse) → 気になる銘柄を「分析して」(equity-analysis)
  → mirror(今の集中度) → 分析+反証 → check(規律ゲート)
  → 自分で決める → log(予測つき) → 期日に score/review
```

## コスト・上限
- 追加費用なし(サブスク内)。**お金でなく使用“上限”**に注意(Proで足りなければMax)。
- 定期自動化(`claude -p`)は 2026/6/15 以降 別クレジット枠。
- J-Quants / EDINET DB 有料データ層は**別トラック**(`DATA_LAYER_SPEC.md`)。**A0=実装済・A1以降は `LICENSE_MATRIX` のToS確認後**。radarコア(mirror/check/log/score/review)・target-check・value-audit(Phase A・手入力 snapshot)は**この層なしで動く**。

## 安全
- Botは **allowlist で自分だけ**。トークンはパスワード扱い(漏れたら再生成)。
- `ANTHROPIC_API_KEY` は未設定。自動発注はしない(分析・通知・記録まで)。

## まだ未実装(実運用後に必要なら)
`analyze`(日本中小型スクリーニング)・`backtest`・過熱の価格自動判定・J-Quants `data`接続・Obsidian自動連携。
