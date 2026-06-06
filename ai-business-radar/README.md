# Personal Equity Research Radar

自分用の「個別株・ETF 投資リサーチ／売買判断ログ」ツール。
(旧 "AI Business Radar" を、事業評価ツールから**個人の投資判断支援**へ作り替えたもの)

> ⚠️ **これは投資助言ツールではありません。** 公開サービス化・投資助言ビジネス化は目的ではありません。
> 出力の「買い候補 / 見送り / 売却検討 / 継続保有」は**自分用の整理ラベル**であり、
> 最終判断と結果の責任は自分にあります。過去の数値や記入例は実データではありません。

## 目的

- 余剰資金で個別株・ETF を**勉強しながら**、自分の売買判断を構造化する。
- AI に売買を丸投げせず、**決算・事業・バリュエーション・リスク・反証**を整理し、自分で最終判断する。
- 証券会社連携・発注・リアルタイム株価取得は**不要**。ローカル完結・**手入力データ**でよい。
- 外部 API / 外部ライブラリは使わない(Python 標準ライブラリのみ)。

## クイックスタート

```bash
cd ai-business-radar

# メイン: 投資分析レポート + AI 用プロンプト集を生成
python3 opportunity_radar.py equity

# 補助(任意): 投資分析ワークフローの概要を出力
python3 opportunity_radar.py run
```

生成物:
- `outputs/equity_research_report.md` … 銘柄ごとの投資リサーチ・判断ログ
- `outputs/equity_prompt_pack.md` … AI に深掘り/反証/決算チェック/振り返りを頼むプロンプト集
- `outputs/workflow_overview.md` … (run コマンド) ワークフロー概要

## 使い方の流れ

1. `inputs/equity_watchlist.json` に銘柄を追加(後述のスキーマ)。
2. `python3 opportunity_radar.py equity` を実行。
3. `outputs/equity_research_report.md` を読み、買う理由/買わない理由/反証条件を点検。
4. **自分で**最終判断する(レポートの分類は出発点)。
5. 売買したら `trade_log` に「なぜ・結果・学び」を追記し、次の決算で KPI を照合。

## 入力スキーマ (`inputs/equity_watchlist.json`)

トップレベルに自分ルールの `policy`、`watchlist` に銘柄配列。

### policy(運用ルール)
- `purpose` … 目的
- `max_position_per_name_jpy` … 1銘柄あたり投入上限(円)
- `max_loss_tolerance_per_name_pct` … 1銘柄あたり最大損失許容(%)
- `earnings_crossing_policy` … 決算跨ぎの方針
- `cautions` … 注意書き

### 1銘柄の項目
| フィールド | 内容 |
|---|---|
| `ticker` | ティッカー/銘柄コード |
| `company_name` | 銘柄名 |
| `market` | 市場 |
| `current_price` | 現在値(手入力) |
| `position_status` | `none` / `holding` / `sold` |
| `thesis` | 投資仮説(なぜ上がると考えるか) |
| `business_summary` | 事業概要 |
| `latest_revenue_growth` | 直近の売上成長 |
| `latest_profit_growth` | 直近の利益成長 |
| `margin_trend` | 利益率トレンド |
| `valuation_notes` | バリュエーション所見 |
| `catalysts` | 上昇カタリスト(配列)→ 期待シナリオに反映 |
| `risks` | 主なリスク(配列) |
| `bear_case` | 弱気シナリオ |
| `reason_to_buy` | 買う理由(配列/文字列) |
| `reason_not_to_buy` | 買わない理由(配列/文字列) |
| `exit_conditions` | 撤退条件(配列)→ 反証/撤退に反映 |
| `source_notes` | 出典メモ |
| `kpis_to_watch` | 決算で見る KPI(配列・任意) |
| `position_sizing` | `{ planned_amount_jpy, max_loss_jpy }`(任意) |
| `self_scores` | 採点軸ごとの自己評価 1-5(任意・後述) |
| `trade_log` | 売買記録の配列 `{ date, action, reason, result, lesson }` |

## 採点軸(10軸 × 5点 = 50点)

1. 事業理解のしやすさ
2. 売上・利益成長の確認しやすさ
3. 競争優位性
4. バリュエーションの納得感
5. 決算KPIの追跡可能性
6. 下落リスクの明確さ
7. 反証条件の明確さ
8. 自分の理解度
9. 余剰資金で試す妥当性
10. 売買後に学びが残るか

各軸は既定では**「自分のノートの充実度」**から 1-5 の目安を自動算出します
(内容の正しさは保証しません)。`self_scores` に 1-5 を入れるとその自己評価を優先します。

## 判断ラベルの決まり方

スコア(充実度)と `position_status` から、出発点としての分類を出します(推奨ではない):

| ポジション | 高スコア+反証定義済 | 中スコア | 低スコア |
|---|---|---|---|
| `none` | 買い候補 | 様子見(リサーチ継続) | 見送り |
| `holding` | 継続保有 | 継続保有(要監視) | 売却検討 |
| `sold` | 振り返り対象(学びを残す) | 〃 | 〃 |

> 判断理由・反証条件・撤退条件は**必ずセット**で出力されます。`bear_case` と
> `exit_conditions` が空だと「買い候補」には上がりにくい設計です。

## 設計上の原則

- AI の出力は「買え/売れ」と**断定しない**。事実と論点の整理に徹する。
- 余剰資金・勉強目的。**集中投資・信用取引・短期の煽り**を避ける注意文を常に表示。
- 1銘柄の投入上限・最大損失許容・決算跨ぎ方針を記録できる。
- 「なぜ買ったか / なぜ売ったか / 結果から何を学んだか」を `trade_log` に残す。

## 動作確認

```bash
python3 -m py_compile opportunity_radar.py   # 構文チェック
python3 opportunity_radar.py equity          # レポート生成
```
