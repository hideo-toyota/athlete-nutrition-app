# ROLES_current.md — 役割正本 **v2**

- doc-id: `ROLES_current`
- version: **v2**（v1=2026-07-07 採用 `f84a2b41…aef0`。本 v2 で改版。バッチ改版v2の一部）
- as_of: 2026-07-10
- writer: クラウド裁定者（cloud adjudicator）
- 位置: `ai-business-radar/radar-ops/ROLES_current.md`（正本）
- 上位規約: `ANALYSIS_QUALITY_RULES.md`（矛盾時はそちらが優先）
- v1→v2 の要旨: (a) education 採点の**自動レーン一本化**を正式化（司令塔の手動採点を停止）/ (b) 0-3 watchlist 書き手宣言**失効**を反映（権限=司令塔へ復帰）/ (c) `dialogue_responder.py` オーナー権限編集の**追認**/ (d) 二重司令塔・二重採点の恒久ルール化 / (e) **判断記録レーン**と**月次投入ゲート**の役割行を新設 / (f) writer フィールド・署名の必須化を再掲。

---

## §1 役割表（窓口・権限・入出力）

| 役割 | 実体 | git 書込 | 入力 | 出力（接頭辞） |
|---|---|---|---|---|
| **司令塔 / commander** | ターミナル版 Claude Code（mac/live・既定の書き手） | 可（既定の書き手・単独コミット） | オーナーが貼る **URL+sha256** の裁定 | 確認依頼MD `CONFIRM_` / `STATUS_` |
| **実行役 / evening executor（My Radar）** | ターミナル版 Claude Code（別セッション）または headless | 不可（`outputs/`・`queue/` 等 非追跡のみ） | 端末プロンプト+`radar-ops/` 手順書 | queue/outbox・heartbeat・`SELF_ROLE_`（開示時） |
| **第2監査役 / second auditor** | デスクトップ版 Claude Code | 不可 | オーナー/裁定者経由 | **所見（findings）のみ**・実行指示チャネルなし |
| **自動レーン群 / automated lanes** | LaunchAgent・headless（下表§1b） | 恒久不可（`outputs/` 等 非追跡のみ） | launchd スケジュール・チャンネル検知 | 観測・生成・Discord webhook |
| **Codex 実装調整役 / implementation** | Codex デスクトップ | 条件付き可（**書き手宣言下のみ**・§3） | オーナー直・ロードマップURL | 実装・テスト・`CODEX_` 接頭辞の記録 |
| **クラウド裁定者 / cloud adjudicator** | 本セッション（クラウド） | 正本（radar-ops 統治文書）への発行 | オーナー経由の状況・確認依頼MD | 裁定 `CLAUDE_HANDOFF_`・正本改版（ROLES/INDEX/ROADMAP） |

### §1b 自動レーン群の内訳（LaunchAgent 実体）
| レーン | LaunchAgent | スケジュール | 出力先 |
|---|---|---|---|
| 株探観測 | `com.radar.kabutan-analysis` | 平日 09:27/12:47/14:52/17:32 + 土 10:41(calibration・LLM不使用) | `.discord_webhook_kabutan` |
| 夜間分析(evening) | `com.radar.evening-analysis` | 平日 22:30（単独担当・旧 session-cron e9e78b20 は失効） | 夜間ch |
| NewsPicks 深掘り | `com.radar.newspicks-deepdive` | 人間起点トリガー | worker-output ch |
| 日経深読み | `com.radar.nikkei-*` | 人間起点のみ（cron化/本文保存/逐語転載 禁止） | `.discord_webhook_nikkei` |
| education 配信 | `education_daily`（19:00 JST） | 毎日 | 教育ch（公開部のみ） |
| **education 採点** | `com.radar.education-grader` | 3分毎 | 教育ch + `education_ledger.jsonl`（**採点はここに一本化**） |
| 対話自動応答 | `dialogue_responder`（launchd） | 定期 | #対話（オーナー投稿を分析・#5246名義） |
| 米国地合い | `com.radar.us-context` | 平日 07:00（M0 v2 契約確認後に再load） | `data/derived/market_context/` |
| orchestrator 自動分析 | `orchestrator_*` | 定期 | `radar-ops/reports/`（`CODEX_AUTO_ANALYSIS_`） |

## §2 規約

### §2.1 単一書き手（single-writer）
- 同時に生きる**実装セッションは1つ**（v1 §4-4 不変）。コア/tests への書き込みは、司令塔の既定権限か、明示の**書き手宣言**を持つセッションに限る。
- パス領域分担: 各コミットは `git diff --cached --stat` で他レーン巻き込みゼロを確認する。

### §2.2 接頭辞規約
- `CLAUDE_HANDOFF_` = **裁定者専用**（仕様・順序・統治の発行）。
- 司令塔 = `CONFIRM_` / `STATUS_`。
- `SELF_ROLE_` = 役割開示（任意セッション・オーナー明示指示時）。
- `CODEX_` = Codex 管理（他レーンは不介入）。
- `VERIFY_` = 検証役レポート。

### §2.3 署名・writer フィールド（必須）
- **全コミット末尾**に `[writer: <role>]`（例 `[writer: commander]` / `[writer: adjudicator]` / `[writer: codex/<task>]`）。
- **台帳・journal の全書込行**に `writer` フィールドを必須化（grader=`writer:"education_grader"`、既存 `grader:"education_grader_llm"` キーは後方互換で維持。daily 配信/failed=`writer:"education_daily"`）。

### §2.4 入力の正規形式
- 裁定入力の正規形式は **URL+sha256**。オーナー転記（hash 無し）で運用する場合は**形式逸脱として記録**し、内容が確認依頼への回答であることを確かめてから実行する。

## §3 書き手宣言の現在状態
| 対象 | 状態 | 備考 |
|---|---|---|
| 0-3 watchlist（`jquants_rest_client.py`＋test） | **失効**（2026-07-07 クローズ `a9be5a0`→条件付き→確定） | 書き手権限は**司令塔へ復帰**。以後、当該2ファイルは宣言なしで触らない |
| `scripts/automation/dialogue_responder.py` の深掘りトリガー編集 | **追認（v2）** | オーナーが端末で明示権限付与のうえレーン担当が編集（`SELF_ROLE_deviation_20260708`）。規律条項不変・py_compile/トリガー6ケース PASS を確認済 → **v2 で追認**。以後の同ファイル変更は司令塔ドメインに復帰し、宣言なしで行わない |
| 現行のオープン宣言 | **なし** | 新規実装は裁定 GO 後・書き手宣言のうえで |

## §4 二重化の恒久ルール（v2 新設・二重司令塔/二重採点の裁定を反映）
1. **education 採点は自動レーン `education_grader` に一本化**。司令塔・他セッションは教育chを**手動採点しない**（旧世代 da17036a の手動採点は `void_duplicate` で是正済み）。
2. **窓口分界**: #対話（`dialogue_responder` 自動）と DM（司令塔が手動）を分ける。同一依頼が両経路に来た場合は**先着一本**・二重応答しない。
3. **grader 著者/透かしゲート**を正とする（`author.id==OWNER_ID` かつ非bot / last_id 単調増加）。bot 名義・旧投稿は機構的に除外される。
4. 台帳の矛盾行・重複行は**削除しない**（append-only）。**訂正行**（void_duplicate / 正典再掲）で是正し、集計は void_* を除外する（`_ledger_rows` は (date, serial) キー化・正典行フィルタ）。

## §5 役割混線の予防（自己申告の常設化）
- 「Codex 司令塔」呼称は使わない（Codex 側は「実装調整役」）。実装と独立監査を兼ねる表現をしない。
- 第2監査役の所見は **findings** として扱い、オーナー/裁定者/INDEX 経由で実装指示化する（指示チャネルの二重化を避ける）。
- git commit metadata だけでは AI セッション帰属は判別不能 → 帰属はコミット署名（§2.3）と報告MDで担保する。

## §6 変更履歴
- v1（`f84a2b41…aef0`）: 初版・役割確定・接頭辞/署名規約。
- v2（本書・2026-07-10）: §4 二重化恒久ルール新設、§3 に 0-3 失効・dialogue_responder 追認を反映、§1b に自動レーン内訳を明記、判断記録レーン/月次投入ゲートを ROADMAP/HANDOFF と接続。
