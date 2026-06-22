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
# 見送りを記録する場合:
cp journal/decision_input.pass.example.json journal/decision_input.json
python3 -m radar log         # 反証可能な予測(claim+horizon)必須・override理由必須
# 期日が来たら、journal/prices.json に horizon の終値を入れて:
python3 -m radar score       # DCAインデックス比で機械採点(未来不参照)
python3 -m radar review      # outputs/journal_review.md(裁量 vs 規律)
```
- `decision_log.jsonl` は**追記専用・個人データ**(.gitignore済)。手で書き換えない。
- 採点は action-aware。`buy/add` は対象がDCAを上回れば hit、`pass/trim/exit` は対象がDCAを下回れば「避けた判断」として hit。

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

### 状態確認(迷ったら最初に)
```bash
python3 -m radar doctor
```
- どの作業ツリーを見ているか、`/private/tmp` か、raw と derived の鮮度差、J-Quants coverage、
  `decision_log.jsonl` が空かどうかを確認する。APIキー値・`.env`値・provider raw本文は表示しない。
- 「データは取ったのに分析に出ない」と感じたら、まず `edinet_features_stale` / `company_map_stale` /
  `jquants_features_missing` の警告を見る。

### ローカルデータ更新後の Discord / LLM 分析ループ
```bash
python3 -m radar daily-update --asof YYYY-MM-DD --max-items 50
```
- まず `outputs/investor_brief/<asof>.md` を読む。これは market snapshot / watch changes /
  human review list の参謀パケットで、今日見る論点・UNKNOWN・反証条件・次に読む資料をまとめる。
- 出力された `outputs/discord/llm_prompt_<asof>.md` の本文を Discord / Claude Code に貼る。
- Claude 側は `outputs/investor_brief/<asof>.md` と `outputs/llm_handoff/<asof>.md` を読み、
  UNKNOWN・反証条件・claim分類・discipline gate を固定形式で返す。
- raw本文/APIキー/.env は貼らない。売買指示・価格目標・順位付け・利益保証・将来断定もさせない。
- 分析品質の校正は `python3 -m radar audit-report --asof YYYY-MM-DD` を見て、mismatch率・p90|Δ|・校正信号から外れ値/期間差/定義差を点検する。
- データ取得の標準時刻は **21:30 JST**。その日のJ-Quants日次・EDINET更新を拾いやすく、Discordで夜の分析に回しやすい。
  06:30 JST は前夜失敗時の再試行、重い全件棚卸しは週末に回す。

## コスト・上限
- 追加費用なし(サブスク内)。**お金でなく使用“上限”**に注意(Proで足りなければMax)。
- 定期自動化(`claude -p`)は 2026/6/15 以降 別クレジット枠。
- J-Quants / EDINET DB 有料データ層は**別トラック**(`DATA_LAYER_SPEC.md`)。**A0/A1=実装済・実キー疎通OK**。確認は `python3 -m radar data-check --offline` / `python3 -m radar data-check --live --provider jquants|edinet-db`。
- A1の疎通OKは「実キーで最小endpointが 200 + JSON object を返した」の意味。鍵有効性の監査証跡にする前に、同じendpointが無効キーで 401/403 になる負例確認を値なしで記録する。
- EDINET DB `companies` / `financials` の minimal sync は本人確認済みの個人内 raw 一時キャッシュ前提で GO。**J-Quants sync と Claude等LLMへの取得本文投入は NO-GO維持**。radarコア(mirror/check/log/score/review)・target-check・value-audit(Phase A・手入力 snapshot)は**この層なしで動く**。
- Daloopa は**外部分析補助の別レーン**(`DALOOPA_LANE_SPEC.md`)。OAuth/setup確認までは `discover_companies("AAPL")` の疎通 probe 以外を実行しない。tearsheet/DCF/earnings review は setup成功後も本体data層へ混ぜず、保有株の仮説点検メモに限定する。

## 安全
- Botは **allowlist で自分だけ**。トークンはパスワード扱い(漏れたら再生成)。
- `ANTHROPIC_API_KEY` は未設定。自動発注はしない(分析・通知・記録まで)。

## まだ未実装(実運用後に必要なら)
`analyze`(日本中小型スクリーニング)・`backtest`・過熱の価格自動判定・J-Quants `data`接続・Obsidian自動連携。
