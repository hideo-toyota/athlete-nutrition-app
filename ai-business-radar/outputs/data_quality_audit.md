# Data Quality Audit — EDINET×J-Quants 整合 / valuation coverage / relative price consistency

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
| metric | edinet_code | sec_code | EDINET FY | JQ FY | EDINET | J-Quants | delta | 推定原因/次点検 |
|---|---|---|---:|---:|---:|---:|---:|---|
| equity_ratio↔equity_ratio | E00492 | 29140 | 2025 | 2025 | 15.9% | 48.9% | 32.98pt | 自己資本/純資産定義・非支配株主持分・連結範囲を重点点検 |
| equity_ratio↔equity_ratio | E00436 | 28020 | 2026 | 2026 | 18.3% | 46.6% | 28.27pt | 自己資本/純資産定義・非支配株主持分・連結範囲を重点点検 |
| equity_ratio↔equity_ratio | E00919 | 45020 | 2026 | 2026 | 24.2% | 47.9% | 23.67pt | 自己資本/純資産定義・非支配株主持分・連結範囲を重点点検 |
| equity_ratio↔equity_ratio | E01480 | 61010 | 2026 | 2026 | 52.0% | 69.1% | 17.12pt | 自己資本/純資産定義・非支配株主持分・連結範囲を重点点検 |
| equity_ratio↔equity_ratio | E00395 | 25030 | 2025 | 2025 | 36.8% | 45.7% | 8.82pt | 自己資本/純資産定義・連結範囲を点検 |
| operating_margin↔operating_margin | E01602 | 64730 | 2026 | 2026 | 3.9% | 1.3% | -2.64pt | 営業利益定義・連結/単体・販管費/一過性項目を点検 |
| revenue_growth_yoy↔sales_growth_yoy | E01678 | 64810 | 2025 | 2025 | 7.9% | -31.8% | -39.79pt | 売上定義・決算期間・前年比分母の差を点検 |
| revenue_growth_yoy↔sales_growth_yoy | E00149 | 19690 | 2026 | 2026 | 11.1% | 0.0% | -11.07pt | J-Quants成長率0.0: 欠損補完/前年比分母/売上定義を点検 |
| revenue_growth_yoy↔sales_growth_yoy | E00605 | 81430 | 2026 | 2026 | -8.3% | 0.0% | 8.28pt | J-Quants成長率0.0: 欠損補完/前年比分母/売上定義を点検 |
| revenue_growth_yoy↔sales_growth_yoy | E01141 | 53370 | 2025 | 2025 | -7.5% | 0.0% | 7.53pt | J-Quants成長率0.0: 欠損補完/前年比分母/売上定義を点検 |
| revenue_growth_yoy↔sales_growth_yoy | E00263 | 17830 | 2025 | 2025 | 7.0% | 0.0% | -7.00pt | J-Quants成長率0.0: 欠損補完/前年比分母/売上定義を点検 |
| roe_proxy↔roe_proxy | E00748 | 78310 | 2025 | 2025 | -38.0% | -66.9% | -28.88pt | 平均自己資本 vs 期末自己資本・利益定義を点検 |
| roe_proxy↔roe_proxy | E00492 | 29140 | 2025 | 2025 | 40.0% | 12.8% | -27.15pt | 平均自己資本 vs 期末自己資本・利益定義を点検 |
| roe_proxy↔roe_proxy | E00436 | 28020 | 2026 | 2026 | 38.9% | 16.2% | -22.65pt | 平均自己資本 vs 期末自己資本・利益定義を点検 |
| roe_proxy↔roe_proxy | E01480 | 61010 | 2026 | 2026 | 23.4% | 17.6% | -5.85pt | 平均自己資本 vs 期末自己資本・利益定義を点検 |

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

## C. J-Quants relative price consistency [CALCULATION/UNKNOWN]
- 方向予測ではなく、同じ市場・業種内で価格リターンとPER/PBRの分布が同時に大きく外れていないかを見る監査です。
- 個別銘柄リストは出しません。市場区分・業種単位の分布だけを出し、調査順序や売買判断には使いません。
- status/asof: `CALCULATION` / `2026-06-22`
- common_equity_rows: 3910 / calculation_groups: 38

| group_type | group | status | n | PER cov | PBR cov | 20d cov | PER med | PBR med | 20d med | 20d p10/p90 | joint_deviation_count | note |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| all_common_equity | ALL | CALCULATION | 3910 | 83.8% | 94.3% | 95.3% | 13.96x | 1.22x | -0.8% | -11.5%/9.3% | 278 | `group_distribution_only` |
| market | TOKYO PRO MARKET | CALCULATION | 181 | 0.0% | 0.0% | 0.0% | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN/UNKNOWN | 0 | `group_distribution_only` |
| market | グロース | CALCULATION | 594 | 70.4% | 98.1% | 99.8% | 16.89x | 2.30x | -4.6% | -22.3%/8.0% | 50 | `group_distribution_only` |
| market | スタンダード | CALCULATION | 1572 | 87.1% | 99.1% | 100.0% | 11.92x | 0.90x | -1.1% | -10.5%/7.1% | 112 | `group_distribution_only` |
| market | プライム | CALCULATION | 1563 | 95.4% | 99.0% | 99.9% | 14.76x | 1.26x | 0.3% | -8.0%/11.3% | 121 | `group_distribution_only` |
| sector33 | その他製品 | CALCULATION | 105 | 86.7% | 100.0% | 100.0% | 12.95x | 0.82x | -0.6% | -9.3%/7.2% | 7 | `group_distribution_only` |
| sector33 | その他金融業 | CALCULATION | 42 | 85.7% | 90.5% | 92.9% | 12.26x | 1.06x | -1.5% | -9.4%/3.0% | 4 | `group_distribution_only` |
| sector33 | ガラス･土石製品 | CALCULATION | 50 | 90.0% | 98.0% | 98.0% | 14.22x | 0.97x | 1.3% | -9.8%/23.9% | 5 | `group_distribution_only` |
| sector33 | ゴム製品 | CALCULATION | 17 | 94.1% | 100.0% | 100.0% | 12.57x | 0.98x | 1.4% | -4.3%/10.3% | 2 | `group_distribution_only` |
| sector33 | サービス業 | CALCULATION | 579 | 79.3% | 91.5% | 92.2% | 14.46x | 1.60x | -1.1% | -12.5%/7.6% | 48 | `group_distribution_only` |
| sector33 | パルプ・紙 | CALCULATION | 25 | 96.0% | 96.0% | 96.0% | 11.54x | 0.54x | -1.5% | -7.8%/5.7% | 4 | `group_distribution_only` |
| sector33 | 不動産業 | CALCULATION | 158 | 75.9% | 82.3% | 82.9% | 10.07x | 1.17x | -0.6% | -8.5%/5.0% | 12 | `group_distribution_only` |
| sector33 | 保険業 | CALCULATION | 16 | 81.2% | 87.5% | 87.5% | 16.40x | 1.48x | -1.8% | -9.9%/14.1% | 2 | `group_distribution_only` |
| sector33 | 倉庫･運輸関連業 | CALCULATION | 31 | 96.8% | 100.0% | 100.0% | 11.29x | 0.70x | -0.3% | -8.6%/4.1% | 3 | `group_distribution_only` |
| sector33 | 化学 | CALCULATION | 203 | 94.1% | 100.0% | 100.0% | 14.52x | 0.93x | 1.2% | -7.8%/14.0% | 18 | `group_distribution_only` |
| sector33 | 医薬品 | CALCULATION | 81 | 48.1% | 96.3% | 98.8% | 17.81x | 1.77x | -9.4% | -24.5%/-0.1% | 3 | `group_distribution_only` |
| sector33 | 卸売業 | CALCULATION | 302 | 89.7% | 94.0% | 94.4% | 12.12x | 0.89x | -0.5% | -8.1%/7.1% | 21 | `group_distribution_only` |
| sector33 | 小売業 | CALCULATION | 346 | 80.9% | 94.2% | 94.8% | 15.98x | 1.58x | -0.6% | -8.5%/6.8% | 23 | `group_distribution_only` |
| sector33 | 建設業 | CALCULATION | 154 | 87.0% | 89.0% | 91.6% | 11.84x | 1.12x | 0.1% | -6.5%/8.0% | 12 | `group_distribution_only` |
| sector33 | 情報･通信業 | CALCULATION | 643 | 77.3% | 92.1% | 94.1% | 14.72x | 1.98x | -4.1% | -18.0%/5.7% | 44 | `group_distribution_only` |
| sector33 | 機械 | CALCULATION | 212 | 90.6% | 98.1% | 98.6% | 15.75x | 1.01x | 2.7% | -6.7%/18.7% | 21 | `group_distribution_only` |
| sector33 | 水産・農林業 | CALCULATION | 12 | 100.0% | 100.0% | 100.0% | 13.71x | 1.06x | -0.0% | -5.1%/1.7% | 2 | `group_distribution_only` |
| sector33 | 海運業 | CALCULATION | 11 | 90.9% | 90.9% | 100.0% | 9.04x | 0.66x | -4.4% | -11.5%/0.8% | 1 | `group_distribution_only` |
| sector33 | 石油･石炭製品 | CALCULATION | 10 | 80.0% | 90.0% | 90.0% | 10.13x | 0.80x | -2.9% | -9.7%/7.6% | 1 | `group_distribution_only` |
| sector33 | 空運業 | CALCULATION | 7 | 71.4% | 71.4% | 85.7% | 11.21x | 1.00x | 1.9% | -0.2%/8.2% | 1 | `group_distribution_only` |
| sector33 | 精密機器 | CALCULATION | 52 | 84.6% | 100.0% | 100.0% | 19.44x | 2.00x | -0.2% | -13.3%/13.2% | 4 | `group_distribution_only` |
| sector33 | 繊維製品 | CALCULATION | 48 | 85.4% | 100.0% | 100.0% | 13.26x | 0.77x | -0.2% | -14.1%/7.9% | 2 | `group_distribution_only` |
| sector33 | 証券･商品先物取引業 | CALCULATION | 38 | 86.8% | 97.4% | 97.4% | 11.16x | 1.06x | -0.1% | -8.4%/7.4% | 1 | `group_distribution_only` |
| sector33 | 輸送用機器 | CALCULATION | 82 | 89.0% | 97.6% | 100.0% | 10.71x | 0.70x | -1.4% | -11.5%/5.5% | 8 | `group_distribution_only` |
| sector33 | 金属製品 | CALCULATION | 89 | 84.3% | 96.6% | 97.8% | 12.48x | 0.60x | 0.7% | -5.1%/11.4% | 7 | `group_distribution_only` |
| sector33 | 鉄鋼 | CALCULATION | 38 | 94.7% | 100.0% | 100.0% | 14.28x | 0.69x | 0.5% | -5.2%/8.5% | 2 | `group_distribution_only` |
| sector33 | 鉱業 | CALCULATION | 5 | 100.0% | 100.0% | 100.0% | 12.39x | 0.99x | -7.7% | -11.2%/2.7% | 2 | `group_distribution_only` |
| sector33 | 銀行業 | CALCULATION | 80 | 97.5% | 98.8% | 100.0% | 14.70x | 0.87x | -0.1% | -4.1%/8.3% | 8 | `group_distribution_only` |
| sector33 | 陸運業 | CALCULATION | 60 | 93.3% | 93.3% | 93.3% | 11.74x | 0.94x | -1.5% | -8.5%/3.8% | 8 | `group_distribution_only` |
| sector33 | 電気機器 | CALCULATION | 228 | 84.2% | 97.8% | 98.2% | 18.29x | 1.36x | -0.7% | -11.5%/23.2% | 22 | `group_distribution_only` |
| sector33 | 電気･ガス業 | CALCULATION | 28 | 96.4% | 100.0% | 100.0% | 9.48x | 0.64x | -2.8% | -20.6%/2.4% | 5 | `group_distribution_only` |
| sector33 | 非鉄金属 | CALCULATION | 32 | 93.8% | 100.0% | 100.0% | 13.54x | 1.16x | 0.0% | -13.5%/11.0% | 3 | `group_distribution_only` |
| sector33 | 食料品 | CALCULATION | 126 | 91.3% | 96.8% | 98.4% | 16.56x | 1.17x | 0.3% | -5.7%/8.7% | 12 | `group_distribution_only` |

- joint_deviation_count は、同一グループ内で20日リターンとPER/PBRの双方が10-90%帯の外に出た件数。
- 件数が多いグループは、ニュース・決算期ズレ・倍率計算の入力列・流動性を点検します。魅力度ではありません。

## 注意
- per/pbr は trailing(予想PERではない)。本レポートは魅力度・売買順ではありません。
- market_cap_jpy は latest_close×shares_outstanding のPIT proxy。投資判断の優先度ではありません。
- 第三者LLM入力は LICENSE_MATRIX E5/J5 本人確認 2026-06-20 済(個人の私的分析利用)。
