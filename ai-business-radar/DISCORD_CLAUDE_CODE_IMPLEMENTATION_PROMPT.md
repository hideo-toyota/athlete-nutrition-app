# Claude Code 実装プロンプト — Discord運用を `daily-update` に集約

以下を Claude Code にそのまま渡す。

---

あなたは `ai-business-radar` のシニア実装者兼、安全設計の監査役です。
目的は、既存の Discord + Claude Code 連携から、現在の投資分析パイプラインを安全に実行できる形にすることです。

実装は「Discord Bot本体を作る」ことではなく、Claude Code が Discord 経由の自然文指示を受けた時に、迷わず実行できる **一括CLI `daily-update`** を追加することです。

## 正

- `DESIGN_PRINCIPLES.md`
- `CLAUDE.md`
- `CLAIMS.md`
- `DATA_LAYER_SPEC.md`
- `SYNC_PHASE_B_PLAN.md`
- `FEATURE_PHASE_C_SPEC.md`
- `FEATURE_PHASE_C_PLAN.md`
- `README.md`
- `RUNBOOK.md`
- 既存実装:
  - `radar/__main__.py`
  - `radar/sources/edinet_db.py`
  - `radar/features/build.py`
  - `radar/research/*`
  - `tests/test_b_sync.py`
  - `tests/test_feature_phase_c.py`

## 現在地

- EDINET DB financials batch sync は実装済み。
- `sync --provider edinet-db --dataset financials --codes-file ... --offset ... --limit ...` が動く。
- `build-features --raw-dir ...` が動く。
- J-Quants Premium Bulk はユーザー許可済み raw が `data/raw/jquants/bulk` に取得済みの場合、`build-jquants-features --asof YYYY-MM-DD` でローカル derived feature を生成できる。
- `research-queue` が derived features から調査項目を生成する。
- `llm-brief` は LLM API を呼ばず、手渡し用 packet だけ生成する。
- `outputs/honest_mirror.md` に既存未コミット差分がある場合がある。今回の実装では触らない。

## 絶対制約

- APIキー値、`.env`、response本文、raw本文を stdout/stderr/log/例外/出力/commit に出さない。
- `data/raw` / `data/metadata` / `data/derived` の実データは commit しない。
- 実LLM API送信は実装しない。
- 自動売買・買い候補・ランキング・期待リターン順・推奨・予測を出さない。
- Daloopa / J-Quants **API sync** / 新provider には踏み出さない。
- J-Quants は **取得済み Premium Bulk raw のローカル derived feature 生成のみ**許可する。J-Quants APIキーを読まない・外部接続しない。
- 既存 `mirror/check/log/score/review/target-check/value-audit/data-check/sync/build-features/research-queue/evidence/llm-brief` の既定I/Oを壊さない。
- Discord側では「通知・要約」まで。発注や外部送信の自動実行はしない。

## 実装するもの

### 1. 新CLI

`python3 -m radar daily-update`

引数:

```bash
python3 -m radar daily-update \
  --asof YYYY-MM-DD \
  --edinet-codes-file data/metadata/edinetdb_company_codes_YYYYMMDD.txt \
  --edinet-offset N \
  --edinet-limit K \
  --years 5 \
  --period annual \
  --jquants auto \
  --max-brief-items 50
```

任意:

```bash
--dry-run
--skip-sync
--skip-features
--skip-jquants
--skip-research
--skip-brief
```

### 2. 挙動

`daily-update` は次を順に実行する。

1. `--asof` を厳密 `YYYY-MM-DD` で検証。
2. `--dry-run` なら、実行予定だけ表示し、外部接続・書込をしない。
3. `--skip-sync` が無ければ:
   - `edinet_db.sync_financials_batch(...)`
   - `--edinet-codes-file`
   - `--edinet-offset`
   - `--edinet-limit`
   - `--years`
   - `--period`
   を使う。
   - 失敗が1件でもあれば、`outputs/daily_update_<asof>.md/json` に manifest path と `retry_offset` を記録し、非0終了。
4. `--skip-features` が無ければ:
   - `build_financial_features_batch(raw_dir=data/raw/edinet-db/financials/<asof>, asof=<asof>)`
   - 失敗があれば非0終了。
5. `--skip-jquants` が無ければ:
   - `--jquants auto|on|off` を扱う。既定は `auto`。
   - `auto`: `data/raw/jquants/bulk` が存在する場合だけ `build_jquants_bulk_features(asof=<asof>)` を実行。無ければ `skipped` として report に記録し、失敗にしない。
   - `on`: `data/raw/jquants/bulk` が無ければ非0終了。存在すれば `build_jquants_bulk_features(asof=<asof>)` を実行。
   - `off`: J-Quants feature生成をしない。
   - ここでは **J-Quants API sync / bulk download / data-check live は実行しない**。
   - 出力は `data/derived/features/jquants_equity_v1/<asof>/features.jsonl`, `summary.md`, `manifest.json` のパスと件数だけ report に含める。raw CSV本文は出さない。
6. `--skip-research` が無ければ:
   - `build_research_queue(asof=<asof>)`
   - `write_research_queue(...)`
   - 現時点の research_queue は EDINET DB feature を主入力とする。J-Quants feature は daily report の「market breadth / coverage / price・momentum補助データ」として別枠表示し、買い候補化・ランキング化しない。
7. `--skip-brief` が無ければ:
   - `build_llm_handoff(asof=<asof>, max_items=<max-brief-items>)`
   - `write_llm_handoff(...)`
   - LLM APIは呼ばない。
8. 最後に `outputs/daily_update_<asof>.md` と `outputs/daily_update_<asof>.json` を生成する。

### 3. daily update report に含めるもの

含める:

- asof
- sync selected/saved/skipped/failure/next_offset/retry_offset/manifest path
- features candidate/built/failure/manifest path
- J-Quants local features:
  - mode(auto/on/off/skipped)
  - listed_codes / feature_rows / input_file_count
  - price_coverage / summary_coverage / dividend_coverage
  - latest_price_date
  - summary_path / manifest_path / features_path
- research_queue item count / output paths
- llm_brief evidence block count / output paths
- 次に実行すべき command 例
- 注意:
  - raw本文なし
  - APIキー値なし
  - LLM API未送信
  - 買い推奨なし
  - 最終判断は人間

含めない:

- APIキー
- response本文
- raw本文
- J-Quants raw CSV本文
- `.env`
- 「買うべき」「おすすめ」「期待リターン順」「ランキング」

### 4. Discord用プロンプトを追加

`PROMPTS.md` に以下の運用プロンプトを追加する。

```text
今日の更新を実行して。
asof=<YYYY-MM-DD>
EDINET DB financials を offset=<N> limit=<K> で取得し、
EDINET features → J-Quants local features → research_queue → llm-brief まで更新して。
raw本文・APIキー値は出さない。LLM API送信はしない。買い推奨・ランキング・予測は出さない。
完了後、件数・失敗・next_offset・次のコマンドだけ教えて。
```

短縮形:

```text
今日の更新 offset=<N> limit=<K>
```

Claude Code は短縮形を受けたら、`python3 -m radar daily-update ...` に展開する。
J-Quants raw がある環境では `--jquants auto` を既定にし、J-Quants API sync は実行しない。

## 実装方針

- 可能なら `radar/daily_update.py` を新設し、実処理はそこに置く。
- `radar/__main__.py` は CLI配線だけにする。
- `daily_update.py` は既存関数を呼ぶ orchestration 層に徹する。
- ネットワーク処理は既存 `sync_financials_batch` だけが行う。
- feature/research/brief は既存関数を使う。
- J-Quants は既存 `build_jquants_bulk_features` を使う。新しい network source は作らない。
- Discord plugin 依存コードは書かない。Claude Code が既存 Discord plugin 経由でこのCLIを呼べれば十分。

## テスト

追加する。

- `tests/test_daily_update.py`

必須ケース:

1. `--help` が落ちない。
2. `--dry-run` は外部接続・書込をしない。
3. sync failure がある場合:
   - report を書く
   - `retry_offset` を出す
   - 非0終了
   - raw本文/APIキー値が report に無い
4. success path:
   - sync/features/jquants/research/brief の各結果をまとめる
   - `outputs/daily_update_<asof>.md/json` を書く
5. `--jquants auto` で raw が無い場合は skipped になり、失敗しない。
6. `--jquants on` で raw が無い場合は非0終了。
7. `--skip-sync` / `--skip-features` / `--skip-jquants` など skip オプションが効く。
8. `--max-brief-items <= 0` を拒否。
9. 禁止語ガード:
   - report に `buy_candidate`
   - `おすすめ`
   - `買うべき`
   - `期待リターン順`
   - `ランキング`
   が出ない。

既存テストも通す。

```bash
python3 -m py_compile radar/*.py radar/sources/*.py radar/features/*.py radar/research/*.py
python3 -m unittest -q
python3 -m radar daily-update --help
python3 -m radar daily-update --asof 2026-06-20 --edinet-codes-file data/metadata/edinetdb_company_codes_20260619.txt --edinet-offset 1200 --edinet-limit 1 --years 5 --period annual --jquants auto --max-brief-items 5 --dry-run
```

## 完了条件

- `daily-update` が実装済み。
- Discordから Claude Code に「今日の更新 offset=1200 limit=200」と投げれば、Claude Code が実行すべきCLIを迷わない。
- J-Quants raw bulk がある場合、`daily-update --jquants auto` で `build-jquants-features` まで実行され、report に coverage と出力pathが出る。
- J-Quants raw bulk が無い場合も `auto` では安全に skipped となり、EDINET pipeline は止まらない。
- `dry-run` で安全に予定確認できる。
- 実行後に `outputs/daily_update_<asof>.md/json` が残る。
- raw本文/APIキー値/LLM API送信なし。
- 既存コマンド非回帰。
- tests all green。
- commit/push。

## コミットメッセージ

```text
Add daily update orchestration CLI
```

---
