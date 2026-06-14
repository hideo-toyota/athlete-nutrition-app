# DATA_LAYER_SPEC — J-Quants + EDINET DB データ/リサーチ層の契約(雛形・実装前)

> 設計のみ。実装はこの契約の帰結。正は [DESIGN_PRINCIPLES.md] / [SPEC.md] / [CLAIMS.md] / [CLAUDE.md]。
> ⚠️ これは**雛形**。`LICENSE_MATRIX.md` の ToS 確認が埋まるまで **sync 実装は NO-GO**(D1)。

## 0. 目的 / 非目的
- **目的**: J-Quants(有料)と EDINET DB のデータから **research_queue(調査候補)** と **evidence pack(根拠パック)** を生成する。
- **非目的**: 自動売買 / 売買推奨 / シグナル化 / スクレイピング / API再配布 / LLM推測で財務数値を作る / 既存 `mirror/check/log/score/review` を壊す。
- **絶対**: 売買断定しない。**discipline gate 前に買い候補を出さない**。最終判断は人間。

## 1. 既存原則との関係 / 非回帰
- 純加法的:新規 CLI とモジュールのみ追加。既存5コマンドの CLI/I/O/既定挙動は**変えない**(D9)。
- ファイル=真実・未来不参照・claim分類(FACT/CALCULATION/INFERENCE/ASSUMPTION/UNKNOWN/UNSAFE)を継承。

## 2. secrets / config
- `.env` から読む: `JQUANTS_API_KEY` / `EDINETDB_API_KEY`。`.env.example` はキー名のみ。
- 未設定時は**明確に SystemExit**(キー値はメッセージに含めない)。
- **キーを stdout/stderr/log/例外/raw/出力に出さない**(redact 必須)。Authorization ヘッダもログ化しない。

## 3. source 層 I/F(`radar/sources/`)
- `common.fetch(provider, endpoint, params, *, client, clock) -> (raw, meta)`
  - **client(HTTP)と clock(現在時刻)は注入可能**(オフラインテスト用)(D8)。
  - レート制限考慮(アカウント単位合算)、429 はバックオフ、失敗は欠損として正直に。
- `jquants.py` / `edinet_db.py` は common を使う薄いアダプタ。

## 4. REST / MCP 役割分担(D5)
- **REST = 記録の正**:`sync` で raw 保存 + provenance。再現性の本線。
- **MCP = 探索・補助のみ**。MCP 出力を判断に使うなら **raw化・raw_hash・source・retrieved_at 付与を必須**。
- EDINET DB の **MCP 設定にキーが入る** → `.claude/settings.local.json` を gitignore。

## 5. provenance / metadata schema(全 raw・全出力に必須 / D3)
```jsonc
{
  "provider": "jquants|edinet_db", "dataset": "prices|financials|...",
  "endpoint": "...", "params": { }, "schema_version": "1",
  "fetch_id": "uuid", "period_end": "YYYY-MM-DD", "submit_date": "YYYY-MM-DD",
  "disclosure_date": "YYYY-MM-DD", "available_at": "YYYY-MM-DD",
  "retrieved_at": "ISO8601(UTC,tz付)", "raw_hash": "sha256(正規化後)",
  "source_doc_id": "FSA EDINET docID 等", "currency": "JPY", "unit": "円|千円",
  "license_scope": "personal", "plan_or_limit": "..."
}
```

## 6. PIT(ポイントインタイム)ルール(D2・致命)
- **build/検証は `available_at <= asof` のみ採用**(未来データ混入を構造排除)。
- dataset 別 `available_at` 導出:

| dataset | available_at |
|---|---|
| listed-info | retrieved_at(ほぼ静的) |
| prices(日足) | その取引日(引け後) |
| financials | disclosure_date(適時開示日)。無ければ submit_date |
| dividends / earnings-calendar | 公表日 |

- latest 値は evidence 本文で**参考表示可**だが、**検証(score)には使わない**。

## 7. dataset 保存先 / 形式 / 責務分離(D4)
```
data/
  raw/<provider>/<dataset>/...      # purgeable cache・git除外・docId/paramsから再取得可能
  cache/                            # git除外
  metadata/fetch_log.jsonl          # 追記専用: 1 fetch = 1 行(provenance)
  metadata/dataset_manifest.json    # 索引: dataset → 最新fetch・期間・件数
  derived/<feature_set>/<asof>.json # 入力 raw_hash を内蔵 = raw purge後も自己再現可能
```
- **システムの真実 = provenance + derived + manifest**(raw 本体ではない)。
- `raw_hash` は **gzip展開・正規化後のバイト列**(改行/キー順で揺れない正規化を定義)。
- retention/purge ポリシーを明記(ToS の「一時キャッシュ」範囲は **`LICENSE_MATRIX.md` 確認後に確定**=現状 **未確認**)。

## 8. feature 定義(`radar/features/`)
- 各特徴量を **公式値 / 自前計算(式明記) / proxy(近似・式明記) / UNKNOWN** に分類。
- 欠損 / nan / inf / 非数値は**黙殺せず UNKNOWN として保持**(計算は停止せず、当該値のみ UNKNOWN)。
- 最小例:売上成長率、営業利益率/成長率、ROE、ROIC proxy(式)、FCF、FCF利回り、自己資本比率、ネットキャッシュ proxy(式)、配当利回り/性向/増配傾向、株数変化率、出来高/売買代金、価格モメンタム、過熱度、(あれば)信用倍率、セグメント依存、大株主変化、財務健全性リスク。
- 各 feature 出力に provenance(由来 dataset・as_of)を保持。

## 9. research_queue schema(`radar/research/queue.py` / D6・語彙ロック)
```jsonc
{
  "type": "research_item",                 // ★ buy_candidate 等の語は禁止
  "ticker", "company_name", "market", "sector",
  "liquidity", "data_freshness",
  "extraction_reason",                      // どの宣言的スクリーンで出たか(config由来=ASSUMPTION)
  "evidence_refs": [ /* provenance */ ],    // 根拠データ(出典・as_of)
  "key_risks": [ ], "falsification": [ ],   // リスク・反証条件(必須)
  "next_to_read": [ ],                      // 一次資料(EDINET docID / IR)
  "discipline_status": "未通過",            // ★ 固定・必須
  "claim_tags": { },
  "disclaimer": "調査候補であり買い推奨ではない。売買は discipline check + 人間判断が必要。"
}
```
- スコアで並べる場合も **「調査優先度(網羅度)」と明示**し、魅力度/推奨にしない。テーマだけの抽出は禁止。

## 10. evidence schema(`radar/research/evidence.py`)
- 含む:概要 / データ鮮度 / J-Quants由来 / EDINET DB由来 / 財務推移 / 収益性 / 資本効率 / 財務安全性 / 株主還元 / 流動性 / 過熱度 / 大株主・セグメント / 仮説 / 弱気シナリオ / 反証条件 / 次に読む一次資料 / **discipline用 action 例** / 免責。
- **売買推奨禁止**。各主張に claim 分類 + source/as_of/retrieved_at。

## 11. claim_audit 統合(`radar/research/claim_audit.py`)
- コード側=機械分類、`CLAIMS.md`/`claim-auditor` エージェント=テキスト監査(役割分担)。
- **EDINET DB の AI所見・財務健全性スコア等は FACT 扱い禁止 → INFERENCE/ASSUMPTION**。原データに遡及可能に。

## 12. CLI 契約(既存5コマンドは不変・以下を追加)
| cmd | 入力 | 出力 | network | 鮮度/欠損 |
|---|---|---|---|---|
| `data-check` | `.env` | 端末(key redact) | A1のみ | キー存在+軽量疎通 |
| `sync jquants/edinet-db ...` | API | `data/raw` + metadata | あり | retrieved_at |
| `build-features` | `data/raw` | `data/derived` | なし | 欠損→UNKNOWN |
| `research-queue` | derived+config | `outputs/research_queue.md/.csv` | なし | 未取得/鮮度明示 |
| `evidence <ticker>` | derived+raw | `outputs/evidence/<ticker>.md` | なし | 由来別+as_of |
| `claim-audit <file>` | md | 端末 | なし | — |
| `--asof` | 全 build系で受理 | 時点固定=再現可能 | — | D7 |

## 13. エラー / エッジ挙動
| 事象 | 挙動 |
|---|---|
| キー未設定 | SystemExit(値非表示) |
| 401/403 | 停止・key redact |
| 429 | 指数バックオフ→上限で停止 |
| 500 / network失敗 | 欠損として停止 or 限定リトライ。古いraw流用時は鮮度警告 |
| 壊れJSON / 非dict root | SystemExit(明示) |
| nan/inf/非数値 | 当該値 UNKNOWN 保持(黙殺禁止) |
| gzip破損 | 停止 |
| 空レスポンス | 欠損明示 |

## 14. テスト一覧(オフライン・fake HTTP/clock)
キー未設定 / **キーがログ・例外・出力に出ない** / network失敗 / 401・403・429・500 / 壊れJSON / 非dict / nan・inf / 欠損 / same fetch の raw_hash 一致 / fetch_log 追記 / **data/raw 以外への書込なし** / research_queue が「買い候補」と書かない / evidence が売買断定しない / **既存 mirror/check/log/score/review 非回帰**。

## 15. Phase 境界
- **A0(ネットワーク無し)**:secrets/config/gitignore/注入可能client・clock/provenance・fetch_log の**スキーマ定義**/offlineテスト。← 紙確定後に着手可。
- **A1(軽量疎通)**:`data-check`(key存在+最小疎通、失敗時redact)。← **ToS確認後**。
- **B**:最小 sync(listed-info / financials / prices)+ raw + metadata。
- **C**:features + research_queue。
- **D**:evidence + claim_audit。
- **E**:既存への導線整理 + README/CLAUDE/SPEC 更新 + 監査。

## 16. 完了条件(各Phase)
キーを見せず疎通 / raw+metadata保存 / research_queue.md生成 / evidence/<ticker>.md生成 / 全出力に source・as_of・retrieved_at / 売買断定なし / gate前に買い推奨なし / 既存テスト非回帰。
