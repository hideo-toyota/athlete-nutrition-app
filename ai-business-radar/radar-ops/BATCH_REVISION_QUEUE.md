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
- 2026-07-10（同日・追記2）: オーナー指示により**次便キュー Q10 を登録**。

## 6. 次便キュー（オーナー指示・急ぎでない）
### Q10 — MV-001 相場観ログの正式取り込み（判断記録レーン接続便で実施）
- 入力: `HANDOFF_OPEN_ITEMS_20260710.md`・`journal/market_view_log.jsonl`（MV-001・前セッションのローカル
  = Mac/live に存在。**配送待ち PENDING_DELIVERY**・受領時に sha256 照合）。
- 作業: MV-001 のスキーマを **judgment_lane（`CLAUDE_HANDOFF_judgment_record_lane.md` §2）と
  ANALYSIS_QUALITY_RULES の相場観規定（オーナー参照「R9」）に整合**させ、`journal/` の正式台帳として
  INDEX に掲載する（PIT・append-only・writer 必須・推奨化禁止ガードは判断記録レーンと同一）。
- ⚠️ 版差の記録（正直申告）: GitHub 正本の `ANALYSIS_QUALITY_RULES.md`（v1 正本化・sha `bf82eb2f…`）は
  **R0–R7 のみで R9 が存在しない**。オーナー参照の R9 は Mac/live 版の規定と推定 → Q10 実施時に
  Mac/live 版を受領・突合し、必要なら ANALYSIS_QUALITY_RULES を v2 改版（R8/R9 追補）してから取り込む。
- 期限: なし（急ぎでない・判断記録レーン実装 SPEC と同便が自然）。

### Q11 — kabutan lunch 分析の訂正と自動品質ゲート追補（Codexレビュー 2026-07-10 受理）
- 裁定: Codexレビュー（公開品質4/10・指摘8点）を**概ね妥当と認定**。処置順:
  1. **即時（司令塔）**: 指摘#1（7236 momentum=15.0 vs 本文「80台」）・#2（3銘柄集計の非再現）を
     `kabutan_observer_lunch.json` と**一次突合で確定してから**、投稿済み本文へ訂正返信（append-only・
     「訂正の核心」文を土台に）。レビュー数値も突合までは INFERENCE 扱い（無検証採用しない）。
  2. **次便（裁定者SPEC・月次ゲート例外=恒久修正）**: kabutan レーン品質ゲート3点 —
     (a) 列挙コード/条件式の決定論的再計算 (b) THIRD_PARTY_REPORT→FACT 昇格阻止
     (c) 検証計画と実装済み取得能力マニフェストの照合（J-Quants=日次・寄与度API無し等）。
  3. **同便**: ANALYSIS_QUALITY_RULES v2 — **CALCULATION / THIRD_PARTY_REPORT をラベル正式定義**
     （現行 R1 は三分類のみ・運用は既に使用中の規約遅れ）＋観測/生成/記録時刻の三分離をタイトル様式に明記。
     Q10 の R8/R9 版差突合と**同便で1回で**解決する。
- 記録事項: 分母相違（現物指数寄与535円 vs 先物前日比1370円）・選抜12銘柄からの breadth 一般化禁止・
  保有読替の UNKNOWN 化（NVDA ファクター重複未計算）・日経平均=PAF調整価格加重（時価総額説明は不正確）・
  引け後照合先=日経公式 Daily Summary（EDINET 不使用）。
