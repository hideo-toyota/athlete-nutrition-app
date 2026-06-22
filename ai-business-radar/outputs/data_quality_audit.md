# Data Quality Audit — EDINET×J-Quants 整合 / valuation coverage

_asof: 2026-06-22 / これは整合性の点検であり、売買順・推奨・予測ではありません_

> これは調査用の整理であり、投資助言・売買指示・利益保証・将来予測ではありません。売買を考える場合も discipline check と人間判断が必要です。

## A. EDINET vs J-Quants cross-check 集計 [CALCULATION/UNKNOWN]
- research items: 900 / cross-checked: 871

| metric | checked | mismatch | period_mismatch | mismatch率 | tolerance | median|Δ| | p90|Δ| | max|Δ| | 校正信号 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| equity_ratio↔equity_ratio | 367 | 17 | 504 | 4.6% | 3.00pt | 0.00pt | 0.55pt | 32.98pt | `outlier_review` |
| net_margin↔net_margin | 367 | 0 | 504 | 0.0% | 2.00pt | 0.00pt | 0.00pt | 0.22pt | `ok` |
| operating_margin↔operating_margin | 361 | 1 | 501 | 0.3% | 2.00pt | 0.00pt | 0.00pt | 2.64pt | `ok` |
| revenue_growth_yoy↔sales_growth_yoy | 366 | 12 | 504 | 3.3% | 2.00pt | 0.00pt | 0.01pt | 39.79pt | `outlier_review` |
| roe_proxy↔roe_proxy | 366 | 4 | 504 | 1.1% | 3.00pt | 0.00pt | 0.15pt | 28.88pt | `ok` |

- mismatch率が高い指標は、tolerance が厳しすぎるか、片側のデータ品質/定義差を示す(要点検)。
- median|Δ| が tolerance に近い指標は、tolerance 見直しの候補。
- p90|Δ| が tolerance を大きく超え、median|Δ| が小さい場合は、全体調整より外れ値/期間差/定義差を優先点検。
- period_mismatch は EDINET と J-Quants の対象FYが違うため、mismatch率の分母から除外。
- 校正信号は自動判定ではなく、次に見るべきデータ品質タスクのラベル。

### mismatch 原因分解(絶対差が大きい順・各指標最大5件)
| metric | edinet_code | sec_code | EDINET | J-Quants | delta | 推定原因/次点検 |
|---|---|---|---:|---:|---:|---|
| equity_ratio↔equity_ratio | E00492 | 29140 | 15.9% | 48.9% | 32.98pt | 自己資本/純資産定義・非支配株主持分・連結範囲を重点点検 |
| equity_ratio↔equity_ratio | E00436 | 28020 | 18.3% | 46.6% | 28.27pt | 自己資本/純資産定義・非支配株主持分・連結範囲を重点点検 |
| equity_ratio↔equity_ratio | E00919 | 45020 | 24.2% | 47.9% | 23.67pt | 自己資本/純資産定義・非支配株主持分・連結範囲を重点点検 |
| equity_ratio↔equity_ratio | E01480 | 61010 | 52.0% | 69.1% | 17.12pt | 自己資本/純資産定義・非支配株主持分・連結範囲を重点点検 |
| equity_ratio↔equity_ratio | E00395 | 25030 | 36.8% | 45.7% | 8.82pt | 自己資本/純資産定義・連結範囲を点検 |
| operating_margin↔operating_margin | E01602 | 64730 | 3.9% | 1.3% | -2.64pt | 営業利益定義・連結/単体・販管費/一過性項目を点検 |
| revenue_growth_yoy↔sales_growth_yoy | E01678 | 64810 | 7.9% | -31.8% | -39.79pt | 売上定義・決算期間・前年比分母の差を点検 |
| revenue_growth_yoy↔sales_growth_yoy | E00149 | 19690 | 11.1% | 0.0% | -11.07pt | J-Quants成長率0.0: 欠損補完/前年比分母/売上定義を点検 |
| revenue_growth_yoy↔sales_growth_yoy | E00605 | 81430 | -8.3% | 0.0% | 8.28pt | J-Quants成長率0.0: 欠損補完/前年比分母/売上定義を点検 |
| revenue_growth_yoy↔sales_growth_yoy | E01141 | 53370 | -7.5% | 0.0% | 7.53pt | J-Quants成長率0.0: 欠損補完/前年比分母/売上定義を点検 |
| revenue_growth_yoy↔sales_growth_yoy | E00263 | 17830 | 7.0% | 0.0% | -7.00pt | J-Quants成長率0.0: 欠損補完/前年比分母/売上定義を点検 |
| roe_proxy↔roe_proxy | E00748 | 78310 | -38.0% | -66.9% | -28.88pt | 平均自己資本 vs 期末自己資本・利益定義を点検 |
| roe_proxy↔roe_proxy | E00492 | 29140 | 40.0% | 12.8% | -27.15pt | 平均自己資本 vs 期末自己資本・利益定義を点検 |
| roe_proxy↔roe_proxy | E00436 | 28020 | 38.9% | 16.2% | -22.65pt | 平均自己資本 vs 期末自己資本・利益定義を点検 |
| roe_proxy↔roe_proxy | E01480 | 61010 | 23.4% | 17.6% | -5.85pt | 平均自己資本 vs 期末自己資本・利益定義を点検 |

## B. J-Quants valuation coverage [CALCULATION/UNKNOWN]
- feature_set/asof: `jquants_equity_v1` / `2026-06-22`
- listed_codes: 4443 / valuation_covered: 3748
- valuation_coverage: 84.4% / price_coverage: 97.7%
- market_cap_coverage: 84.5% / market_cap_covered: 3753
- per_coverage: 75.1% / pbr_coverage: 84.3%
- alias_hits: `{"bps": {"BPS": 3751}, "eps": {"EPS": 3755}, "pbr_method": {"bps:BPS": 3733, "shares_equity:ShOutFY": 13}, "per_method": {"eps:EPS": 3334, "shares_net_profit:ShOutFY": 1}, "shares": {"ShOutFY": 3753}}`
- uncovered_reasons: `{"no_per_pbr_inputs": 584, "no_price": 104, "nonpositive_or_unusable_inputs": 7}`
- per_uncovered_reasons: `{"no_per_inputs": 584, "no_price": 104, "nonpositive_or_unusable_inputs": 420}`
- pbr_uncovered_reasons: `{"no_pbr_inputs": 586, "no_price": 104, "nonpositive_or_unusable_inputs": 7}`

- uncovered の `no_per_pbr_inputs` が多い場合、EPS/BPS 列エイリアスが実 raw と不一致の可能性(要列名確認)。
- PER/PBR 個別の未カバーは `per_uncovered_reasons` / `pbr_uncovered_reasons` を優先して確認。
- `nonpositive_or_unusable_inputs` は赤字/債務超過など。算出不能で正しく UNKNOWN。
- `no_price` は価格欠損。価格 bulk の範囲/銘柄を確認。

## 注意
- per/pbr は trailing(予想PERではない)。本レポートは魅力度・売買順ではありません。
- market_cap_jpy は latest_close×shares_outstanding のPIT proxy。投資判断の優先度ではありません。
- 第三者LLM入力は LICENSE_MATRIX E5/J5 本人確認 2026-06-20 済(個人の私的分析利用)。
