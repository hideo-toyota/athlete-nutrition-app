# FEATURE_PHASE_C_SPEC — EDINET DB financials feature layer

> 正: DESIGN_PRINCIPLES.md / CLAIMS.md / DATA_LAYER_SPEC.md / LICENSE_MATRIX.md /
> SYNC_PHASE_B_PLAN.md / EARNINGS_CYCLE_VALUE_AUDIT_SPEC.md。
> これは **Phase C(feature生成)の契約**。実装はこの契約から逸脱しない。

## 0. 判定
- **Phase C 設計: GO**。
- **Phase C minimal 実装スコープ: EDINET DB financials raw → data/derived のみ**。
- **NO-GO 維持**: research_queue / evidence / 第三者LLM入力 / ランキング / 買い候補 / 推奨 / 予測。

## 1. 目的 / 非目的
- 目的: Phase B sync 済みの `data/raw/edinet-db/financials/...` から、監査可能な特徴量を `data/derived` に生成する。
- 非目的: 銘柄抽出、割安判定、スコア順、買い候補、売買判断、DCF、将来予測。
- 出力は「何が計算でき、何が UNKNOWN か」を固定するだけ。投資判断はまだしない。

## 2. 入力契約
Phase C minimal は **明示 raw-path 入力**から始める。自動探索は後段。

```bash
python3 -m radar build-features \
  --provider edinet-db \
  --dataset financials \
  --raw-path data/raw/edinet-db/financials/<asof>/<code>_period-annual_years-<n>.json \
  --asof YYYY-MM-DD
```

必須:
- raw path は `data/raw/edinet-db/financials/` 配下のみ。
- sidecar `<raw>.provenance.json` が存在し、`dataset=financials`、`edinet_code`、`raw_hash_compressed`、`raw_hash_normalized`、`available_at` を持つ。
- `edinet_code` は `^E\d{5}$` で検証してから output path に使う。
- `available_at <= asof`。`available_at` は timezone 付き ISO8601 として parse し、`asof` は **JST 当日末(23:59:59+09:00)** に変換して比較する。未来データなら停止し、derived を書かない。
- Phase C minimal は `period=annual` のみ。quarterly / quarterly_standalone は UNKNOWN が多く、別設計。

## 3. 出力契約
保存先:

```text
data/derived/features/edinet_financials_v1/<asof>/<edinet_code>.json
```

CLIに表示してよいもの:
- output path
- feature_set id/version
- `asof`
- `edinet_code`
- feature件数
- UNKNOWN件数
- input raw hash

CLIに表示してはいけないもの:
- raw本文
- APIキー
- 個別featureの値の全量
- 「割安」「買い候補」「期待リターン」「ランキング」

## 4. derived schema
```json
{
  "schema_version": "1",
  "feature_set": "edinet_financials_v1",
  "feature_registry_version": "1",
  "generated_at": "2026-06-18T12:00:00+00:00",
  "asof": "2026-06-18",
  "provider": "edinet-db",
  "dataset": "financials",
  "edinet_code": "E02144",
  "period": "annual",
  "input": {
    "raw_path": "data/raw/...",
    "provenance_path": "data/raw/...provenance.json",
    "raw_hash_normalized": "sha256...",
    "raw_hash_compressed": "sha256...",
    "available_at": "2026-06-10T15:33:00+09:00",
    "retrieved_at": "2026-06-18T..."
  },
  "build": {
    "config_hash": "sha256...",
    "code_commit": "gitsha-or-UNKNOWN",
    "normalization_version": "1"
  },
  "source_snapshot": {
    "current_period": {},
    "previous_period": {},
    "used_fields": {}
  },
  "features": {}
}
```

`config_hash` の入力集合は、**feature registry / alias registry / feature assumptions / build-features 関連 config**。
Phase C minimal では `roic_proxy` を UNKNOWN 固定にするため、ROIC用 tax_rate assumption は config_hash に含めない。

`source_snapshot.used_fields` は **計算に使った raw field の値だけ**を保持する。raw全文は複製しない。
これにより raw purge 後でも、どの入力から計算されたか監査できる。

## 5. Measured schema
各 feature は CLAIMS.md の分類を持つ。

```json
{
  "value": 0.123,
  "status": "CALCULATION|UNKNOWN",
  "unit": "ratio|x|JPY|null",
  "classification": "own|proxy|official",
  "formula_id": "operating_margin_v1",
  "source_fields": ["revenue", "operating_income"],
  "source_periods": ["current"],
  "raw_hash_normalized": "sha256...",
  "raw_hash_compressed": "sha256...",
  "note": null
}
```

ルール:
- **スケール統一**: 率・マージン・成長率・ROE等はすべて decimal ratio で格納する。
  例: 12.3% は `value=0.123`, `unit="ratio"`。表示層が必要なら `%` 表示に変換する。
  `value=12.3` / `value=8.0` と `unit="%"` は禁止。percentage point / bps は別 unit を定義するまで使わない。
- 欠損 / nan / inf / 非数値 / 分母0 は `status=UNKNOWN`, `value=null`。
- UNKNOWN を 0 / false にしない。
- `classification=official` は provider の直接値だけ。自前計算は `own`、近似は `proxy`。
- Phase C minimal は provider の analysis score / AI所見を feature にしない。

## 6. feature registry v1
公式API docs上、financials は年度別財務時系列データで、PL/BS/CFと1株指標を含む。
ただし実 raw field 名は provider 変更余地があるため、実装は宣言的 alias registry を持つ。
alias が複数一致し矛盾する場合は UNKNOWN。

| id | classification | unit | formula | 必須入力 | UNKNOWN条件 |
|---|---|---:|---|---|---|
| revenue_growth_yoy | own | ratio | `(revenue_t / revenue_t-1) - 1` | current revenue, previous revenue | 前期なし / 分母<=0 / 非数値 |
| operating_margin | own | ratio | `operating_income / revenue` | revenue, operating_income | revenue<=0 / 欠損 |
| net_margin | own | ratio | `net_income / revenue` | revenue, net_income | revenue<=0 / 欠損 |
| roe_proxy | proxy | ratio | `net_income / average_equity` | net_income, equity_t, equity_t-1 | 前期 equity なし / average_equity<=0 |
| roic_proxy | UNKNOWN | null | `UNKNOWN until invested_capital_proxy and tax assumptions are configured` | none | Phase C minimal では常に `status=UNKNOWN`, `value=null` |
| fcf_proxy | proxy | JPY | `operating_cash_flow - capex_abs` | operating_cash_flow, capex | 欠損 |
| net_cash | own | JPY | `cash_and_equivalents - interest_bearing_debt` | cash, debt | 欠損 |
| equity_ratio | own | ratio | `equity / total_assets` | equity, total_assets | total_assets<=0 / 欠損 |
| valuation_status | UNKNOWN | null | `UNKNOWN until prices/market_cap dataset` | none | Phase C minimal では常に UNKNOWN |

`roic_proxy` は Phase C minimal では `valuation_status` と同様に UNKNOWN 固定。
将来出す場合は `invested_capital_proxy` の式と `tax_rate` assumption を config 化し、ASSUMPTION依存を明示する。
`valuation_status` は将来も「割安」verdict を持たない。価格/時価総額 dataset が入っても、別SPECで定義するまでは UNKNOWN。

## 7. alias registry の初期方針
実装時に `radar/features/registry.py` 等で宣言する。

```text
revenue: revenue, net_sales, sales
operating_income: operating_income, operating_profit
net_income: net_income, profit_attributable_to_owners_of_parent
equity: net_assets, equity, total_equity
total_assets: total_assets, assets
operating_cash_flow: operating_cash_flow, cash_flows_from_operating_activities
capex: capital_expenditure, purchase_of_property_plant_and_equipment, capex
cash: cash_and_deposits, cash_and_cash_equivalents
interest_bearing_debt: interest_bearing_debt, borrowings, bonds_payable
```

これは実装上の候補であり、rawに存在しない alias は UNKNOWN。provider field を勝手に推測して FACT化しない。

## 8. PIT / 改訂 / restatement
- sidecar provenance の `available_at` を採用時点とする。
- raw内に `submit_date` / `disclosure_date` があれば `available_at` の説明に使うが、採否は sidecar が正。
- raw path に含まれる `<asof>` 日付は保存場所のラベルであり、PIT採否には使わない。
- restatement flag が rawにある場合、derived に `restatement_flags` として保持する。
- restated / revised の扱いは「正しい過去値」ではなく「取得時点の vendor raw」。後知恵混入の疑いがある場合は warning。
- `asof` 比較は sync と同じく JST 当日末。`available_at` が timezone 無しなら停止。
- years=1 の raw では前期が無いため、`revenue_growth_yoy` / `roe_proxy` は UNKNOWN になり得る。これは正常な「正直なUNKNOWN」であり失敗ではない。

## 9. 書込・安全
- 書込は `data/derived/features/edinet_financials_v1/...` のみ。
- `data/raw` は読むだけ。
- `outputs/`, `journal/`, `data/cache` には書かない。
- ネットワーク禁止。`urllib` / `requests` / `socket` を feature層に import しない。
- APIキーを読まない。`.env` を読まない。

## 10. テスト必須
- pure feature計算: 正常、欠損、nan、inf、非数値、分母0、前期なし。
- alias解決: 一致なし UNKNOWN、複数候補矛盾 UNKNOWN。
- PIT: sidecar available_at > asof で停止、derivedを書かない。
- hash: `raw_hash_compressed` と `raw_hash_normalized` の両方を再計算し、sidecar と一致しなければ停止。
- feature metadata: 各 feature も `raw_hash_normalized` と `raw_hash_compressed` を持つ。
- scope: raw_path traversal拒否、derived path traversal拒否。
- edinet_code: `^E\d{5}$` 以外は output path 構築前に拒否。
- restatement_flags: rawに改訂/訂正を示す field がある場合、derived に保持する。
- determinism: 同一 raw + sidecar + config + code_commit で同一 derived。
- no-network: feature層にネットワーク import なし。
- no-advice: 出力に buy_candidate / recommendation / expected_return / ranking を含めない。
- non-regression: mirror/check/log/score/review/target-check/value-audit/data-check/sync の CLI不変。

## 11. 完了条件
Phase C minimal 完了は以下すべて:
- `python3 -m radar build-features ...` が EDINET DB financials raw 1件から derived 1件を作る。
- raw本文・APIキーを表示しない。
- derived に source_snapshot / raw_hash / feature_registry_version / config_hash / code_commit が入る。
- UNKNOWN が 0扱いされない。
- research_queue / evidence / LLM投入に進んでいない。
