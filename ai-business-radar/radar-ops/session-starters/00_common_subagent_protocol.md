# 00_common_subagent_protocol.md — 共通起動プロトコル（改訂 v2）

- as_of: 2026-07-10 / writer: クラウド裁定者 / 適用: 全セッション起動時に**最初に**読む
- 改訂点(v2): 正本参照を ROLES v2 / INDEX v2 / ROADMAP v2 に更新。判断記録レーン・月次投入ゲート・education 自動採点一本化を反映。

## 起動時に必ず行う（順）
1. **INDEX 照合**: `ai-business-radar/radar-ops/INDEX_current.md` を読み、§7 配備照合（正本群の sha256 一致）を確認。不一致は着手前に停止・報告。
2. **役割の確定**: `ROLES_current.md` §1 で自分の行を特定。接頭辞（§2.2）と署名 `[writer:]`（§2.3）を確認。
3. **規約の内面化**: `ANALYSIS_QUALITY_RULES.md`（FACT/INFERENCE/UNKNOWN 三分離・R2 禁止事項・PIT・秘密非扱い）。
4. **工程の確認**: `ROADMAP_current.md` で自分の担当工程の状態（CLOSED/IN_SPEC/BLOCKED/DORMANT）と**月次投入ゲート**（§M）を確認。**ゲート外の新規着手はしない**。

## 不変規律（全レーン共通）
- **売買推奨・順位・価格目標を出さない**（検証優先度 ≠ 推奨順位）。
- **秘密（鍵/webhook/.env 実値/有料本文/raw 本文）を読まない・保存しない・出力しない**。状態表記のみ。
- **PIT・append-only**（既存日を上書きしない・台帳は訂正行で是正）。
- **単一書き手**（コア/tests は既定権限か書き手宣言のあるセッションのみ）。各コミットで巻き込みゼロ確認。
- **正直な申告**（逸脱・未達・データ品質の瑕疵を隠さない）。DoD 接地でのみ「完了」と書く。

## 入力・出力
- 裁定入力の正規形式は **URL+sha256**（司令塔）。転記形式は形式逸脱として記録。
- 出力接頭辞: 裁定者=`CLAUDE_HANDOFF_` / 司令塔=`CONFIRM_`・`STATUS_` / 開示=`SELF_ROLE_` / Codex=`CODEX_` / 検証役=`VERIFY_`。
- 報告は `radar-ops/reports/` へ（`publish_reports.sh` 経由で reports リポへ配送。秘密スキャン必須）。

## 停止条件（共通）
単一 asof 不一致 / 偽 OK / 正常行巻き込み / 既存出力形式の非互換破壊 / 秘密・有料本文・raw 本文への接触 / 裁定範囲外の着手要求 → **停止・差し戻し**。
