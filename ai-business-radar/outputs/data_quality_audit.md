# Data Quality Audit — EDINET×J-Quants 整合 / valuation coverage

_asof: 2026-06-20 / これは整合性の点検であり、売買順・推奨・予測ではありません_

> これは調査用の整理であり、投資助言・売買指示・利益保証・将来予測ではありません。売買を考える場合も discipline check と人間判断が必要です。

## A. EDINET vs J-Quants cross-check 集計 [CALCULATION/UNKNOWN]
- research items: 790 / cross-checked: 770

| metric | checked | mismatch | mismatch率 | tolerance | median|Δ| | max|Δ| |
|---|---:|---:|---:|---:|---:|---:|
| equity_ratio↔equity_ratio | 770 | 217 | 28.2% | 3.00pt | 1.07pt | 43.36pt |
| net_margin↔net_margin | 770 | 198 | 25.7% | 2.00pt | 0.41pt | 160.26pt |
| operating_margin↔operating_margin | 761 | 159 | 20.9% | 2.00pt | 0.41pt | 49.73pt |
| revenue_growth_yoy↔sales_growth_yoy | 770 | 374 | 48.6% | 2.00pt | 1.79pt | 414.28pt |
| roe_proxy↔roe_proxy | 770 | 184 | 23.9% | 3.00pt | 0.64pt | 134.11pt |

- mismatch率が高い指標は、tolerance が厳しすぎるか、片側のデータ品質/定義差を示す(要点検)。
- median|Δ| が tolerance に近い指標は、tolerance 見直しの候補。

### mismatch 明細(絶対差が大きい順・各指標最大5件)
| metric | edinet_code | sec_code | EDINET | J-Quants | delta |
|---|---|---|---:|---:|---:|
| equity_ratio↔equity_ratio | E01891 | 69930 | 15.8% | 59.2% | 43.36pt |
| equity_ratio↔equity_ratio | E02057 | 67860 | 71.3% | 45.7% | -25.63pt |
| equity_ratio↔equity_ratio | E00919 | 45020 | 24.2% | 47.9% | 23.67pt |
| equity_ratio↔equity_ratio | E01480 | 61010 | 52.0% | 69.1% | 17.12pt |
| equity_ratio↔equity_ratio | E01474 | 60160 | 42.1% | 57.5% | 15.43pt |
| net_margin↔net_margin | E01300 | 57210 | -15.2% | -175.5% | -160.26pt |
| net_margin↔net_margin | E02070 | 67360 | 159.0% | 97.5% | -61.44pt |
| net_margin↔net_margin | E01790 | 67070 | 41.9% | -12.2% | -54.10pt |
| net_margin↔net_margin | E01875 | 66590 | -20.1% | -62.2% | -42.07pt |
| net_margin↔net_margin | E01727 | 64330 | -9.1% | -43.9% | -34.82pt |
| operating_margin↔operating_margin | E02046 | 78590 | 14.9% | -34.8% | -49.73pt |
| operating_margin↔operating_margin | E01300 | 57210 | -46.0% | -10.1% | 35.91pt |
| operating_margin↔operating_margin | E00935 | 45210 | 22.4% | -1.2% | -23.54pt |
| operating_margin↔operating_margin | E00973 | 45520 | -20.1% | 1.4% | 21.48pt |
| operating_margin↔operating_margin | E01875 | 66590 | -18.7% | -37.5% | -18.78pt |
| revenue_growth_yoy↔sales_growth_yoy | E00839 | 42220 | 7.8% | 422.1% | 414.28pt |
| revenue_growth_yoy↔sales_growth_yoy | E01300 | 57210 | -58.9% | 127.3% | 186.21pt |
| revenue_growth_yoy↔sales_growth_yoy | E01648 | 64940 | -2.1% | 76.9% | 79.03pt |
| revenue_growth_yoy↔sales_growth_yoy | E01081 | 50160 | -52.7% | 23.7% | 76.46pt |
| revenue_growth_yoy↔sales_growth_yoy | E01815 | 68040 | 13.1% | 81.1% | 67.97pt |
| roe_proxy↔roe_proxy | E00839 | 42220 | -2.5% | 131.6% | 134.11pt |
| roe_proxy↔roe_proxy | E00867 | 78860 | -22.8% | -145.3% | -122.58pt |
| roe_proxy↔roe_proxy | E01300 | 57210 | -3.3% | -66.8% | -63.51pt |
| roe_proxy↔roe_proxy | E01308 | 57070 | -22.8% | 40.3% | 63.07pt |
| roe_proxy↔roe_proxy | E01891 | 69930 | -118.7% | -59.1% | 59.69pt |

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
