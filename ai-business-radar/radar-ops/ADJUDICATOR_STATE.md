# ADJUDICATOR_STATE.md — 裁定者ダッシュボード(3分で読む現在地)

- as_of: **2026-07-15**  / writer: クラウド裁定者 [writer: adjudicator]
- 性質: **再生成可能なビュー・正本ではない**(正本は BATCH_REVISION_QUEUE.md=詳細台帳と各裁定文書。
  本書は毎便更新・上書き可。INDEX §7 の sha 照合対象に**含めない**)。
- 使い方: ターミナルなら `git fetch && git show origin/claude/radar-batch-revision-lk9h56:ai-business-radar/radar-ops/ADJUDICATOR_STATE.md`。外出時は GitHub モバイルで本ファイルを直接閲覧。

---

## 0. 現行性能主張の正(R4・2026-07-14 固定)
**safety=PARTIAL / reproducible delivery=FAIL / outcome learning=INSUFFICIENT / investable alpha=NOT_PROVEN**
(矛盾する性能表現は全レーン禁止・昇格には軸ごとの定義済み証拠。詳細= completion_blueprint 裁定)
✅ 司令塔は復旧済み(af26aaf 実証・07-15 期限の代替条項は不発効)。

## 1. いま動いているもの(実行中・監視中)
| 項目 | 状態 | 次のイベント |
|---|---|---|
| **Q14 解除(2レーン)** | 両裁定発行済み(NewsPicks: `f2067dce…` / orchestrator: `807e0981…`)・司令塔の照合→解除操作待ち | **LIVE-CONFIRM ×2**(各レーン初回実投稿)→ 完了で Q14 全クローズ+暫定措置(2節降格)解除を同時判定 |
| orchestrator 健全性チェック | 解除後3営業日投稿0なら FAIL パターン報告 | 司令塔 |
| Q13 教材 | Codex 改稿完了(f6b3077)・司令塔10項目レビュー **期限 07-14 EOD JST** | PASS→参照切替→クローズ |
| 2c-1 delta 修正 | 狭域再オープン中(TZ 正規化+破損 filing 区別)・実装待ち | 実装→検証役 delta 再検証(F3/F8 の2面)→ PASS で 2c-2 SPEC 発行(裁定者) |

## 2. 報告待ち(司令塔からの CONFIRM_ 未着・状態 UNKNOWN)
- **Q11/R1-1/R1-2 = Codex 実装+独立検証 PASS(条件付き受領・07-15)** → 17:32 自然スロット
  POSTED_OK で Q11 クローズ+kabutan 降格解除+delivery 昇格を同一裁定。完了パケット+VERIFY 3本の配送待ち
- 訂正1号(lunch)/2号(preclose)の投稿完了記録(msg id)
- ShOutFY 自己株控除・Bulk/REST パス衝突の読み取り再現(Q17 5-2)
- starters 通常パス配備・scratch 3件所有者確認(boot v2 タスク)

## 3. 配送待ち(PENDING_DELIVERY・受領後に裁定者が処置)
- CAPABILITY_MANIFEST.md(CONFIRM_ 埋込方式)→ INDEX 追補4
- **Relay dry-run 2ファイル**(CONFIRM_relay_dryrun_delivery・F4 方式)→ SPEC 後に追認判定
- Mac の CLAUDE.md(+AGENTS.md あれば)→ 監査 → 薄いブートストラップ版を発行
- HANDOFF_OPEN_ITEMS_20260710・MV-001(Q10)/ Mac/live 版 ANALYSIS_QUALITY_RULES(R8/R9 突合)
- **統合審査便の原本4件**: COMPLETION_BLUEPRINT packet(`ae055fdf…`)+AOL(8771130)/POC-M0(b7fabeb)/SD(8ac65a7)
- FRED_API_KEY 記入(オーナー)→ M0 v2 契約確認と合わせて実装 GO 判定

## 4. 裁定者の宿題(発行予定)
| 便 | 内容 | 前提 |
|---|---|---|
| **正本改版バンドル**(INDEX 追補4と同便) | ROLES v2.1(検証役行+#10+profile サブ表 §1c)/ starters 07(検証役)・08(quant)/ AQR v2(CALCULATION・THIRD_PARTY_REPORT 正式定義+claim taxonomy 一本化+R8/R9)/ QD-2 正本文言改版(W1/W3 状態フィールド化)/ CLAUDE.md・AGENTS.md 薄型 / ADJUDICATOR_INTAKE_PROTOCOL の INDEX 掲載 | manifest 受領+Mac 版 AQR(揃った分で切る) |
| 2c-2 readiness SPEC | consumer migration 含む | 2c-1 delta PASS |
| Relay M0 SPEC | 輸送のみ・修正5条件 | クリティカルパス(Q11 クローズ・2c-1 delta・Q14 LIVE-CONFIRM)後 |
| Q12 前方ゲート正式依頼 | 要求仕様5点(台帳確定済み)をオーナー経由で Codex へ | 随時可 |
| **2026-08 月次ゲート** | 候補: DT-1b / A0(HB-003 基盤)/ D0-EVIDENCE-PACKET(48KiB)/ QD-3(owner_attested フローとセット)。**outcome ledger 消化(open 55件)を容量計算に算入** | 8月初週 |

## 5. 直近の裁定索引(新しい順・詳細は各文書)
| 日付 | 裁定 | 文書(reports/) |
|---|---|---|
| 07-14 | Blueprint R1-R4: 性能主張固定・信頼性4点=即応クラス・構造化出力=設計のみ・Gates C/D=原則のみ | `CLAUDE_HANDOFF_completion_blueprint_ruling_20260714.md` |
| 07-14 | クリティカルパス: 司令塔復旧第一・Q11 限定SPEC・担当の期限付き代替構造 | `CLAUDE_HANDOFF_critical_path_ruling_20260714.md` |
| 07-14 | ハイブリッド/Relay: Q18追補 ACCEPT・SPEC DEFER(条件3点)・dry-run 保留資産 | `CLAUDE_HANDOFF_relay_m0_hybrid_ruling_20260714.md` |
| 07-14 | Q14 orchestrator 解除可+健全性チェック | `CLAUDE_HANDOFF_q14_release_orchestrator_20260714.md` |
| 07-14 | Q14 NewsPicks deepdive 解除可+LIVE-CONFIRM 発効+HOLD 実効対応表の標準化 | `CLAUDE_HANDOFF_q14_release_newspicks_20260714.md` |
| 07-13 | Q14 C-12/F-I =(a)採用+LIVE-CONFIRM 条項 | `CLAUDE_HANDOFF_q14_c12_ruling_20260713.md` |
| 07-12 | A0=HB-003 の enabling substrate・8月ゲート(Q17 5-5 解消) | `CLAUDE_HANDOFF_a0_hb003_integration_ruling_20260712.md` |
| 07-12 | データ活性化+Relay 8項目(Q17) | `CLAUDE_HANDOFF_data_activation_relay_ruling_20260712.md` |
| 07-12 | 出力 HOLD 二段裁定+2c-1 FAIL 処置 | `CLAUDE_HANDOFF_output_hold_ruling_20260712.md` |
| 07-12 | 検証枠組み v2(11件受理)/ 2c-1 割当 | `CLAUDE_HANDOFF_verifier_role_20260712.md` / `VERIFY_ASSIGN_2c1_snapshot_20260712.md` |
| 07-12 | quant-DS 条件付き採用(Q16) | `CLAUDE_HANDOFF_quant_ds_ruling_20260712.md` |
| 07-11 | 2c-1 SPEC / Q11+2c-1 受理 / boot v2 / 教材裁定・割当 | `CLAUDE_HANDOFF_phase2c1_*` ほか |

## 6. 恒久原則の要点(裁定で確立した順に)
検証は分類を変えない / レーン停止裁定に到達実態の全数確認を同梱 / HOLD の実在と実効は別(機構-遮断対象の対応表必須) / fail-open 経路を作らない(bypass 禁止・実弾 positive は解除後初回スロット) / 取得できない証拠を要求しない(UNKNOWN 明示) / 二重定義禁止(入力健全性の正本=Q14(f)) / 単一裁定者(本セッション)。
