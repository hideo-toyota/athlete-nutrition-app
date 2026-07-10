# BATCH_REVISION_QUEUE.md — バッチ改版キュー（裁定者・引き継ぎ台帳）

- doc-id: `BATCH_REVISION_QUEUE`
- as_of: 2026-07-10
- writer: クラウド裁定者（cloud adjudicator・新世代セッション）
- 位置: `ai-business-radar/radar-ops/BATCH_REVISION_QUEUE.md`
- 目的: 前世代裁定者が積んだ「未発行のバッチ改版一式」を引き継ぎ、本ラウンドで**発行(issued)**に遷移させる台帳。append-only。

---

## 0. 引き継ぎの再構成根拠（FACT）
正本ツリー（Mac/live）は本体 push 禁止のため GitHub `athlete-nutrition-app` には未配備だった。前世代の handoff は reports リポの一次資料から再構成した:
- `CONFIRM_g1_residuals_20260709.md` §次アクション: 「待機: INDEX/ロードマップ/ROLES v2 バッチ改版(裁定者)/ dialogue_responder.py の追認・巻き戻し裁定 / 判断記録レーン仕様・M0仕様の発行 / …」
- `CONFIRM_batch1_issue_map_m0_20260709.md` §次: 「バッチ改版(ROLES v2 / INDEX v2 / ロードマップv2 ほか)の次便を待つ」
- `SELF_ROLE_deviation_20260708.md`: dialogue_responder のオーナー権限編集 = 「ROLES v2 で追認または巻き戻しの裁定対象」
- `SELF_ROLE_disclosure_commander_20260709.md` §9: education 二重採点 = 自動レーン一本化の具申（裁定待ち）
- `STATUS_roles_adopted_20260707.md` / `CODEX_ORG_20260707.md`: 役割表・接頭辞・INDEX §7 配備照合の様式

## 1. キュー項目と発行状態
| # | 項目 | 前世代状態 | 本ラウンド | 成果物 |
|---|---|---|---|---|
| Q1 | **ROLES v2** | 未発行 | **issued** | `ROLES_current.md`（v2） |
| Q2 | **INDEX v2** | 未発行 | **issued** | `INDEX_current.md`（v2・§7 全13ファイル sha） |
| Q3 | **ロードマップ v2** | 未発行 | **issued** | `ROADMAP_current.md`（v2） |
| Q4 | **判断記録レーン 発効** | 仕様未発行 | **issued（ACTIVE）** | `CLAUDE_HANDOFF_judgment_record_lane.md` |
| Q5 | **月次投入ゲート 発効** | 未定義 | **issued（ACTIVE・初回2026-07）** | `CLAUDE_HANDOFF_monthly_intake_gate.md` |
| Q6 | **session-starters 改訂配布** | 未改訂 | **issued** | `session-starters/00–06`（06 新規） |
| Q7 | **dialogue_responder 追認/巻き戻し** | 裁定待ち | **追認**（ROLES v2 §3） | ROLES_current.md §3 |
| Q8 | **education 二重採点の恒久ルール化** | 具申・裁定待ち | **自動一本化を正式化** | ROLES v2 §4-1 / ROADMAP §1 |
| Q9 | **ANALYSIS_QUALITY_RULES 正本化 / ISSUE_MAP 正本化** | v1 配備のみ | **正本化（据置）** | 両 md を正本ツリーへ |

## 2. 本ラウンドで発行しなかったもの（次便へ持ち越し・理由付き）
- **M0 v2 実装 GO**: `SOURCE_CONTRACT_us_context_m0.md` の契約確認は**別便**。前提の一部（FRED/SOX/FX）が UNKNOWN のため、月次投入ゲート §5 で「契約確認後の限定実装」に絞る方針のみ記載。実装 GO は契約確認とキー記入が揃ってから。
- **Phase 2c 各節 SPEC**（2c-1 snapshot / 2c-2 readiness / TOPIX·33業種 index 取得）: 実装順は採用済（ROADMAP §2）。SPEC 本体は次便。
- **DT-1b/c SPEC**: 月次投入ゲートで 2026-08 へ hold（ROADMAP §3・§M）。
- **§7-4 grader二重行の正典指定・date衝突是正**: バッチ第1便 accept §2 で**実施済**（`88aa365`）。本キューでは再発行しない。

## 3. 受領後の司令塔手順（配備照合）
1. INDEX_current.md §7 の sha256 マニフェスト（全13ファイル）を照合 → `incoming/` を最新の鏡に。
2. `CONFIRM_batch_revision_v2_202607` を作成（受領・照合結果・逸脱の有無）→ `publish_reports.sh` 配送。
3. 月次投入ゲート初回記録 `CONFIRM_intake_202607` を作成（投入=M0限定 or 2c-1 振替・DT-1b hold の記録）。
4. education 手動採点の停止を運用に反映（自動 `education_grader` 一本化・ROLES v2 §4-1）。

## 4. 参照 sha256（本発行物）
- 正本13ファイル: INDEX_current.md §7 マニフェスト参照。
- INDEX_current.md 自身: `7773458f7c660d6868f8a6912c5c098781b507f64f8339c21c2a80e0e44f6176`
- 発行カバー（reports 配送）: `CLAUDE_HANDOFF_batch_revision_v2_20260710.md`（equity-radar-reports/reports/）。

## 5. 履歴
- 2026-07-10: 新世代裁定者が Q1–Q9 を発行。Q2 で正本ツリーを `ai-business-radar/radar-ops/` に初配備。M0/2c/DT-1b は次便へ持ち越し（§2）。
- 2026-07-10（同日・追記）: **オーナー裁定 = 既発行 v2（87b7eec）で宿題A（INDEX v2・ROLES v2）充足**。
  なお `HANDOFF_OPEN_ITEMS_20260710.md` と `journal/market_view_log.jsonl`（MV-001・オーナー相場観表明）は
  GitHub 正本に**未配送**（Mac/live のみに存在と推定・PENDING_DELIVERY）。受領後に sha256 照合のうえ、
  INDEX への掲載（相場観ログの正本化・判断記録レーンとの接続）は**次便**で扱う。
  原則の確認（オーナー指示より）: **市場超過は前提でなく、判断ログで検証する仮説**
  （ANALYSIS_QUALITY_RULES R2 および判断記録レーン §1 と整合・矛盾なし）。
