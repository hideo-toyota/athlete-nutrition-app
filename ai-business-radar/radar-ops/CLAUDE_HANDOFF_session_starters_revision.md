# CLAUDE_HANDOFF — session-starters改訂指針 + INDEX v2優先化(司令塔用)

クラウド側裁定者より。Codexのsession-starters監査を受理。**全指摘採用**(いずれも既決ルールへの
文書整合であり新規スコープではない)。加えて監査が露呈させたINDEX陳腐化を優先是正する。

## 1. session-starters 改訂(全採用・改訂順は§3)
- **00_common_subagent_protocol**: 権限・秘密・書き手統制・共通Return Packetのみに絞る。分析品質は
  ANALYSIS_QUALITY_RULES、J-Quantsは各terminal、BT規律はBT-1系を**参照**させる(肥大化させない)。
  **override規律の厳格化**: 「人間overrideは理由記録で続行」は**SHOULD/MAYのみ**に適用。
  秘密非表示・ToS・test期間封印・書き手統制(single-writer)は**理由付きでもoverride不可**=
  裁定改版でのみ変更。
- **01_command_center**: 「司令塔版(ターミナルClaude専用・git既定書き手)」と
  「Codex実装調整版(git非接触・提案は裁定者へ)」に**分割**。Codexが司令塔を名乗る経路を封じる。
- **05_code_audit_fix**: 「裁定済みタスクの実装・テスト・自己検証」に変更。**独立監査は別セッション**
  (実装者は自分の実装を監査しない原則)。
- **02_data_ops**: 原則**read-only**。修正はReturn Packetで05へ渡し、書き手宣言後のみ実装。
- **03_analysis_selection → 03_analysis_and_review に改名**: 候補件数を**0〜10件**(0件=正常)。
  必須記載: ANALYSIS_QUALITY_RULES R1〜R9のPASS/FAIL/N-A / analysis_generated_at+各observed_at /
  raw・重複除外後・クラスタ数の3件数 / 検証優先度は期待リターン順でない / 指数→個別読替禁止 /
  報道因果とデータ因果の分離 / 基準を満たす対象ゼロならhuman review list 0件 / discipline未通過の明記。
- **04_backtest_strategy**: 固定優先候補(P5等)削除。INDEX/ROADMAP掲載タスクのみ受領。
- **06_jquants_cli_adapter**: 0-3は「完了済み・回帰確認のみ」。00との重複規則は06へ一本化。

## 2. Return Packet 共通スキーマ(00に定義)
- 種別4分類: `independent_verification` / `second_audit_opinion` / `adjudicator_decision` /
  `human_decision`。
- 共通欄: `task_id` / 正規指示のURL+sha256 / writer宣言 / 許可ファイル /
  状態(完了|部分完了|停止) / commit ID / 次の担当。

## 3. 改訂順(Codex提案どおり)
ANALYSIS_QUALITY_RULES配備(INDEX掲載)→ 00/01/05の役割衝突解消 → 02/03/04/06のレーン別更新。

## 4. INDEX v2 の優先化(監査が露呈させた陳腐化)
- INDEX_current は §7追加(75fceec)以降、十数本の新規正本(ISSUE_MAP / ANALYSIS_QUALITY_RULES /
  judgment_lane_spec / deployment_gate_spec / us_context_m0_spec v2 / reading_layer_integrity /
  dual_commander_resolution / g1_residuals_accept / audit_consolidation ほか)を**未掲載**。
- 裁定者は**バッチ改版の第一便として INDEX v2 を最優先発行**する(ROLES v2と同便)。それまで
  司令塔は incoming/ に各文書を配備し、暫定の有効文書一覧を確認依頼MDで保持してよい。
- 常設正本の新設: ISSUE_MAP / ANALYSIS_QUALITY_RULES を §1(常設・全セッション必読)へ昇格。

## 5. スコープ確認
- 本件は新機能でなく**既決ルールへの文書整合+目次是正**。Phase 2c・M0の実装順に影響しない
  (並行の文書整備)。実装リソースを食わない範囲で司令塔が進めてよい。

規律不変: single-writer / 秘密・ToS・test封印はoverride不可 / append-only / push無し(報告リポ)。
