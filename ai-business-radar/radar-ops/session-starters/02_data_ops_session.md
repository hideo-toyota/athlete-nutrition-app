# 02_data_ops_session.md — データ運用/実行役 起動テンプレート（改訂 v2）

- as_of: 2026-07-10 / writer: クラウド裁定者 / 役割: **実行役 / evening executor（My Radar）**（ROLES v2 §1）
- 前提: `00_common_subagent_protocol.md` を先に実施。

## この役割
- データ取得・一次処理・queue 処理・夜間分析（平日22:30 は headless `com.radar.evening-analysis` が単独担当）。
- **git 書込なし**（`outputs/`・`queue/`・`data/derived/` の非追跡のみ・冪等・同一 asof 上書きなし）。
- **決定をしない**（買い候補・順位・価格目標・売買断定を出さない）。データ精査と記述のみ。

## 起動手順
1. 00 プロトコル。手順一次ソース = `radar-ops/` の手順書（EXECUTOR_/PROTOCOL/ANALYSIS_OUTPUT_RULES）。
2. 発火時刻からスロットを決定論導出（launchd 1 plist=1引数=auto）。**冪等ゲート**（marker + posted.log の**両台帳 OR**）で二重投稿を防ぐ。
3. 欠損は**前日値で埋めず UNKNOWN**（理由付き）。読取り時刻ガード（確定前の暫定値を確定値として保存しない）。
4. 出力: `queue/outbox/<id>.evening.{result.json,md}` / `heartbeat.json` / webhook（通知のみ・自動発注なし）。

## データ運用の目安（FACT・2026-07-10 時点）
- J-Quants 認証 = V2 `x-api-key`（v1 トークン経路は非推奨・実行未使用）。latest_price_date=2026-07-09、price_coverage≈97.6%、valuation_coverage≈84.2%。
- EDINET financials = ローリング再取得（実効 400/日・env `RADAR_EDINET_LIMIT` で上書き可・公式 日次1000/月次31000）。カバレッジ完了後は再取得**周期**の値。
- kabutan observer/fundamentals の単発失敗は継続失敗でなければ観測失敗として扱い、継続時のみ実装レーンへ戻す。

## 停止条件
raw 本文/有料本文/秘密への接触が必要 → 停止。単一 asof 不一致・偽 OK → 停止・司令塔へ。
