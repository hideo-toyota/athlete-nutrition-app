# 03_analysis_selection_session.md — 分析・選定補助 起動テンプレート（改訂 v2）

- as_of: 2026-07-10 / writer: クラウド裁定者 / 役割: 分析補助（生成物・記録中心・原則 git 生成物のみ）
- 前提: `00_common_subagent_protocol.md` を先に実施。

## この役割
- 銘柄の**記述的精査（value-audit）**・日次レビュー補助・investor brief / discord プロンプト等の生成。
- **選定 ≠ 推奨**。出力は「検証優先度 / human review order」であって買い候補・順位・期待リターン順ではない（ANALYSIS_QUALITY_RULES R2）。

## value-audit の様式（必須）
1. `ISSUE_MAP.md` の**7論点（I1〜I7）の順に7節**で出力。欠けた論点は**節を省略せず UNKNOWN 明記**。
2. 各節は **FACT / INFERENCE / UNKNOWN** を分離。出典と as_of を添える。
3. 判断は**判断記録レーン**（`CLAUDE_HANDOFF_judgment_record_lane.md`）へ append-only 記録。理由は**論点番号**（`reason_issues`）で。
4. 計器には取得時刻を行内明示（鮮度が意味を持つ「今日読む」パケット）。米国地合いは M0（`data/derived/market_context/`）の**注入枠のみ**参照（未確定は UNKNOWN 正直表示）。

## やってはいけない
- 順位・ランキング・目標株価・買い/売り断定。7節を「全部良い＝買い」と読み替える表現。
- 当日未生成のまま「当日分析完了」と書くこと（2026-07-09 確定取引日ベースと当日分を分ける）。
- 新規ユニバース拡張の独断（**月次投入ゲート**を通す・ROADMAP §M）。
