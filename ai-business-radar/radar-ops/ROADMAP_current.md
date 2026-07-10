# ROADMAP_current.md — 工程・順序正本 **v2**

- doc-id: `ROADMAP_current`
- version: **v2**（バッチ改版v2）
- as_of: 2026-07-10
- writer: クラウド裁定者（cloud adjudicator）
- 位置: `ai-business-radar/radar-ops/ROADMAP_current.md`（正本）
- 上位規約: `ANALYSIS_QUALITY_RULES.md` / 役割: `ROLES_current.md` / 論点: `ISSUE_MAP.md`
- 原則: 順序は裁定者が裁く。**推測で前提を作らない**・SPEC 無しの先行実装をしない・**新規着手は月次投入ゲートを通す**（§M）。DoD 接地でのみ「完了」と書く。

---

## §0 ステータス凡例
`CLOSED`=DoD 全項目クローズ / `ACCEPTED`=受理・運用フェーズ / `IN_SPEC`=仕様待ち（実装停止）/ `BLOCKED`=前提未達で着手禁止 / `DORMANT`=休眠孤立レーン（不介入）。

## §1 完了・運用中
| 工程 | 状態 | 根拠 |
|---|---|---|
| **G0 / Phase 0**（0-1 是正・0-4 education 空投稿修正・§7配備・D0-R） | **CLOSED** | `CONFIRM_g0_phase0_20260707`。389件テストOK |
| **0-3 watchlist V2 移行**（R0限定） | **CLOSED（確定）** | `5da453d`＋独立検証PASS＋空codeガード `fe62a45` 再検証PASS。書き手宣言失効→権限=司令塔 |
| **G1 残務**（kabutan launchd / evening 単独化 / トリアージ / EDINET / 二重採点是正） | **CLOSED** | `CONFIRM_g1_residuals_20260709`＋バッチ第1便 accept §2。465件テストOK |
| **DT-1a**（決算カレンダー・JPX 実装＋J-Quants 第2ソース化） | **ACCEPTED** | `b992387` 受理。J-Quants earnings-calendar 200 でクロスチェック源に |
| **daily-education 配信** | **ACCEPTED（運用）** | 19:00 JST 自動。DoD 全クローズ `CONFIRM_education_dod_close_20260706` |
| **education 採点** | **ACCEPTED（自動一本化）** | `education_grader` へ一本化（ROLES v2 §4）。手動採点は停止 |
| **報告配送自動化** | **ACCEPTED** | `publish_reports.sh`・初回33件 push `1e9051f`。以後 reports/ へ配送 |
| **ISSUE_MAP v1 配備** | **ACCEPTED** | `205fe01`。value-audit 7論点・7節出力を採用 |
| **§7-4 二重行/date衝突 是正**（accept §2） | **CLOSED** | grader二重行の正典指定・(date,serial)キー化・void訂正 |

## §2 仕様待ち・実装停止（IN_SPEC）
| 工程 | 状態 | 待ち |
|---|---|---|
| **米国地合い M0 v2** | **IN_SPEC** | v1 破棄（LaunchAgent unload 済）。`SOURCE_CONTRACT_us_context_m0.md` 提出済 → **裁定者の契約確認(実装GO)待ち**。FRED_API_KEY 記入待ち（オーナー）。当夜間に合う系列は NK225F のみ・SOX/FX は UNKNOWN 開始 |
| **Phase 2c 読み取り層の整合性** | **IN_SPEC** | 実装順採用済（`CONFIRM_phase2c_adoption_20260710`）。**2c 各節の SPEC 発行待ち**。順: 2c-1 snapshot → 2c-2 readiness → 2c-3 CA隔離 → （TOPIX/33業種 index 取得を先行）→ 2c-4 判断採点 |

## §3 着手禁止（BLOCKED）
| 工程 | 状態 | 解除条件 |
|---|---|---|
| **DT-1b/c**（信用・空売り取得の本実装） | **BLOCKED→順序解放待ち** | D0-R で経路確定（JPX スクレイピングではなく J-Quants V2 `/markets/margin-interest`・`/markets/short-*` 200）。**DT-1c は G1 通過を待って着手可となったが、着手は月次投入ゲート（§M）を通す**。DT-1b から順に SPEC 発行 |

## §4 休眠・不介入（DORMANT）
| 対象 | 状態 |
|---|---|
| us_market / us_evidence（NVDA/TSLA PIT evidence・テスト4件済） | **DORMANT**（取得実行ゼロ・接続ゼロ・不介入。M0 とは別物） |
| sector_analyst_spec（仕様提案のみ・実装皆無・作成主体UNKNOWN） | **DORMANT**（接頭辞違反は記録済・不介入） |
| CODEX_ 接頭辞ファイル（実数5件） | **不介入**（Codex 管理） |

## §5 新設レーン（バッチ改版v2で発効）
| レーン | 状態 | 仕様 |
|---|---|---|
| **判断記録レーン（judgment-record lane）** | **発効（ACTIVE）** | `CLAUDE_HANDOFF_judgment_record_lane.md`。value-audit の判断を append-only で記録・理由は ISSUE_MAP 論点番号（I1〜I7）・PIT・推奨に化けない構造 |
| **月次投入ゲート（monthly intake gate）** | **発効（ACTIVE）** | `CLAUDE_HANDOFF_monthly_intake_gate.md`。新規工程・新規対象の着手を月次の裁定ゲートに集約（§M） |

## §M 月次投入ゲートと進行規律
- **新規着手は月次投入ゲートを通す**。ゲート外の割込みは「継続観測」「DoD クローズ」「裁定済みの実装」に限る。
- 進行は次順で裁く: **前工程 DoD クローズ → SPEC 発行 → 書き手宣言 → 実装＋テスト → 報告MD → 受理**。
- 継続観測（ゲート不要）: FRED/Cboe 着時刻窓の実測、kabutan 実弾（09:27 morning・土 calibration）、EDINET ローリング再取得（400/日）。

## §6 直近の待機事項（as_of 2026-07-10）
1. M0 v2: SOURCE_CONTRACT の裁定者確認（GO/修正）・FRED_API_KEY 記入。
2. Phase 2c: 2c-1/2c-2 と TOPIX/33業種 index 取得の小仕様発行。
3. 継続観測の結果反映（着時刻窓を初週で狭める）。
4. 本バッチ改版（ROLES/INDEX/ROADMAP v2・判断記録レーン・月次投入ゲート・session-starters）の**司令塔側受領・配備照合**。

## §7 変更履歴
- v1: G0〜G1 主体の工程表。
- v2（本書・2026-07-10）: G1 CLOSED 反映、M0 を v2/IN_SPEC 化、Phase 2c を工程化、DT-1b/c を順序解放（月次ゲート経由）、判断記録レーン・月次投入ゲートを新設発効。
