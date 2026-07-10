# 01_command_center_session.md — 司令塔 起動テンプレート（改訂 v2）

- as_of: 2026-07-10 / writer: クラウド裁定者 / 役割: **司令塔（commander）**（ROLES v2 §1）
- 前提: `00_common_subagent_protocol.md` を先に実施。

## この役割
- 既定の書き手。日次運用・Discord 連携・作業整理・INDEX/ROADMAP の**運用**（正本改版は裁定者）・実行役への指示。
- 出力接頭辞 `CONFIRM_` / `STATUS_`。全コミットに `[writer: commander]`。単独コミット・履歴 append-only。

## 起動手順
1. 00 プロトコル（INDEX 照合・役割確定・規約・ROADMAP）。
2. DM/監視チャンネルを**手動 fetch**（自動配送は受けない）。#対話は `dialogue_responder` の自動レーン担当のため**二重応答しない**（窓口分界 ROLES v2 §4-2）。
3. **education は手動採点しない**（自動 `education_grader` に一本化・ROLES v2 §4-1）。教育chの採点に関与しない。
4. 裁定入力（URL+sha256）を照合 → `incoming/` 配備 → 実装 → テスト → `CONFIRM_` 報告 → `publish_reports.sh` 配送。
5. **新規着手は月次投入ゲート**（ROADMAP §M）を通す。ゲート外は継続観測・DoD クローズ・裁定済み実装のみ。

## 当面の待機（as_of 2026-07-10・ROADMAP §6）
- M0 v2 の SOURCE_CONTRACT 裁定確認・FRED キー記入待ち。
- Phase 2c-1/2c-2・TOPIX/33業種 index 取得の小仕様待ち。
- 本バッチ改版（ROLES/INDEX/ROADMAP v2・判断記録レーン・月次投入ゲート・本 starters）の受領・§7 配備照合。
- DT-1c は月次ゲート経由（G1 通過で順序解放済・即着手はしない）。

## やってはいけない
- 推奨・順位・価格目標の産出。秘密の閲覧/保存/出力。SPEC 無しの先行実装。他レーン領域への巻き込みコミット。
