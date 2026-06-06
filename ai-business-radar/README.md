# Personal Equity Research Radar

自分用の「個別株 **上昇トレンド分析** + 投資リサーチ／売買判断ログ」ツール。

> ⚠️ **これは投資助言ツールではありません。絶対に勝てる投資法でもありません。**
> 目的は、余剰資金で個別株・ETF を**勉強しながら**、市場平均を上回れる可能性を検証し、
> 上昇トレンド・過熱・リスク・売買判断を**構造化**すること。出力の分類ラベルは整理用であり、
> **AI に売買を丸投げせず、最終判断と結果の責任は自分が持ちます。**

## 特徴

- **ローカル完結・外部ライブラリ不要**(Python 標準ライブラリのみ。pip インストール不要)。
- 株価は **ローカルCSV** で動作。**J-Quants API** は任意で上書き(キーが無くてもCSVで動く)。
- 証券会社連携・発注・リアルタイム株価取得は **しない**。手入力/手元データで完結。

## コマンド

```bash
cd ai-business-radar

python3 opportunity_radar.py trend            # ★メイン: 上昇トレンド分析
python3 opportunity_radar.py backtest-trend   # トレンド・シグナルの簡易バックテスト
python3 opportunity_radar.py equity           # 銘柄ごとの投資リサーチ・判断ログ
python3 opportunity_radar.py run              # 投資分析ワークフロー概要(補助)
```

### `trend` の出力
- `outputs/trend_report.md` … 銘柄ごとのトレンド判定・理由・反証・撤退条件・指標
- `outputs/trend_ranking.csv` … トレンドスコア順のランキング(表計算で並べ替え可)
- `outputs/trade_journal_prompts.md` … AI に深掘り/振り返りを頼むプロンプト集
- `outputs/obsidian/<ticker>.md` … Obsidian 用の銘柄メモ(下記テンプレート)

### `backtest-trend` の出力
- `outputs/trend_backtest_report.md` … 学習/検証(アウトオブサンプル)別の成績

## クイックスタート(オフラインで試す)

サンプル株価CSV(合成データ)が同梱されているので、そのまま動きます。

```bash
# (サンプルCSVを再生成したい場合のみ) python3 scripts/make_sample_prices.py
python3 opportunity_radar.py trend
python3 opportunity_radar.py backtest-trend
```

## データの用意

`inputs/equity_watchlist.json` の `data_source` で指定します。

```json
"data_source": {
  "type": "csv",                                  // csv または jquants
  "price_dir": "data/prices",                     // <ticker>.csv を探す場所
  "benchmark_file": "data/prices/BENCHMARK.csv",  // TOPIX等のベンチマーク
  "benchmark_name": "TOPIX"
}
```

- **CSV 形式**: ヘッダ `date,open,high,low,close,volume`(日付昇順でなくてもOK、内部でソート)。
  ファイル名は原則 `<ticker>.csv`。銘柄ごとに `"csv_file": "path/to.csv"` で個別指定も可。
- **J-Quants を使う場合**: `data_source.type` を `"jquants"` にし、各銘柄に `"jquants_code": "7203"` を設定。
  認証情報は `.env`(`.env.example` 参照)か環境変数から読みます。**取得に失敗したら自動でCSVにフォールバック**します。

```bash
cp .env.example .env   # JQUANTS_API_KEY 等を記入(コードに直書きしない)
```

## 上昇トレンド判定(計算する指標)

各銘柄について、20/60/120日移動平均とその傾き、終値の各線との上下、20日/60日高値・年初来高値からの距離、
20/60/120日リターン、ベンチマーク相対リターン、出来高20日平均比、売買代金20日平均、ATR/値幅率、
最大ドローダウン、決算跨ぎリスク、ストップ高/安(代理)を算出します。

### トレンドスコア(0〜100)
**加点**: 終値が20/60/120日線の上 / 20>60>120日線の並び / 20・60日線が上向き / 60日リターンがプラス /
ベンチ比で強い / 出来高を伴って上昇 / 流動性が十分 / 高値圏を維持。
**減点**: 20日線から過熱乖離 / 出来高が細い / 急騰直後で押し目なし / 決算直前 /
最大DDが大きい / ベンチより弱い / 下落日に大きく崩れる。

### 判断ラベル
`強い上昇トレンド` / `上昇トレンド候補` / `押し目監視` / `過熱注意` / `レンジ` / `下落トレンド`

各銘柄レポートには必ず以下を含めます:
**なぜ上昇トレンドと判定したか / 反証条件(崩れたら否定)/ 買うならどの条件を待つか /
買わない理由 / 損切り・撤退条件 / 決算前後の注意点 / 市場平均と比べて本当に強いか**。
銘柄に `"material_or_pts": true` を付けると、**熱量(短期の出来高・急騰)と継続トレンド(MA構造)を分けて**評価します。

## バックテスト(`backtest-trend`)

- シグナル発生日の**翌営業日**にエントリー(`entry`: `next_open`/`next_close`)。**未来データは使いません**。
- 決済: 損切り / 利確 / 最大保有日数 / トレンドスコア低下。**手数料+スリッページ**を往復控除。
- **学習期間(in-sample)と検証期間(out-of-sample)に分割**して集計(`backtest.train_end`)。
- 出力: 勝率・平均利益・平均損失・累積リターン・最大DD・**シャープ**・プロフィットファクタ・平均保有日数、
  および**ベンチマークのバイ&ホールド比較**。

```json
"backtest": {
  "entry_threshold": 70, "exit_threshold": 50, "entry": "next_open",
  "stop_loss_pct": 0.08, "take_profit_pct": 0.20, "hold_max_days": 40,
  "fee_rate": 0.001, "slippage_rate": 0.001, "train_end": "2025-08-01"
}
```

> 過去の結果は将来を保証しません。パラメータの過剰最適化(カーブフィット)に注意してください。

## 入力スキーマ(`inputs/equity_watchlist.json` の銘柄)

トレンド分析に使う主なフィールド:
`ticker` / `company_name` / `market` / `jquants_code`(任意)/ `csv_file`(任意)/
`next_earnings_date`(決算跨ぎ判定)/ `material_or_pts`(材料株フラグ)/ `current_price` /
`position_status`(none/holding/sold)。

リサーチ・判断ログ(`equity` でも使用):
`thesis` / `business_summary` / `latest_revenue_growth` / `latest_profit_growth` / `margin_trend` /
`valuation_notes` / `catalysts` / `risks` / `bear_case` / `reason_to_buy` / `reason_not_to_buy` /
`exit_conditions` / `source_notes` / `kpis_to_watch` / `position_sizing` / `self_scores` / `trade_log`。

トップレベルに `policy`(投入上限・最大損失許容・決算跨ぎ方針)、`data_source`、`trend_params`、`backtest`。

## Obsidian 銘柄メモのテンプレート(`outputs/obsidian/<ticker>.md`)

```markdown
# 銘柄名 / コード

## 今日の判断
- 判断 / 理由 / 上昇トレンドスコア / ベンチマーク比 / 出来高 / 過熱度

## 買う理由
## 買わない理由
## 反証条件
## 撤退条件
## 決算で確認すること
## 売買後の振り返り
- なぜ買ったか / なぜ売ったか / 結果 / 学び / 次回改善
```

## 設計上の原則

- AI の出力は「買え/売れ」と**断定しない**。判断ラベルは出発点で、推奨ではない。
- 余剰資金・勉強目的。**集中投資・信用取引・短期の煽り**を避ける注意文を常に表示。
- 1銘柄の投入上限・最大損失許容・決算跨ぎ方針を `policy`/`position_sizing` に記録。
- 「なぜ買ったか / なぜ売ったか / 結果 / 学び / 次回改善」を `trade_log` と Obsidian メモに残す。

## 動作確認

```bash
python3 -m py_compile opportunity_radar.py ohlcv_data.py trend_indicators.py trend_backtest.py
python3 opportunity_radar.py trend
python3 opportunity_radar.py backtest-trend
```

## ファイル構成

```
ai-business-radar/
├── opportunity_radar.py     # CLI(trend / backtest-trend / equity / run)
├── ohlcv_data.py            # OHLCV ローダ(CSV / J-Quants・stdlibのみ)
├── trend_indicators.py      # 指標・スコア・ラベル(未来データ不使用)
├── trend_backtest.py        # 簡易バックテスト
├── scripts/make_sample_prices.py  # 合成サンプル株価の生成(開発用)
├── inputs/
│   ├── equity_watchlist.json
│   └── opportunities.json
├── data/prices/             # 日足CSV(サンプル同梱)
└── outputs/                 # 生成物
```
