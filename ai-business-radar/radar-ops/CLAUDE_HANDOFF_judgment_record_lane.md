# CLAUDE_HANDOFF_judgment_record_lane.md — 判断記録レーン 仕様（発効）

- doc-id: `CLAUDE_HANDOFF_judgment_record_lane`
- as_of: 2026-07-10
- writer: クラウド裁定者（cloud adjudicator）
- 位置: `ai-business-radar/radar-ops/CLAUDE_HANDOFF_judgment_record_lane.md`
- 上位規約: `ANALYSIS_QUALITY_RULES.md`（R2 禁止事項・R3 PIT/append-only・R5 論点連動）/ 論点: `ISSUE_MAP.md`
- 状態: **発効（ACTIVE）**。本仕様の受領（sha256 一致）後、司令塔が実装 SPEC を最小単位で受け実装する。

---

## 1. 目的と非目的
- **目的**: value-audit の**判断（読み取りの結論）を append-only で記録**し、後から「何を根拠に、どの論点で、どう判断したか」を検証可能にする。判断の**採点**（後日の答え合わせ）を可能にする土台でもある（ROADMAP 2c-4 の入力）。
- **非目的**: 判断記録は**売買推奨・順位・価格目標ではない**（ANALYSIS_QUALITY_RULES R2）。記録は「注目度/検証優先度」であって買い候補ではない。集計が推奨ランキングに化ける経路を**構造で禁止**する。

## 2. 記録スキーマ（1判断=1行・append-only JSONL）
保存先: `journal/judgment_ledger.jsonl`（gitignore・runtime state・PIT 追記）。

| フィールド | 必須 | 内容 |
|---|---|---|
| `date` | ✓ | 判断の as_of（記録日）。PIT。 |
| `code` | ✓ | 銘柄コード（末尾0ゲート・`^\d{4,5}$` 準拠） |
| `serial` | ✓ | 同日複数判断を区別する連番（(date, serial) が集計キー） |
| `issues` | ✓ | 論点別所見の配列。各要素 `{issue: "I1".."I7", verdict: "FACT|INFERENCE|UNKNOWN", note, source, asof}` |
| `reason_issues` | ✓ | 判断の理由に効いた**論点番号**の配列（例 `["I3","I6"]`） |
| `priority` | ✓ | 検証優先度（`high|med|low`）。**推奨順位ではない**旨をスキーマ note で固定 |
| `writer` | ✓ | 記録主体（ROLES §2.3）。例 `commander` / `judgment_record` |
| `status` | ✓ | `active` / `void_duplicate` / `void_misfire`（是正は削除でなく訂正行） |
| `revises` | 任意 | 訂正対象の (date, serial)。void 時に必須 |

## 3. 不変条件（実装ガード）
1. **7論点網羅**: `issues` は I1〜I7 を欠かさない。データ無しは省略せず `verdict:"UNKNOWN"`（R5）。
2. **推奨禁止ガード**: スキーマに `rank` / `target_price` / `buy|sell` 相当のフィールドを**置かない**。集計出力に順位列を作らない（テストで存在しないことを固定）。
3. **PIT・append-only**: 既存 (date, serial) を上書きしない。是正は `status:"void_*"` + 正典行再掲。
4. **集計の (date, serial) キー化**: `_ledger_rows` 同様、date 単独キーで「最後が勝つ」不可視化を起こさない。void_* は集計から除外。
5. **理由の論点接地**: `reason_issues` の各値は `issues[].issue` に存在すること（宙に浮いた理由を作らない）。

## 4. 出力（人間可読・計器のみ）
- `outputs/judgment/<date>.md`（gitignore）: 銘柄ごとに7節（I1〜I7）+ `reason_issues` + `priority`。**推奨・順位・目標株価を出さない**（R2）。
- 月次ロールアップ `outputs/judgment/monthly_<YYYYMM>.md`: 論点別の UNKNOWN 残率・検証優先度の分布（**銘柄ランキングにしない**）。

## 5. テスト（DoD）
- (a) 7論点欠落行を拒否（UNKNOWN 明記で通過）。
- (b) 禁止フィールド（rank/target_price/buy-sell）が**スキーマにもレンダにも存在しない**ことを固定。
- (c) void_duplicate 訂正行で先行行が集計から除外され、正典行のみ算入。
- (d) 同日複数 serial が (date,serial) キーで全可視。
- (e) `reason_issues` の宙吊り参照を拒否。

## 6. 停止条件
- 判断記録が推奨・順位・目標株価を含み得る形に変わったら**停止**（R2/R6）。
- 単一 asof 読み不一致・偽 OK・正常行巻き込みは停止・差し戻し（R6）。

## 7. 受領後の手順（司令塔）
1. 本仕様 sha256 照合 → `incoming/` 配備。
2. 実装 SPEC（スキーマ実装・集計・レンダ・テスト）を最小単位で受け、単独コミット＋テスト＋`CONFIRM_` 報告。
3. 既存 value-audit 出力形式を壊さない（バイト等価または明示的改善のみ）。
