# INDEX_current.md — 正本インデックス **v2**

- doc-id: `INDEX_current`
- version: **v2**（v1 世代 sha `75fceeac…`／`75fceeaca933645fa13cb1772059c1e8d47ed27ad980f6b13959f10156b6e90d`。本 v2 で改版・バッチ改版v2）
- as_of: 2026-07-10
- writer: クラウド裁定者（cloud adjudicator）
- 位置: `ai-business-radar/radar-ops/INDEX_current.md`（正本）
- 役割: 正本群の**目次・配備照合(§7)・現行タスクの再構成起点**。新セッションは本書を最初に照合して起動する（session-starters/00）。

---

## §1 正本群（統治文書）
| doc | 役割 | version |
|---|---|---|
| `ANALYSIS_QUALITY_RULES.md` | 分析品質規約（最上位） | v1（正本化） |
| `ROLES_current.md` | 役割・接頭辞・署名・書き手宣言 | **v2** |
| `ROADMAP_current.md` | 工程・順序・月次投入ゲート | **v2** |
| `ISSUE_MAP.md` | value-audit 7論点 | v1（正本化） |
| `INDEX_current.md` | 本書（目次・配備照合） | **v2** |

## §2 発効レーン仕様（裁定者発行）
| doc | 役割 | 状態 |
|---|---|---|
| `CLAUDE_HANDOFF_judgment_record_lane.md` | 判断記録レーン | 発効 ACTIVE |
| `CLAUDE_HANDOFF_monthly_intake_gate.md` | 月次投入ゲート | 発効 ACTIVE（初回=2026-07） |
| `CLAUDE_HANDOFF_kabutan_quality_gates_spec.md` | kabutan 品質ゲート（Q11・実装GO） | 発行 2026-07-10（同日追補） |
| `CLAUDE_HANDOFF_phase2c1_snapshot_spec.md` | Phase 2c-1 snapshot（実装GO・月次ゲート振替枠） | 発行 2026-07-11 |

## §3 配送経路
- 報告・確認依頼は `radar-ops/reports/` に置き、`scripts/publish_reports.sh`（秘密スキャン必須）で reports リポ（`equity-radar-reports`）へ配送。
- 裁定文書の受領は `incoming/`（gitignore の取込ミラー）に配備し §7 で照合。

## §4 session-starters（改訂配布）
| doc | 対象 |
|---|---|
| `session-starters/00_common_subagent_protocol.md` | 全セッション共通（最初に読む） |
| `session-starters/01_command_center_session.md` | 司令塔 |
| `session-starters/02_data_ops_session.md` | 実行役/データ運用 |
| `session-starters/03_analysis_selection_session.md` | 分析・選定補助 |
| `session-starters/04_backtest_strategy_session.md` | バックテスト・戦略検証 |
| `session-starters/05_code_audit_fix_session.md` | コード監査・修正 |
| `session-starters/06_cloud_adjudicator_session.md` | クラウド裁定者（新規） |

## §7 配備照合マニフェスト（sha256）
起動時に各正本の sha256 一致を確認する（不一致は着手前に停止・報告）。**照合対象 = 下記 manifest 15件 + INDEX 自身1件 = 計16件**（INDEX 自身の期待 sha256 は自己参照不能のため、発行カバー/boot 指示書が搬送する）。session-starters は `incoming/session-starters/` 配下の実体を照合する（通常パスの旧版と混同しない）:

```
bf82eb2f9b5cdf3ebdbd497abc64d92ec474b56817c50d73f5223c77e876fcb0  ANALYSIS_QUALITY_RULES.md
c112fa99a6f0da1f49d101aa1ad3dd7a7908264c2db1a5ca6f0512ad35c41645  ISSUE_MAP.md
a1138519eea63a675216761eeace9934155dea196cad368d23971353745b86c9  ROLES_current.md
2a8310e2ac2fc0c3578c6d6885c5ab94e77892f4e1e25857f9d161f3035fa3aa  ROADMAP_current.md
97156e66d31253a02b5a14b1d7ce780cb165dc50efe7834f1fdb666b615ad508  CLAUDE_HANDOFF_judgment_record_lane.md
7bf4692dbe2ae5e6fc40eab5255c14474d26bfddddec49e785e45dfbbd5b3bc8  CLAUDE_HANDOFF_monthly_intake_gate.md
3e8bd8a1a21ed1412e9731c3a80bbfa8c83d290353ce1b2f20f67d64e3261999  session-starters/00_common_subagent_protocol.md
b687e98b59273a4a33ab9e75290a7e53c5d3140839c416a9c9c2250ed46e520d  session-starters/01_command_center_session.md
036f613eb10e6dd4a3790e9d629eddebc04655af1531b324a7d70ccdd0799707  session-starters/02_data_ops_session.md
1aed1b9545def6d8bbca2b40e09dfd88a9960d854ae71f5e6f2c062a92e2df4d  session-starters/03_analysis_selection_session.md
5a9d934e852acf72c2dc2cff17348d485bc1e68d05db7ccf8e7800d8b9c7ac62  session-starters/04_backtest_strategy_session.md
31ee8325a4c667a74783d99f08f159aca9ee6206ee409c51b06bd692514fe5d9  session-starters/05_code_audit_fix_session.md
412bceed218e1cfa79981f4fdcab5a20ccc249dc5dfa54c5592b282f78b784ea  session-starters/06_cloud_adjudicator_session.md
a93ff45cd2e425dc28eb40fc16b82bd230117cb477c6d03cb227b2437e6f8afa  CLAUDE_HANDOFF_kabutan_quality_gates_spec.md
aa79ee4f717e3c9017c3640bef20bfa1cf8960a1a2463c5b2009e55a74124255  CLAUDE_HANDOFF_phase2c1_snapshot_spec.md
```

> 注: `incoming/` は取込ミラー（gitignore）。上記は正本ツリー（`ai-business-radar/radar-ops/`）配下の実体に対する照合値。

## §8 現行タスクの再構成起点（as_of 2026-07-10）
- 完了/運用: G0・G1・0-3・DT-1a・education（配信/採点自動一本化）・報告配送・ISSUE_MAP・二重採点是正（ROADMAP §1）。
- 仕様待ち: M0 v2（SOURCE_CONTRACT 裁定確認・FRED キー）/ Phase 2c（各節 SPEC）。
- 順序解放（月次ゲート経由）: DT-1b→c。
- 本バッチの司令塔側 TODO: §7 照合 → `incoming/` 配備 → `CONFIRM_batch_revision_v2` で受領報告 → 月次投入ゲート初回記録 `CONFIRM_intake_202607`。

## §9 変更履歴
- v1（`75fceeac…`）: G0/G1 世代の目次・§7 8ファイル配備。
- v2（本書・2026-07-10）: 正本群を ROLES/ROADMAP v2・判断記録レーン・月次投入ゲート・改訂 session-starters(00–06) に更新。§7 を全13ファイルの sha256 マニフェストに刷新。
- v2 追補（同日）: kabutan 品質ゲート SPEC（Q11 前倒し発行）を §2/§7 に追加（計14ファイル）。実装時に `CAPABILITY_MANIFEST.md` を追加予定（ゲートC）。
- v2 追補2（2026-07-11）: Phase 2c-1 snapshot SPEC を §2/§7 に追加（計15ファイル・月次投入ゲート §5 の振替条項発動 = 当月投入枠を M0 から 2c-1 へ）。
- v2 追補3（2026-07-11）: §7 冒頭の件数誤記を訂正（「全13ファイル」のまま15件掲載していた = Codex F3 指摘・factual_correction）。照合対象の定義（manifest 15 + INDEX 自身 = 16件）と INDEX 自身 sha の搬送方法、session-starters の照合パス（incoming/ 配下）を明文化。
