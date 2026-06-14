# DATA_LAYER_SPEC — J-Quants + EDINET DB データ/リサーチ層の契約(v2・実装前)

> 設計のみ。実装はこの契約の帰結。正は DESIGN_PRINCIPLES.md / SPEC.md / CLAIMS.md / CLAUDE.md。
> ⚠️ `LICENSE_MATRIX.md` の ToS 確認が埋まるまで **A1疎通・sync 実装は NO-GO**(D1)。**A0(ネットワーク無し)のみGO**。

## 0. 目的 / 非目的
- **目的**: J-Quants(有料)+ EDINET DB のデータから **research_queue(調査候補)** と **evidence pack(根拠)** を生成。
- **非目的**: 自動売買 / 売買推奨 / シグナル化 / スクレイピング / API再配布 / LLM推測で財務数値を作る / 既存5コマンドを壊す。
- **絶対**: 売買断定しない。**discipline gate 前に買い候補を出さない**。最終判断は人間。

## 1. 既存原則との関係 / 非回帰
- 純加法的(新規CLI/モジュールのみ)。既存 `mirror/check/log/score/review` の CLI/I/O/既定挙動は不変(D9)。
- 未来不参照・ファイル=真実・claim分類(FACT/CALCULATION/INFERENCE/ASSUMPTION/UNKNOWN/UNSAFE)を継承。

## 2. secrets / config
- `.env`: `JQUANTS_API_KEY` / `EDINETDB_API_KEY`。`.env.example` はキー名のみ。未設定は SystemExit(値非表示)。
- **キーを stdout/stderr/log/例外/raw/出力に出さない**(redact 必須)。Authorization ヘッダもログ化しない。
- **redact/gitignore 対象**: `.env`, `.claude/settings.local.json`, `.cursor/mcp.json`, その他MCPクライアント設定, `data/raw`, `data/cache`, `data/derived`(実データ)。
- **運用パラメータは config 化**(A1前に確定・コード直書き禁止): `retry_max`(例3)/ `backoff_base_sec`(例2)/ `max_response_bytes` / `daily_request_budget`(レート上限の消費予算)。

## 3. source 層 I/F(`radar/sources/`)
- `common.fetch(provider, endpoint, params, *, client, clock) -> (raw, meta)`。**client/clock 注入可能**(D8)。
- 失敗時の挙動は §13 の表に**一意化**(「停止 or リトライ」のような選択余地を残さない)。
- `jquants.py` / `edinet_db.py` は common を使う薄いアダプタ。EDINET DB REST=`edinetdb.com/v1/`、MCP=`edinetdb.jp/mcp`。

## 4. REST / MCP 役割分担(D5)
- **REST = 記録の正**(`sync` で raw 保存 + provenance)。再現性の本線。
- **MCP = 探索・補助のみ**。MCP を判断に使う場合、**保存対象 = tool名・引数・レスポンス本文・retrieved_at・raw_hash**(session/system promptは除く)を raw化。
- MCP 設定にキーが入る → `.claude/settings.local.json` / `.cursor/mcp.json` を gitignore。

## 5. provenance / metadata schema(全 raw・全出力に必須 / D3 拡張)
```jsonc
{
  "provider":"jquants|edinet_db", "dataset":"prices|financials|ratios|...",
  "endpoint":"...", "params":{}, "schema_version":"1",
  "fetch_id":"uuid", "retrieved_at":"ISO8601(UTC,tz付)",
  "raw_hash_compressed":"sha256(取得バイト列)", "raw_hash_normalized":"sha256(正規化後)",
  "hash_algorithm":"sha256", "normalization_version":"1",
  "raw_size":0, "content_type":"application/json|text/csv", "vendor_last_modified":"...|null",
  "period_end":"YYYY-MM-DD", "submit_date":"YYYY-MM-DD", "disclosure_date":"YYYY-MM-DD",
  "available_at":"ISO8601(datetime,tz付)",                      // PIT(§6)。日付粒度は当日終端の時刻
  "entity_id":"...", "securities_code":"7203", "edinet_code":"E0...", "company_id":"...", "isin":"...|null",
  "currency":"JPY", "unit":"円|千円|百万円",
  "accounting_standard":"JP GAAP|IFRS|US GAAP", "consolidated":true,
  "source_doc_id":"FSA EDINET docID", "source_url":"...", "license_scope":"personal", "plan_or_limit":"..."
}
```

## 6. PIT(ポイントインタイム)ルール(D2・致命)
- **build/検証は `available_at <= asof` のみ採用**。latest は evidence 本文で参考表示可・**検証(score)には使わない**。
- 日足は **取引日の JST 引け後に available** とし、**日中時刻の asof では当日を採用しない**(時刻・tz を持つ)。
- `available_at` は **datetime(tz付)に統一**。日付粒度の dataset は「当日終端の時刻」を入れる。`asof` が日付のみなら **当日末** を asof として比較(date/datetime 混在を排除)。
- dataset 別 `available_at` 導出(全対象):

| dataset | provider | available_at |
|---|---|---|
| listed-info / companies | both | retrieved_at(ほぼ静的・コード変更は entity履歴で管理) |
| prices(日足) | jquants | 取引日(JST引け後) |
| financials | both | disclosure_date。無ければ submit_date |
| dividends | jquants | 公表日 |
| earnings-calendar | jquants | 公表日(予定→確報で置換、版を持つ) |
| ratios / analysis(scores) / rankings / industries | edinet_db | **元 financials の available_at を継承**(派生)。**scores は INFERENCE** |
| text-blocks | edinet_db | submit_date / disclosure_date |
| bulk(J-Quants) | jquants | **各レコード本来の available_at を尊重**(bulkでもPIT個別適用) |

## 7. raw / cache / derived / manifest(D4 修正)
```
data/raw/<provider>/<dataset>/...      # cache・git除外
data/cache/                            # git除外
data/metadata/fetch_log.jsonl          # 追記専用: 1 fetch = 1 行(provenance)
data/metadata/dataset_manifest.json    # 索引
data/derived/<feature_set>/<asof>.json # 使用入力フィールド + 各raw_hash_normalized + feature_registry_version + config_hash + code_commit を内包
```
- **再現性モデル(修正)**: 検証に使うデータは **(a) raw を保持** または **(b) derived に“使用フィールドのスナップショット + raw_hash_normalized + feature_registry_version + config_hash + code_commit”を内包**(コード・設定・式の版まで固定して初めて再現可能)。
  raw_hash 単独では再計算できない。**vendor改訂/削除で再fetchは別物になり得るため、purge は (b) 完了後に限り可**。
- 真実 = provenance + derived(snapshot+版情報入り) + manifest。raw は purgeable cache。
- hash方針: `sha256`。**`raw_hash_compressed`(取得バイト列)と `raw_hash_normalized`(正規化後)の2フィールド**、`normalization_version`・`content_type` を併記。

## 8. feature 定義(`radar/features/` + レジストリ必須)
- **feature レジストリ**(宣言的): 各 feature に `id / 分類(official|own|proxy) / 式 / 必須入力(dataset.field) / 単位 / UNKNOWN条件 / 除外ルール`。
- 欠損 / nan / inf / 非数値は**黙殺せず当該値を UNKNOWN 保持**(計算は停止しない)。UNKNOWN は queue/score で**除外 or 明示**。
- 最小例(式はレジストリに明記): 売上/営業利益 成長率・営業利益率・ROE・ROIC proxy・FCF・FCF利回り・自己資本比率・ネットキャッシュ proxy・配当利回り/性向/増配・株数変化・出来高/売買代金・モメンタム・過熱度・(あれば)信用倍率・セグメント依存・大株主変化・健全性リスク。
- **代表featureの具体式(分類・入力field・UNKNOWN条件)の確定は Phase C の前提**。例: `ROE = 当期純利益 / 期中平均自己資本`(分類=own / 入力=financials.net_income, financials.equity / 欠損→UNKNOWN)。

## 9. entity マッピング
- 主キー候補: `securities_code`(J-Quants) ↔ `edinet_code`(EDINET DB) ↔ `company_id` ↔ `isin`。
- **コード変更・上場廃止・社名変更の履歴**を持ち、結合は as_of 時点で解決。未解決は UNKNOWN。
- **履歴ソース(どの dataset を正とするか)・衝突時の優先規則・コード再割当の扱い**を mapping 定義に明記(Phase B の前提)。

## 10. research_queue schema(`radar/research/queue.py` / D6・語彙ロック強化)
```jsonc
{
  "type":"research_item",                  // ★固定。buy_candidate 等の語は禁止
  "ticker","company_name","market","sector","liquidity","data_freshness",
  "extraction_reason_id":"screen:<id>",    // ★宣言的config由来のみ。自由文の推奨表現禁止
  "evidence_refs":[ /* provenance */ ],
  "key_risks":[], "falsification":[],      // 必須
  "next_to_read":[],                       // EDINET docID / IR
  "discipline_status":"未通過",            // ★固定・必須
  "coverage_priority": 0,                   // ★並べ替えに使う場合のみ。名称は“網羅度”。魅力度/期待リターン順は禁止
  "claim_tags":{},
  "disclaimer":"調査候補。買い推奨ではない。売買は discipline check + 人間判断が必要。"
}
```

## 11. evidence schema(`radar/research/evidence.py`)
- 含む: 概要 / 鮮度 / 由来別データ / 財務推移 / 収益性 / 資本効率 / 安全性 / 還元 / 流動性 / 過熱度 / 大株主・セグメント / 仮説 / 弱気 / 反証 / 次資料 / 免責。各主張に claim 分類 + source/as_of。
- **`discipline用 action 例` は「人間が自分で `check` に通すための雛形文字列(金額はプレースホルダ)」に限定**。例: `check buy <TICKER> <AMOUNT> <SECTOR>`。**具体金額・売買案・推奨は禁止**。

## 12. claim_audit 統合(`radar/research/claim_audit.py`)
- コード側=機械分類、`CLAIMS.md`/`claim-auditor`=テキスト監査。
- **EDINET DB の AI所見・analysis scores は FACT 禁止 → INFERENCE/ASSUMPTION**。原データに遡及可能に。

## 13. CLI 契約(既存5コマンド不変・追加)
| cmd | 文法 | 出力 | network |
|---|---|---|---|
| `data-check` | `data-check` | 端末(key redact) | A1のみ・軽量疎通 |
| `sync` | `sync <jquants\|edinet-db> --dataset <name> [--from YYYY-MM-DD --to YYYY-MM-DD] [--ticker X]` | `data/raw`+metadata | あり |
| `build-features` | `build-features [--asof YYYY-MM-DD]` | `data/derived` | なし |
| `research-queue` | `research-queue [--asof YYYY-MM-DD]` | `outputs/research_queue.md/.csv` | なし |
| `evidence` | `evidence <ticker> [--asof YYYY-MM-DD]` | `outputs/evidence/<ticker>.md` | なし |
| `claim-audit` | `claim-audit <file>` | 端末 | なし |
- `--asof` は厳密 `YYYY-MM-DD` 検証(既存 mirror/score と同実装)。各コマンドは 入力/出力先/鮮度/欠損/注意 を表示。

## 14. エラー / エッジ挙動(一意化)
| 事象 | 挙動 |
|---|---|
| キー未設定 | SystemExit(値非表示) |
| 401 / 403 | 即停止・redact |
| 429 | 指数バックオフ(最大N回)→ 上限で停止 |
| network失敗 / 5xx | 最大N回リトライ→失敗は**欠損として停止**(古いraw流用時は鮮度警告) |
| 部分成功 | 取得分のみ保存 + **欠損を明示** |
| 壊れJSON / 非dict root / CSV列欠損 / gzip破損 | SystemExit(明示) |
| nan / inf / 非数値 | 当該値 UNKNOWN 保持(黙殺禁止) |
| 巨大レスポンス | 上限超で停止(上限を config 化) |

## 15. テスト一覧(オフライン・fake HTTP/clock)
キー未設定 / **キーがログ・例外・出力に出ない** / network失敗 / 401・403・429・5xx / 壊れJSON / 非dict / CSV列欠損 / nan・inf / 欠損 / same fetch の raw_hash 一致 / fetch_log 追記 / **source層が data/raw・data/metadata 以外に書かない**(build/output層は所定出力のみ) / research_queue が「買い候補」を書かない / evidence が売買断定しない・action例が金額入り売買案でない / **既存5コマンド非回帰**。

## 16. Phase 境界 と Phase別 完了条件
- **A0(ネットワーク無し)** ← GO可:secrets/config/gitignore/注入可能client・clock/provenance・fetch_log のスキーマ定義/offlineテスト。完了=キー処理・redact・スキーマ・テストが揃い、ネット接続コードは無い。
- **A1(軽量疎通)** ← ToS確認後:`data-check`(key存在+最小疎通、失敗時redact)。完了=キーを見せず疎通可否を返す。
- **B**:最小 sync(listed-info / financials / prices)+ raw + metadata + manifest。完了=raw+provenanceが保存され raw_hash再現。
- **C**:features レジストリ + research_queue。完了=research_queue.md 生成・推奨漏れ無し。
- **D**:evidence + claim_audit。完了=evidence/<ticker>.md 生成・売買断定無し・全主張 claim分類。
- **E**:既存への導線 + README/CLAUDE/SPEC 更新 + 監査。
