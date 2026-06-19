# SYNC_PHASE_B_PLAN — 最小 sync(Phase B)実装計画

> 正は DATA_LAYER_SPEC.md(§5 provenance / §6 PIT / §7 raw/manifest / §14 エラー / §16 Phase) /
> LICENSE_MATRIX.md / DATASET_SCOPE.md / DESIGN_PRINCIPLES.md / CLAIMS.md / CLAUDE.md。
> 対象 dataset は DATASET_SCOPE.md の結論 = **EDINET DB `companies`(企業マスタ)** から開始。
> `1494ce8` 以降で `companies` の最小実装済み。`372a62e` 以降で境界を強化。
> 2026-06-18 の本人確認により、EDINET DB の個人内 raw 一時キャッシュ運用は **Phase B の範囲でGO**。
> ただし **第三者LLM入力 / 再配布 / feature / research_queue / evidence は引き続き範囲外**。

## 1. 目的 / 非目的
- **目的**: 「取得 → `data/raw` 保存 → provenance 記録 → hash → PIT(available_at) → manifest」という
  **sync の骨格**を、まず **EDINET DB companies**、次に **EDINET DB financials(1 EDINET code / 予算付きbatch)** で成立させ、**raw_hash で再現可能**にする。
- **非目的(やらない)**: feature 生成 / research_item 生成 / evidence / **第三者LLM入力** / ランキング /
  買い候補 / 推奨 / 予測 / 複数 provider・複数 dataset への拡大 / Daloopa 統合。

## 2. provider / dataset / endpoint(候補・要・本人確認)
- provider: `edinet-db`(REST 正・`edinetdb.jp/v1`、auth=X-API-Key)。MCP は探索補助で sync には使わない(REST=記録の正)。
- dataset:
  - `companies`(企業マスタ): entity mapping の起点。
  - `financials`(財務): **1 EDINET code + years + period** が基本単位。batch はこの単位を順次実行するだけで、feature化はしない。
- endpoint: `/companies`(最小取得。`per_page` を最小、必要なら `page` で逐次)。
  - `financials`: `/companies/{code}/financials`。query は `years` と `period=annual|quarterly|quarterly_standalone`。
  - ⚠️ endpoint / ページング / レスポンス形は **公式 API docs(`edinetdb.jp/docs/api`)で本人確認**し、config 駆動で固定する。
- 取得単位: **1 ページ(最小 per_page)から**。全件取得は配管検証が通ってから。

## 3. 保存先・retention
```
data/raw/edinet-db/companies/<asof>/page_<n>.json   # 取得バイト列(raw・git除外)
data/raw/edinet-db/financials/<asof>/<edinet_code>_period-<period>_years-<n>.json
data/metadata/fetch_log.jsonl                        # 1 fetch=1行(provenance・追記専用)
data/metadata/edinetdb_financials_batch_<asof>_offset-<n>_limit-<n>.json
data/metadata/dataset_manifest.json                  # 索引(任意・B後半)
```
- **raw はローカル限定**。`data/raw` 以外に漏らさない。`outputs/` や journal には書かない。
- **gitignore 必須**(既存 `.gitignore` に `data/raw/ data/cache/ data/derived/` 済。`data/metadata/` の実データも追加検討)。
- **retention/purge**: 本人確認済みの個人利用前提では、当面は **手動 purge + 定期再取得**で運用する。
  purge は再現情報(provenance + 必要なら derived)確保後のみ(DATA_LAYER §7)。
- **現時点の purge は手動**。`license_scope=personal/local-temporary-cache/no-redistribution/no-raw-llm` は
  一時キャッシュ方針の宣言であり、自動 purge/再取得ロジックの実装完了を意味しない。
  E3 確定後に TTL / purge コマンド / manifest 更新のいずれかを追加する。
- **キー値・response 本文をログ/出力/例外/Claude に出さない**(redact 必須・A1 と同じ規律)。

## 4. provenance 必須フィールド(DATA_LAYER §5 準拠)
1 fetch = 1 行(`data/metadata/fetch_log.jsonl`)。最低限:
- `provider`(=edinet-db) / `dataset`(=companies|financials) / `endpoint` / `params`
- `asof` / `available_at`(companies はほぼ静的 → retrieved_at を当日終端 tz付きで) / `retrieved_at`(tz付き)
- `raw_hash_compressed` / `raw_hash_normalized` / `hash_algorithm`(=sha256) / `normalization_version`
- `content_type` / `raw_size`
- `source_url`(キー秘匿値を含めない) / `license_scope`(=personal) / `plan_or_limit` /
  `schema_version` / `fetch_id`
- companies 固有: `company_id` / `edinet_code` / `securities_code` /(あれば)`isin`(entity mapping の起点)
- financials 固有: `edinet_code` / `period_end` / `submit_date` / `disclosure_date` /(あれば)`source_doc_id`
> 既存 `radar/sources/provenance.py` の `make_provenance / validate_provenance / append_fetch_log` を流用
> (全必須キーを None 既定で埋める設計)。**書込は渡した metadata_dir 配下のみ**(source層の書込スコープ)。

## 5. hash 方針
- `sha256`。`raw_hash_compressed`(取得バイト列)と `raw_hash_normalized`(JSON を sort_keys 正規化後)の2本。
  既存 `common.hash_bytes / normalize_json_bytes` を流用。**同一 fetch は raw_hash 一致**を再現性の証跡にする。

## 6. asof / PIT ルール(DATA_LAYER §6)
- 採用は `available_at <= asof` のみ(未来データ不参照)。
- companies は静的 → `available_at = retrieved_at`(当日終端の tz付き時刻)。`asof` が日付のみなら当日末で比較。
- このため、現行実装は **live取得した企業マスタの保存**に限る。`available_at=retrieved_at` なので、
  過去 `asof` へのバックフィルはPIT違反として拒否される。過去時点の企業マスタ再現は別設計(entity履歴)で扱う。
- financials は `available_at` / `disclosure_date` / `submit_date` のうち取れる提出・開示時刻を使う。
  `asof` 日付は JST 当日末で比較し、未来データなら raw を保存しない。日時が無い場合は retrieved_at を fallback とする。
- latest は参考表示可・検証(将来の score)には使わない。

## 7. LLM 非投入ルール(致命)
- sync が取得した **raw / 本文を Claude(第三者LLM)に渡さない・要約もしない・プロンプトに載せない**。
- B の成果物は **ファイル(raw + provenance)だけ**。人間が見るのは「件数・hash・保存先・鮮度」などメタのみ。
- 第三者LLM入力(E5/J5)は LICENSE_MATRIX 未確認 → B では一切踏み出さない。

## 8. エラー時挙動(DATA_LAYER §14・A1 と一貫)
| 事象 | 挙動 |
|---|---|
| キー未設定 | SystemExit(値非表示) |
| 401 / 403 | 即停止・redact(再試行しない) |
| 429 | 指数バックオフ(retry_max まで)→ 上限で停止 |
| 5xx / network / timeout | retry_max まで再試行 → 失敗は**欠損として停止**(redact) |
| 壊れ JSON / 非 dict root | SystemExit(明示・本文は出さない) |
| 巨大レスポンス | `max_response_bytes` 超で停止 |
| 部分成功(ページ途中) | 取得分のみ raw 保存 + **欠損を明示**(黙って埋めない) |
| nan/inf/欠損値 | 当該値 UNKNOWN 保持(0 にしない・companies では基本該当せず) |

## 9. CLI 契約(最小実装済み)
```
python3 -m radar sync --provider edinet-db --dataset companies [--asof YYYY-MM-DD] [--page N --per-page K]
python3 -m radar sync --provider edinet-db --dataset financials --code E02367 [--asof YYYY-MM-DD] [--years N --period annual]
python3 -m radar sync --provider edinet-db --dataset financials --codes-file data/metadata/edinetdb_company_codes_YYYYMMDD.txt [--asof YYYY-MM-DD] [--offset N --limit K --years N --period annual]
```
- `--asof` は厳密 `YYYY-MM-DD`(既存 mirror/score/target-check と同実装)。
- `--codes-file` は `data/metadata` 配下の EDINETコード一覧に限定。空行・`#`コメント・CSVヘッダは無視。
- `--code` と `--codes-file` は排他。batch は `data_layer.daily_request_budget` 以下の `--limit` で小分け実行し、同一 `asof` の既存 batch manifest の `total_attempts` を既使用分として扱う。
- batch は既存 raw+provenance が hash/PIT/params 一致なら再取得せず `skipped_existing` にする。壊れた sidecar は再取得対象。
- batch は最初の失敗で停止し、manifest に redacted class のみ記録し、CLI は非0で停止する。`next_offset` / `retry_offset` を使って失敗地点から再開する。
- 既存 6コマンド + value-audit + `data-check` の I/O は不変(純加法)。
- 出力先・件数・hash・鮮度・欠損・注意を端末に表示(**本文・キーは出さない**)。

## 10. テスト計画(オフライン・fake client / clock)
- fake client で 200/401/403/429/5xx/timeout/壊れJSON/非dict/巨大/部分成功。
- **キー値・本文が stdout/stderr/log/例外/戻り値に出ない** sentinel。
- raw 書込先が `data/raw/edinet-db/companies/...` または `data/raw/edinet-db/financials/...` のみ(脱出しない・他を汚さない)。
- provenance に必須フィールドが揃い、`available_at`/`retrieved_at` が tz付き。
- 同一 fetch で `raw_hash_*` 一致(再現性)。fetch_log 追記専用。
- PIT: `available_at > asof` を採用しない。
- financials batch: `--code`/`--codes-file` 排他、invalid code は fetch 前に停止、重複は決定的に skip、`--offset/--limit` 順序、budget超過拒否、skip-existing の sidecar/hash 検証、partial failure manifest。
- **既存非回帰**: mirror/check/log/score/review/target-check/value-audit/data-check の I/O 不変・全 --help。

## 11. GO / NO-GO ゲート
- **コード実装: GO**(EDINET DB companies + financials の最小単位・オフラインテスト必須)。
- **live sync 運用: EDINET DB の個人利用・raw一時キャッシュについて本人確認済みの前提でGO**。
- **第三者LLM入力 / 再配布 / feature / research_queue / evidence: NO-GO 維持**。
- **運用GO 条件(すべて満たす)**:
  1. EDINET DB は個人内利用・ローカル一時キャッシュ・再配布禁止を本人確認済み。
  2. raw は `data/raw` の git除外領域に限定し、本文を端末・ログ・LLMに出さない。
  3. purge は手動運用。反復・大規模化前に TTL / purge コマンド / manifest のいずれかを追加検討。
  4. EDINET DB **公式 API docs で `/companies` と `/companies/{code}/financials` の endpoint/パラメータ/X-API-Key** を確認。
- これらが揃ったら **EDINET DB companies 1ページ / financials 1社 → raw+provenance 保存 → hash 再現** を運用上もGO。

## 12. A1 との差分
| | A1(実装済) | B(本計画) |
|---|---|---|
| ネット | 疎通のみ(GET 1回) | 取得して **raw 保存** |
| 保存 | **しない** | `data/raw` + `data/metadata`(provenance) |
| 本文 | 読まず捨てる(形だけ) | raw を保存(LLM には渡さない) |
| 出力 | status/success/redact error | 件数/hash/保存先/鮮度(本文・キーなし) |
| ゲート | J1/E1(プログラム利用)で可 | **E2/E3/E7 + endpoint 確認**で可 |

## 13. Phase C(feature)へ渡す最小成果物
- `data/raw/edinet-db/companies/<asof>/*.json` と `data/raw/edinet-db/financials/<asof>/*.json`(raw)+ `fetch_log.jsonl`(provenance)。
- これが **entity master**(edinet_code↔securities_code↔company_id)として Phase C の名寄せ・feature 入力の起点になる。
- **Phase C(feature 生成)・research_queue・evidence・LLM 投入は本書の範囲外**(別 Phase・別ゲート)。

> ※本書は投資助言ではない。最小 sync の安全な実装契約であり、取得データを売買判断・推奨・予測に使わない。
