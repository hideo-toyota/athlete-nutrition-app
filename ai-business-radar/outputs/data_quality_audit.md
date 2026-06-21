# Data Quality Audit — EDINET×J-Quants 整合 / valuation coverage

_asof: 2026-06-20 / これは整合性の点検であり、売買順・推奨・予測ではありません_

> これは調査用の整理であり、投資助言・売買指示・利益保証・将来予測ではありません。売買を考える場合も discipline check と人間判断が必要です。

## A. EDINET vs J-Quants cross-check 集計 [CALCULATION/UNKNOWN]
- research items: 800 / cross-checked: 780

| metric | checked | mismatch | period_mismatch | mismatch率 | tolerance | median|Δ| | p90|Δ| | max|Δ| | 校正信号 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| equity_ratio↔equity_ratio | 321 | 12 | 459 | 3.7% | 3.00pt | 0.00pt | 0.93pt | 23.67pt | `ok` |
| net_margin↔net_margin | 321 | 0 | 459 | 0.0% | 2.00pt | 0.00pt | 0.01pt | 0.22pt | `ok` |
| operating_margin↔operating_margin | 315 | 1 | 455 | 0.3% | 2.00pt | 0.00pt | 0.01pt | 2.64pt | `ok` |
| revenue_growth_yoy↔sales_growth_yoy | 321 | 11 | 459 | 3.4% | 2.00pt | 0.00pt | 0.01pt | 39.79pt | `outlier_review` |
| roe_proxy↔roe_proxy | 321 | 2 | 459 | 0.6% | 3.00pt | 0.00pt | 0.18pt | 5.85pt | `ok` |

- mismatch率が高い指標は、tolerance が厳しすぎるか、片側のデータ品質/定義差を示す(要点検)。
- median|Δ| が tolerance に近い指標は、tolerance 見直しの候補。
- p90|Δ| が tolerance を大きく超え、median|Δ| が小さい場合は、全体調整より外れ値/期間差/定義差を優先点検。
- period_mismatch は EDINET と J-Quants の対象FYが違うため、mismatch率の分母から除外。
- 校正信号は自動判定ではなく、次に見るべきデータ品質タスクのラベル。

### mismatch 明細(絶対差が大きい順・各指標最大5件)
| metric | edinet_code | sec_code | EDINET | J-Quants | delta |
|---|---|---|---:|---:|---:|
| equity_ratio↔equity_ratio | E00919 | 45020 | 24.2% | 47.9% | 23.67pt |
| equity_ratio↔equity_ratio | E01480 | 61010 | 52.0% | 69.1% | 17.12pt |
| equity_ratio↔equity_ratio | E00932 | 45190 | 73.7% | 82.1% | 8.39pt |
| equity_ratio↔equity_ratio | E01122 | 52010 | 50.3% | 58.7% | 8.36pt |
| equity_ratio↔equity_ratio | E01593 | 72590 | 48.8% | 55.3% | 6.55pt |
| operating_margin↔operating_margin | E01602 | 64730 | 3.9% | 1.3% | -2.64pt |
| revenue_growth_yoy↔sales_growth_yoy | E01678 | 64810 | 7.9% | -31.8% | -39.79pt |
| revenue_growth_yoy↔sales_growth_yoy | E02100 | 66620 | 21.6% | 0.0% | -21.60pt |
| revenue_growth_yoy↔sales_growth_yoy | E01726 | 62680 | 9.8% | -4.8% | -14.57pt |
| revenue_growth_yoy↔sales_growth_yoy | E01902 | 69990 | 12.7% | 0.0% | -12.74pt |
| revenue_growth_yoy↔sales_growth_yoy | E01975 | 65940 | 11.1% | 0.0% | -11.08pt |
| roe_proxy↔roe_proxy | E01480 | 61010 | 23.4% | 17.6% | -5.85pt |
| roe_proxy↔roe_proxy | E02100 | 66620 | -28.0% | -32.5% | -4.51pt |

## B. J-Quants valuation coverage [CALCULATION/UNKNOWN]
- feature_set/asof: `jquants_equity_v1` / `2026-06-20`
- listed_codes: 4443 / valuation_covered: 3741
- valuation_coverage: 84.2% / price_coverage: 97.7%
- per_coverage: 75.0% / pbr_coverage: 84.0%
- alias_hits: `{"bps": {"BPS": 3751}, "eps": {"EPS": 3755}, "pbr_method": {"bps:BPS": 3733}, "per_method": {"eps:EPS": 3334}, "shares": {}}`
- uncovered_reasons: `{"no_per_pbr_inputs": 584, "no_price": 104, "nonpositive_or_unusable_inputs": 14}`
- per_uncovered_reasons: `{"no_per_inputs": 584, "no_price": 104, "nonpositive_or_unusable_inputs": 421}`
- pbr_uncovered_reasons: `{"no_pbr_inputs": 588, "no_price": 104, "nonpositive_or_unusable_inputs": 18}`

- uncovered の `no_per_pbr_inputs` が多い場合、EPS/BPS 列エイリアスが実 raw と不一致の可能性(要列名確認)。
- PER/PBR 個別の未カバーは `per_uncovered_reasons` / `pbr_uncovered_reasons` を優先して確認。
- `nonpositive_or_unusable_inputs` は赤字/債務超過など。算出不能で正しく UNKNOWN。
- `no_price` は価格欠損。価格 bulk の範囲/銘柄を確認。

## 注意
- per/pbr は trailing(予想PERではない)。本レポートは魅力度・売買順ではありません。
- 第三者LLM入力は LICENSE_MATRIX E5/J5 本人確認 2026-06-20 済(個人の私的分析利用)。
