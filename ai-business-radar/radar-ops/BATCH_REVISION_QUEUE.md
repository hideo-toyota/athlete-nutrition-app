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
- **状態更新（2026-07-10 同日）: SPEC を前倒し発行済み** = `CLAUDE_HANDOFF_kabutan_quality_gates_spec.md`
  （preclose 便でも既知誤り #7/#8 が再発しプロセス欠陥と認定 → 「次便」から当日発行へ繰上げ。
  訂正2号+暫定措置（因果較正/保有読替の2節降格）は
  `reports/CLAUDE_HANDOFF_codex_preclose_review_ruling_20260710.md` 参照）。
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

### Q12 — 逆方向レビュー: Codex 発の分析（CODEX_AUTO_ANALYSIS_* 等）の正確性監査（オーナー指摘 2026-07-11 受理）
- 問題認定: 現行の品質ループは**非対称**。司令塔/レーン→Codex レビューの方向はゲート化済み（Q11）だが、
  **Codex 実行役→司令塔・記録系の方向には検証ゲートが無い**。
- 既知の誤り伝播（FACT・配送済み報告どうしの矛盾）: `CODEX_AUTO_ANALYSIS_20260710` の
  「EDINET 全体バッチ進捗 400/3818(10.5%)・coverage 完了と表現できない」は、
  `CONFIRM_edinet_daily_limit_20260709` の確定事実（**07-07 に 3818/3818 完了済み・400/日は
  ローリング再取得周期**）と矛盾（doctor の progress counter 表示の読み違い）。
- 作業（次便以降・2段）:
  1. **遡及スポット監査**: 配送済み CODEX_AUTO_ANALYSIS_（07-07/07-09/07-10）の主要主張を
     既確定事実と突合し、誤り一覧を訂正行形式で記録（司令塔実施・裁定者が突合表を発行）。
     ※ CODEX_ ファイル自体は不介入原則のまま — 訂正は別文書で（append-only）。
  2. **前方ゲート**: CODEX_AUTO_ANALYSIS_PROMPT.md へ「実行前に incoming/ の確定事実
     （EDINET 調査・2c-1 snapshot 行等）を読み、既確定と矛盾する再主張をしない」節を追加。
     同ファイルは **Codex 管理**のため、変更はオーナー経由で Codex に依頼（裁定者は要求仕様を発行）。
     2c-1 で doctor に snapshot 行が並記された今、400/3818 誤読は表示レベルでも解消可能。
- 位置づけ: 恒久修正クラス（月次ゲート例外）。ただし実装枠は Q11 実弾→2c-2 の直列を乱さない
  タイミングで（遡及監査は読み取りのみなので随時可）。
- **スコープ更新（2026-07-11・Codex findings F9/F10/F11 受理・append-only）**:
  1. **EDINET「400」の3指標分離を採用**（F9）: `corpus_coverage`（07-07 に 3818/3818 完了）/
     `latest_slice_visibility`（旧 reader の最新 asof 可視範囲 400/3818 — この記述は部分的に正しい）/
     `snapshot_coverage`（2c-1: with_filing 3818/3837・missing 19）。Q12 訂正文はこの3語で書く。
  2. **遡及監査の対象を拡張**（F10）: 07-09 / 07-10 / **07-11** の3通（07-07 版は当該論点で正しいと
     Codex 自身が確認 → 監査対象から除外し、正常例として突合表に記載）。
  3. **前方ゲート要求仕様の確定**（F11・オーナー経由で Codex に依頼する内容）:
     (a) `incoming/INDEX_current.md`・`ROLES_current.md`・`ANALYSIS_QUALITY_RULES.md` の必読
     (b) v2 session-starters の正パス（incoming/ 配下）参照
     (c) EDINET 3指標分離の遵守 (d) 同日再実行は append-only または版管理（PIT 規律との衝突解消）
     (e) 既確定事実と矛盾する implementation queue を生成しない。
  4. **orchestrator 統合分析の暫定隔離**（F7 関連）: Q11 ゲートは kabutan レーンのみを保護。
     orchestrator 経路はゲート外につき、その成果物は**前方ゲート実装まで draft 扱い**
     （Obsidian/CONFIRM_ への無検証転記禁止）。07-11 04:02 の
     `orchestrator_integrated_0402.md` は **NO_POST / quarantine** 指定（既知誤認3点を含む）。
     **月曜の Q11 実弾成功による暫定措置解除は kabutan レーン限定**であり、orchestrator には及ばない。

### Q13 — 教育資料「共通ドライバー回」の改稿と教材採用ゲート（2026-07-11 裁定）
- 裁定: Codex レビュー（重要5+追加4）**全点受理・条件付き採用を追認**
  （`reports/CLAUDE_HANDOFF_education_material_ruling_20260711.md`）。
- 改稿9箇所の要点: DCA/インデックスの概念分離＋**事前登録ベンチマーク** / observer 件数=
  CALCULATION＋入力出自併記 / 分散効果の断定緩和（相関<1・ストレス時相関上昇）/ Q2=転用問題化
  （主要な罠+副次的な罠+確認データ）/ Q3=H1・H2 分割＋検証窓＋反証条件 / 535円=THIRD_PARTY_REPORT
  留め / NVDA 9.0%・32.5%に as_of+算定方法 / 3436 テーマ分類=INFERENCE / 20/50 の適用限界明記。
- **模範解答・採点基準も同時改稿**（本文のみ改稿だと grader が誤採点 — 整合性要件）。
- **教材採用ゲート新設（恒久）**: 新規・大幅改稿教材は配信ローテーション投入前に独立レビュー1回
  （Codex/第2監査役・findings 形式・採用/条件付き/差し戻しの3値）。本教材は改稿後に Codex の
  解消確認レビュー（軽量）を経て投入。既存配信済み教材への遡及はしない。
- **状態更新（2026-07-11 同日）: 実作業を正式割当済み** =
  `reports/CLAUDE_HANDOFF_education_revision_assignment_20260711.md`。
  改稿=Codex（書き手宣言 `codex/edu-common-drivers`・対象パスは司令塔が確定）/
  軽量再レビュー=司令塔（10項目 PASS/FAIL+解答キー整合のみ・テーマ再審なし）/
  投入判定=裁定者。実装枠は不消費。再レビューの優先度は月曜 Q11 実弾・訂正投稿確認より後。

### Q14 — orchestrator レーン品質ゲート（2026-07-11 FAIL 裁定・要求仕様確定済み）
- 契機: 07-11 08:29 orchestrator 統合分析の Codex レビュー = **FAIL 3/10・BLOCKER 3件**
  （取得層の偽OK: 日経businessがChatGPT画面なのに status=ok / 土曜を「寄り前」扱い /
  「J-Quants未確定」が manifest 実在と矛盾）。裁定全文 =
  `reports/CLAUDE_HANDOFF_orchestrator_fail_ruling_20260711.md`。
- **即時処置（裁定命令・司令塔）**: orchestrator 自動投稿の一時停止（投稿ステップのみ・可逆・
  生成はdraft継続可）/ append-only VOID訂正の投稿 / 偽OK運用ファイルの訂正記録。
  解除条件 = 本ゲートの DoD 達成。
- 要求仕様（SPEC は次便・5点確定）: (a) 取得先ドメインallowlist検証（不一致=FAILED・status=ok禁止）
  (b) セクション完全性（欠落=partial） (c) 営業日ゲート（DT-1a trading_calendar 使用・
  非営業日は週末/休日レビュー様式へ） (d) 入力実在チェック（「未確定」主張前に manifest 確認）
  (e) 投稿前検証器（Q11型: CALC再計算・ラベル昇格阻止=意味強化翻訳含む・能力マニフェスト照合
  =TOPIX日程はJPX総研公式を追記・基準値as_of開示・答え合わせの再現可能様式）。
- 裁定者の自省記録: F7 の「draft扱い」は投稿経路の実態確認を欠いた甘い措置だった
  （0402 は権限で偶然止まっただけ）。停止命令までに投稿到達1件 = 判断遅延として記録。

### Q13 状態更新2（2026-07-12・パス確定報告の受理・append-only）
- 司令塔 `CONFIRM_q13_material_paths_20260712.md`（fdc68af → 報告リポ 4b7cd31）を**設計ごと受理**:
  1. **EDUCATION_MATERIAL_SPEC.md 新規作成方式を承認**: `CLAUDE_HANDOFF_daily_education.md` は
     裁定者専用接頭辞（ROLES §2.2）のため Codex は直接上書きせず、改稿版を新ファイルとして作成 →
     旧ファイル置換と参照切替（education_daily.sh:55）は司令塔レビュー後。
     **裁定者の見落とし（割当時に接頭辞衝突を検知せず）を司令塔が解消した — 記録する。**
  2. 3層スコープ承認: 宣言対象（仕様本体の改稿版新規作成 / education_daily.sh PROMPT ブロック :54-66 /
     回帰テスト追随）・整合対象（grader 採点プロンプト :148- ・波及時のみ事前一言）・
     **不変=機械可読マーカー**（PUBLIC_ABOVE/ANSWERS_BELOW — grader 抽出・完全性ゲートが厳密一致依存・事故クラス）。
  3. 宣言成立 = 本 CONFIRM の Codex 到達（オーナー中継）。
- 実行キュー承認+1修正: ①〜③（月曜 Q11 実弾 → Q12 遡及監査随時 → Q13 再レビュー）は承認。
  ただし **Q14 の即時処置（orchestrator 投稿停止+VOID 訂正）だけは①より先**
  （偽 OK 計器の停止は時間依存のリスク遮断）。

### Q13 状態更新3（2026-07-12・宣言成立確認+解釈裁定・append-only）
- 書き手宣言 `[writer: codex/q13]` **成立確認**（根拠: CONFIRM_q13_material_paths_20260712 の到達・Codex 受領返答）。
- 通知文 16〜20 行の軽微矛盾（参照切替の帰属）への**解釈裁定 = Codex の保守的解釈を正として確定**:
  Codex は仕様（EDUCATION_MATERIAL_SPEC.md 新規）・PROMPT 改稿案・テスト追随まで。
  **本番参照切替は司令塔の 10項目 PASS 後・司令塔のコミット**。
- 拘束不変条件を追加: **Codex のコミットは司令塔 PASS まで 19:00 LaunchAgent の本番挙動を変えない**。
  education_daily.sh 直接編集が即時に本番へ効く構造なら、差分は新規ファイル/patch 側に留め、
  sh への反映は司令塔の切替コミットに含める（手段は Mac 側に委任・不変条件が判定基準）。
- Codex は解釈を完了報告（CODEX_ 文書）へ明記予定・対象ファイル未変更のまま次作業=改稿着手。

### Q15 — 検証役の正式化と再稼働準備（2026-07-12・オーナー質問を契機に登録）
- 裁定全文: `reports/CLAUDE_HANDOFF_verifier_role_20260712.md`。
- 穴の自己指摘: ROLES v2 §1 に検証役の行が欠落（VERIFY_ 接頭辞のみ存在）/ session-starters に検証役用なし。
- 発行物（CAPABILITY_MANIFEST 受領時の INDEX 追補4 と**同便**・churn 1回に束ねる）:
  1. **ROLES v2.1**: 検証役行の追加（固定基準の反証型実装検証・実装者/テスト作成者と同一人格不可・
     git 書込なし・保全は司令塔）+ 懸案 #10 の反映。
  2. **session-starters/07_verification_session.md** 新規。
- 検証割当書テンプレートは裁定書 §4 に確定済み — starter 発行前でも割当書+オーナー起動で先行起用可。
- 起用候補: Q11 検証器の反証検証（クローズ条件にはしない・事後）/ 2c-1 snapshot の look-ahead 反証
  （2c-2 前が理想）/ Q14 ゲート実装後 / Q12 標本再検証（任意）。

### Q13 状態更新4（2026-07-12・Codex 改稿完了・司令塔レビュー待ちへ遷移）
- 完了報告受領: commit `f6b3077 feat(education): add Q13 material quality contract [writer: codex/q13]`
  / 新仕様 `radar-ops/EDUCATION_MATERIAL_SPEC.md` / 報告 `CODEX_Q13_EDUCATION_REVISION_20260712.md`。
- 拘束不変条件の遵守申告（Codex）: education_daily.sh:54-66 変更なし / 旧 CLAUDE_HANDOFF_daily_education.md
  変更なし / 19:00 LaunchAgent 挙動変更なし / PROMPT 改稿案は新仕様側に隔離 / 参照切替は留保 /
  別セッション差分（orchestrator_post.py 等・Q14 コミット 4c8c595）の巻き込みなし・amend なし。
- テスト申告: 教育 40件 PASS・全体回帰 492件 PASS（直前基線 486+回帰6件追加=492 と整合・CALCULATION）。
- **次工程 = 司令塔の軽量レビュー**（10項目 PASS/FAIL+解答キー整合のみ・テーマ再審なし）。
  レビュー時の確認点3つ（裁定者指定）:
  1. **grader プロンプト整合の「事前通知」実施の有無**（宣言は「必要な場合のみ・事前通知して」を条件と
     していた。通知記録が無ければ軽微逸脱として記録 — 処置には影響させない）。
  2. `git show --stat f6b3077` で不変条件を機械確認（sh:54-66・旧仕様・公開部マーカーへの diff ゼロ）。
  3. テスト2系統の再実行（教育40・全体492）。
- 全 PASS → 司令塔が参照切替を判断・実施（切替コミット）→ CONFIRM_ 報告 → 裁定者受領で Q13 クローズ。
- 優先度は不変: Q14 即時処置 → 月曜 Q11 実弾 → 本レビュー。

### Q14 状態更新（2026-07-12・即時処置完了+到達実態の訂正+追加 VOID 裁定）
- 即時処置3点 = **完了・受理**: ①キルスイッチ `4c8c595`（フラグ可逆・生成draft継続・実弾遮断確認・
  テスト494=492+2整合） ②08:29 VOID（msg 1525622810968326195） ③偽OK訂正
  （status=partial+error_classes+correction メタ・items 不変）。
- **事実訂正（裁定書に append-only 追記済み）**: 07-11 の投稿到達は1件でなく**計4件**
  （08:30・09:05・11:39=土曜「前場後」・18:44）。裁定者の過少記録として訂正。
  教訓の標準化: **レーン停止裁定には到達実態の全数確認を同梱**。
- **追加裁定: 残り3件（09:05・11:39・18:44）は全件 VOID**（投稿ごとに欠陥タグ B1/B2/B3、
  確定できない投稿は「ゲート外産出・入力健全性未検証」と正直に記載 — 欠陥の捏造禁止）。
- 週末レビュー再生成「しない」= 承認。解除条件（Q14 ゲート DoD）不変・SPEC は次便。
