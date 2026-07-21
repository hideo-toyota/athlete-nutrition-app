# INDEX_current.md — 正本インデックス **v3**

- doc-id: `INDEX_current`
- version: **v3**（v2 sha256 `786cd44cbb2b8abb3b80df3968bbee568acc4d561559233a1808a77e6bea4c4b` を本v3で改版）
- as_of: 2026-07-22
- writer: クラウド裁定者（cloud adjudicator。binding本文のcanonical issuer）
- binding_intake: `956da7d56c6767e4c7b775c438b53cad7419528f`
- binding_baseline_ruling: `6d7edab0e834e310964de6bac5b0a33f9e1832bd`
- canonical_baseline: `86cd36a70f66b8ea7a73a58e9c2ae8b47eb9e0cd`
- supersedes_on_effective: v2 sha256 `786cd44cbb2b8abb3b80df3968bbee568acc4d561559233a1808a77e6bea4c4b`
- 位置: `ai-business-radar/radar-ops/INDEX_current.md`（正本）
- 役割: 正本群の**目次・配備照合(§7)・現行タスクの再構成起点**。新セッションは本書を最初に照合して起動する（session-starters/00）。
- 発効条件: `ANALYSIS_QUALITY_RULES.md` v2と本書v3のbyte-hash付き`CLAUDE_HANDOFF_` binding裁定、ownerによる直接配備またはownerが明示指定したcommander単独writerによる正本配備、配備後bytesに対するクラウド裁定者の`CLAUDE_HANDOFF_` read-back受理が完了した時点で同時発効する。commanderが発行する`CONFIRM_`はdeployment receiptであり、裁定者artifactのprefixではない。draft、intake、binding裁定またはdeployment receiptだけを実装GO・売買承認・発注承認へ読み替えない。

---

## §1 正本群（統治文書）
| doc | 役割 | version |
|---|---|---|
| `ANALYSIS_QUALITY_RULES.md` | 分析品質規約（最上位） | **v2** |
| `ROLES_current.md` | 役割・接頭辞・署名・書き手宣言 | **v2** |
| `ROADMAP_current.md` | 工程・順序・月次投入ゲート | **v2** |
| `ISSUE_MAP.md` | value-audit 7論点 | v1（正本化） |
| `INDEX_current.md` | 本書（目次・配備照合） | **v3** |

## §2 発効レーン仕様（裁定者発行）
| doc | 役割 | 状態 |
|---|---|---|
| `CLAUDE_HANDOFF_judgment_record_lane.md` | 判断記録レーン | 発効 ACTIVE |
| `CLAUDE_HANDOFF_monthly_intake_gate.md` | 月次投入ゲート | 発効 ACTIVE（初回=2026-07） |
| `CLAUDE_HANDOFF_kabutan_quality_gates_spec.md` | kabutan 品質ゲート（Q11・実装GO） | 発行 2026-07-10（同日追補） |
| `CLAUDE_HANDOFF_phase2c1_snapshot_spec.md` | Phase 2c-1 snapshot（実装GO・月次ゲート振替枠） | 発行 2026-07-11 |

## §3 配送経路
- 報告・確認依頼は `radar-ops/reports/` に置き、`scripts/publish_reports.sh`（秘密スキャン必須）でreportsリポ（`equity-radar-reports`）へ配送。
- 裁定文書の受領は `incoming/`（gitignoreの取込ミラー）に配備し§7で照合。
- `OWNER_DECISION_SUPPORT` は、別途発効した専用SPECが指定するオーナー限定経路以外へ配送しない。現行の公開・自動・Discord・教育・headless経路は `EVIDENCE_ONLY` のまま維持する。

## §4 session-starters（改訂配布）
| doc | 対象 |
|---|---|
| `session-starters/00_common_subagent_protocol.md` | 全セッション共通（最初に読む） |
| `session-starters/01_command_center_session.md` | 司令塔 |
| `session-starters/02_data_ops_session.md` | 実行役/データ運用 |
| `session-starters/03_analysis_selection_session.md` | 分析・選定補助 |
| `session-starters/04_backtest_strategy_session.md` | バックテスト・戦略検証 |
| `session-starters/05_code_audit_fix_session.md` | コード監査・修正 |
| `session-starters/06_cloud_adjudicator_session.md` | クラウド裁定者 |

- 本v3発効後、`session-starters/00_common_subagent_protocol.md`に残るFACT/INFERENCE/UNKNOWN三分離および旧R2禁止事項の要約はv1由来のlegacy summaryとして扱い、AQR v2の四分離とR2を優先する。starter実体は本packetで変更せず、将来の別SPEC/write-setで同期する。

## §7 配備照合マニフェスト（sha256）
起動時に各正本のsha256一致を確認する（不一致は着手前に停止・報告）。**照合対象 = 下記manifest 15件 + INDEX自身1件 = 計16件**（INDEX自身の期待sha256は自己参照不能のため、発行カバー/boot指示書が搬送する）。session-startersは`incoming/session-starters/`配下の実体を照合する（通常パスの旧版と混同しない）。

```
acc8557febfaab832dc25fb6dadc2ca1ee3910f933b4bd51cd335495cd6169a7  ANALYSIS_QUALITY_RULES.md
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

> 注: `incoming/`は取込ミラー（gitignore）。上記は正本ツリー（`ai-business-radar/radar-ops/`）配下の実体に対する照合値。

## §8 現行タスクの再構成起点（as_of 2026-07-22）
- 経済目的: オーナー資本の継続性を守りつつ、全適用cost控除後の利益と事前登録benchmark超過を探索・検証する。
- 出力既定: 全レーン `EVIDENCE_ONLY`。`OWNER_DECISION_SUPPORT` は、オーナーが事前登録した決定論ルールの `CALCULATION` 出力と、オーナー自身の判断記録・V2〜V4 paper scoringに限定する。Claude裁量の個別化された銘柄候補、LONG/SHORT指示、比較順位、entry/exit水準、価格レンジ、position-size案は禁止。
- 証拠状態: `alpha_status=NOT_PROVEN`、`investable_alpha=NOT_PROVEN`、現行V5 item=0。AQR v2またはINDEX v3をalpha証明、実装GO、売買承認、POST承認または発注承認へ読み替えない。
- Baseline: VL-1 baselineはbinding裁定により`86cd36a70f66b8ea7a73a58e9c2ae8b47eb9e0cd`へ前進。write-set不変・実装GOではなく、packet適用時にtracked/untracked再衝突チェックを要する。
- HOLD非干渉: managed deploymentおよびR-C2の既存記録・状態を変更しない。R-C2=`PARTIAL`、Candidate B=`HOLD (0/96)`、Candidate E=`EXECUTION NO-GO`、FA-1/TA-1=`HOLD`を維持し、新規managed/admin操作、exact2、F4、pilot、recompute、promotion、POST、LaunchAgent/launchctl、broker/order routingその他未発行GOは`NONE`を維持する。
- 正本移行順序: draft packet → 裁定者のbyte-hash付き`CLAUDE_HANDOFF_` binding ruling → owner直接またはowner指定commander単独writerによるAQR v2 + INDEX v3正本配備（commander経路は`CONFIRM_` deployment receipt）→ 裁定者の`CLAUDE_HANDOFF_` read-back受理。canonicalコード、validator、tests、data、outputs、POST、LaunchAgent/launchctl、pilot、recompute、promotion、broker、発注、資金利用は別SPEC・別GO。
- 既存の完了/運用、仕様待ち、月次投入ゲートおよび各レーンSPECの状態は本v3だけでは変更しない。

## §9 変更履歴
- v1（`75fceeac…`）: G0/G1世代の目次・§7 8ファイル配備。
- v2（2026-07-10）: 正本群をROLES/ROADMAP v2・判断記録レーン・月次投入ゲート・改訂session-starters(00–06)に更新。§7を全13ファイルのsha256マニフェストに刷新。
- v2追補（2026-07-10）: kabutan品質ゲートSPEC（Q11前倒し発行）を§2/§7に追加（計14ファイル）。
- v2追補2（2026-07-11）: Phase 2c-1 snapshot SPECを§2/§7に追加（計15ファイル・月次投入ゲート§5の振替条項発動）。
- v2追補3（2026-07-11）: §7冒頭の件数誤記を訂正。照合対象をmanifest 15 + INDEX自身 = 16件とし、INDEX自身shaの搬送方法とsession-starters照合パスを明文化。
- v3（2026-07-22）: `ANALYSIS_QUALITY_RULES.md` v2のhashへ更新。利益目的、EVIDENCE_ONLY既定、C-1 generator分離、V0〜V5、`alpha_status=NOT_PROVEN`、VL-1 baseline `86cd36a7`および既存HOLD非干渉を再構成起点へ明記。INDEX自身のhashはpacket manifestで搬送する。
