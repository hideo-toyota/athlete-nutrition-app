# BT-1 SPEC 裁定書(20差分の最終決定・2026-07-02)

対象: equity-radar-live 側 `BACKTEST_PHASE_BT1_SPEC.md` と
原本 `radar-ops/CLAUDE_HANDOFF_swing_analytics_roadmap.md`(v2) の差分20項目。
裁定: **原本17 / 草案1 / ハイブリッド2**。SPEC を本裁定どおり更新してから実装に進むこと。

| # | 項目 | 裁定 | 内容 |
|---|---|---|---|
| 1 | 入力データ | **原本** | raw日足(`bulk/equities/bars/daily/premium`)+`fins/summary` DiscDate を直接使用。derivedスナップショットは時系列バックテストの入力にしない |
| 2 | setup registry | **原本** | `radar/backtest/setups.py` にコードで3 setup固定。汎用JSON specはBT-2以降(自由度の温床のため) |
| 3 | 計測単位 | **原本** | 全指標R建て(期待値R/平均勝ちR/負けR/最大DD(R))。損益率/CAGRは補助表示まで |
| 4 | 参加率 | **原本** | 想定売買代金 ≤ 平均売買代金の **1%**(5%は結果を甘く見せる) |
| 5 | 地合い具体式 | **原本** | risk_on: positive_rate_20d>0.6 かつ 20日median>0 / risk_off: <0.4 かつ <0 / ボラ急上昇: 20日σが60日σ比1.5倍超 |
| 6 | フィルター多重比較 | **原本** | フィルター有/無=各1試行として attempts_log 記録。両系統を train で計測 |
| 7 | 決算跨ぎ窓 | **原本** | **3営業日前〜翌1営業日** entry禁止・保有中は前営業日終値で event exit。5日/2日案は別 backtest_id のバリアントとしてなら可(基準の事後変更は禁止) |
| 8 | exit schema | **原本** | enum: time/stop/trailing/event/thesis_broken/manual。BT-1実装は time/stop/event のみ。上場廃止・売買停止は新enumでなく「イベント無効(除外)」で処理 |
| 9 | 損失制御値 | **原本** | risk 1%/trade・同時2件・資金100万・日次-2R/月間-5R/累積-10R。**紙上トライアルと同一値であることが必須**(実運用の予行にならないため) |
| 10 | train/test | **原本** | train=〜2025-06 / test=2025-07〜。CLI公開は `--period train|test` のみ(--from/--to は内部実装可・公開しない)。test は backtest_id ごとに1回 |
| 11 | attempts_log | **ハイブリッド** | 正= **実験単位**(setup×パラメータ×フィルター有無、append-only)。草案の銘柄×日次ログは内部デバッグ用に併存可(gitignore) |
| 12 | コスト | **草案採用** | 片側 手数料5bps+スリッページ10bps(往復0.3%)。原本0.2%より保守的なため。**今固定し、以後調整禁止** |
| 13 | サンプル下限 | **両方** | 全体イベント<50=sample_too_small(原本) かつ バケットセル<20=UNKNOWN |
| 14 | バケット閾値 | **原本** | 小型<500億/大型>3000億・PER/PBR3分位・20日リターン分位・決算後5営業日・出来高急増有無 |
| 15 | クロス分解 | **原本** | 1軸ずつ。全軸クロス禁止を明記 |
| 16 | 出力名 | **原本** | `outputs/backtests/<backtest_id>_<train|test>.md/json`。run_id は manifest内フィールドに格納 |
| 17 | 銘柄リスト | **ハイブリッド** | trades.csv/signals.jsonl(実コード入り)は**監査用の内部成果物として許可**。ただし **gitignore・レポート.md非掲載・Discord/LLM非投入**。公開レポートは setup統計+匿名化例示のみ |
| 18 | CLI | **原本** | `python3 -m radar backtest --setup <name> --period train|test [--dry-run]`(既存CLI流儀と統一) |
| 19 | DoD | **原本** | 3 setup × フィルター有無2系統の train 結果+attempts_log。test は人間承認後 backtest_id ごと1回 |
| 20 | ガード | **原本** | FORBIDDEN_OUTPUT_TOKENS を全出力に適用・canonical root guard 対象化(実装ガード名で明記) |

## 裁定の原理(なぜ原本寄りか)
- 数字の優劣ではなく、**事前登録の不変性**(#7/#10)と**紙上トライアルとの同一性**(#9)が本体。
- 唯一 #12 で草案を採ったのは「**より保守的な仮定は常に採用してよい**」という非対称ルールによる。
- #17 は「監査可能性」と「銘柄リスト非公開」の両立: 内部ログ=可(ローカル・gitignore)、公開出力=統計のみ。

## 次アクション(equity-radar-live 側)
1. 本裁定どおり BACKTEST_PHASE_BT1_SPEC.md を更新(裁定番号を SPEC 内に引用)
2. 更新後の SPEC を人間に提示して承認を得る
3. 承認後に実装(テスト要件は roadmap v2 のとおり)
