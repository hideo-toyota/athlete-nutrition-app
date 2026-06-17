# EARNINGS_CYCLE_VALUE_AUDIT_PLAN — Phase A 実装計画(設計のみ・コード前)

> 正は EARNINGS_CYCLE_VALUE_AUDIT_SPEC.md(v2.1)。上位は DESIGN_PRINCIPLES / SPEC / CLAIMS / CLAUDE /
> DATA_LAYER_SPEC / LICENSE_MATRIX / TARGET_CHECK_SPEC。**この PLAN は SPEC の契約を一字一句満たす手順書**。
> 起草: planner役 / 承認: 人間ゲート(未承認)。**本書はコードを含まない。**
> 方針: **stdlib のみ・純加法・ファイル=真実・未来不参照(available_at<=asof)・宣言的設定**。
> Phase A スコープ: **ネット無し / 手入力 snapshot(`--from-file`)/ 対DCA=UNKNOWN**。B/C は ToS 未充足で NO-GO。

---

## 0. ゴールと非ゴール(Phase A)
- **ゴール**: 手入力 snapshot で `value-audit register → score → review` の**閉ループ**をオフラインで回す。
  割安“仮説”を反証可能に事前固定し、次決算サイクルで**事後検証**(年率10%ハードル・構造化一致率)。
- **非ゴール**: 銘柄取得 / sync / 同業相対(universe)/ 進捗率の自動取得 / 対DCA 算出 / 買い候補・推奨・予測。
- **既存不変**: `mirror/check/log/score/review/target-check` の CLI/I/O/挙動は変えない(純加法)。

---

## 1. モジュール構成(新規ファイルのみ・純加法)
```
ai-business-radar/
├── radar/
│   ├── value_audit.py        # 【新】純計算: Measured / operator真理表 / サイクル数理 / 集計。I/O無し・決定論
│   ├── value_store.py        # 【新】入力検証 + 追記専用JSONL I/O + ticker検証/safe slug/path-safety
│   ├── report.py             # 【改・追記】render_value_audit() / render_value_review() を追加
│   ├── config.py             # 【改・追記】value_audit ブロックの検証を追加(存在時のみ・既存不変)
│   └── __main__.py           # 【改・追記】`value-audit {register|score|review}` 配線 + dispatch
├── config.json               # 【改・追記】"value_audit" ブロック(§9.0 初期値)
├── journal/
│   ├── value_thesis.jsonl    # 【新・個人データ】仮説イベント(追記専用)→ .gitignore
│   ├── value_outcomes.jsonl  # 【新・個人データ】採点イベント(追記専用)→ .gitignore
│   ├── value_thesis_input.example.json   # 【新・追跡】register --from-file の手入力サンプル
│   └── value_thesis.example.jsonl        # 【新・追跡】保存形式のサンプル(1〜2件)
├── outputs/value_audit/<slug>.md         # 【生成】個別レポート(4点)
├── outputs/value_audit_review.md         # 【生成】較正レポート(固定表示順)
└── tests/test_value_audit.py             # 【新】オフラインテスト(SPEC §8)
```
- **保存先は `journal/` 配下**(SPEC §2.4)。既存 `decision_log.jsonl` は ROOT だが、value 系は journal/ に集約。
- `.gitignore` に **`journal/value_thesis.jsonl` / `journal/value_outcomes.jsonl`** を追加(実データ非追跡)。
  追跡するのは `*.example.*` と本 PLAN/SPEC のみ。

---

## 2. モジュール境界と関数契約(=インターフェイス / SPEC §2 に一致)

| モジュール | 責務 | 主な関数(契約) | 純粋性 |
|---|---|---|---|
| `value_audit` | 純計算 | `evaluate_condition(cond, actual) -> matched(bool\|None)`(§2.6.1 真理表) / `raw_return(p0,p1)` / `annualize(raw, days, cfg) -> Measured` / `cycle_days(start,end)` / `aggregate(outcomes,theses,cfg) -> ReviewStats` | **純粋・決定論・I/O無し** |
| `value_store` | 検証 + 永続化 + 安全 | `validate_ticker(s) -> slug` / `safe_output_path(slug) -> Path` / `load_thesis_input(path) -> dict`(必須項目・禁止項目・anti_thesis ゲート) / `append_thesis(d) -> thesis_id` / `append_outcome(d)` / `read_theses()` / `read_outcomes()`(壊れ行で行番号付き停止) / `active_theses()`(amends/supersedes 解決) | I/Oのみ・追記専用 |
| `report` | 契約準拠出力 | `render_value_audit(thesis) -> md`(4点・不確実性先頭・免責) / `render_value_review(stats) -> md`(固定表示順) | 純粋 |
| `__main__` | CLI | `cmd_value_audit(args)`(register/score/review に分岐) | 薄い |

- `Measured` = `{value, status, unit, note}`(SPEC §2.0)。`status:UNKNOWN` のとき `value=None`(0/false にしない)。
- `ReviewStats` = `{n_thesis, n_scored, n_unknown, falsification_count, risk{...}, checklist_match_rate, hit_10pct, hit_dca}`。
  hit_dca は Phase A では `UNKNOWN`(分母0なので率を出さない)。

---

## 3. フェーズ(垂直スライス。各スライス末に py_compile + unittest + 該当コマンド + 既存非回帰 + Codex ゲート)

> register→score→review は依存順。**A-1(純計算)を先にテストまで固めてから** A-2 以降を積む(数理のブレを先に潰す)。

### A-0 — 足場・契約・安全(コード基盤)
- `config.json` に `value_audit` ブロック追加(§9.0 初期値: `annual_hurdle_pct:10` / `hurdle_basis:"pre_tax"` /
  `annualization_day_base:365` / `min_cycle_days:45` / `max_cycle_days:200` / `benchmark_index_ref:null` /
  `min_metrics_for_audit:3`)。
- `config.py`:**value_audit ブロックは存在時のみ検証**(型・範囲)。**未存在でも既存コマンドは不変**(非回帰の要)。
- `value_store.validate_ticker` / `safe_output_path`:**`^[A-Za-z0-9._-]{1,15}$`**・`/ \ .. 空白 制御 全角 空` 拒否、
  slug=ticker、解決後パスが `outputs/value_audit/` 配下である事を確認(脱出拒否)。
- `.gitignore` 追記。`journal/*.example.*` を作成。
- **DoD**: 不正 ticker/パスは `SystemExit`。value_audit ブロック不正は明示失敗。**既存6コマンド非回帰**。
- **検証**: `python3 -m radar mirror` / `check` / `target-check` / `data-check --offline` が従来通り。

### A-1 — `value_audit.py`(純計算)★最初に固める
- `evaluate_condition`:**§2.6.1 真理表をそのまま実装**。`tolerance` 既定 0.0、`in_range/out_of_range` は `[lo,hi]`、
  **型不整合は例外(呼び出し側で register 拒否/score 停止に変換)**、`actual` が非数値/nan/inf/UNKNOWN は `None`(分母外)。
- `raw_return` / `cycle_days` / `annualize`:`annualize` は `cycle_days` が `[min,max]` 外なら **Measured(UNKNOWN, note=範囲外)**。
  範囲内のみ `(1+raw)**(day_base/days)-1` を CALCULATION で返す。`raw_return` は常に CALCULATION。
- `aggregate`:**分母に入れる status = FACT/CALCULATION のみ**(§2.0)。UNKNOWN/INFERENCE/ASSUMPTION を率に数えない。
- **DoD**: 真理表の境界/tolerance、年率ゲート、UNKNOWN を 0/false にしない、を**単体テストで網羅**。
- **検証**: `python3 -m unittest tests.test_value_audit`(この段で数理テストが緑)。

### A-2 — `value-audit register`(仮説の事前固定)
- `value_store.load_thesis_input`:**必須項目**(`cheapness_reason` / `anti_thesis` / `falsification` /
  `next_earnings_checklist`)欠落で拒否。**anti_thesis 品質ゲート**(3項目空不可・定型文/プレースホルダ拒否)。
  **禁止フィールド**(`buy_intent`/`entry_plan`/`target_price`/`position_size`/`rank`/`score` 等)があれば拒否。
  `position_intent ∈ {paper_only, existing_holding_review}` のみ。構造化条件(§2.6)の型検証。
- PIT:`snapshot_at`・各 valuation の `available_at <= asof` を確認(未来混入は拒否)。手入力値は `status:ASSUMPTION` 既定。
- `append_thesis`:`event_id`/`thesis_id`/`schema_version`/`created_at`/`asof`/`source:"manual"` を付与し追記。
- `report.render_value_audit`:**4点**(検証対象/必要条件/反証条件/次決算で見る項目)+ 不確実性先頭 +
  「これは購入意思ではない/紙上の仮説」+ 免責。`outputs/value_audit/<slug>.md`。
- **DoD**: 必須欠落・禁止フィールド・未来データ・不正 ticker は拒否。出力に**推奨/予測/買い候補語が無い**。
- **検証**: サンプル `--from-file` で md 生成 + thesis 追記。`register --help` が落ちない(**help 文字列の `%` は `%%`**・B4 の教訓)。

### A-3 — `value-audit score`(事後採点・凍結)
- `active_theses`:`amends`/`supersedes` を解決し**有効版**を対象に。**`next_earnings_available_at <= asof` のみ採点**、未到来は `pending`。
- 採点:`raw_return`(entry_rule=翌取引日終値・対称)→ `annualize`(範囲ゲート)→ `vs_target_10pct`(annualized が
  CALCULATION のときのみ判定)。**`benchmark`/`excess_vs_dca`/`beat_dca` は null+UNKNOWN(対DCA 未算出)**。
  `checklist_result`/`falsification_triggered` は **§2.6.1 真理表**で機械判定。`max_drawdown_pct` は UNKNOWN(日足無し)。
- `append_outcome`:`event_id(=outcome_id)`/`thesis_id`/`schema_version`/`scored_at`/`asof`/`source` を付与し追記。
- **凍結**:閾値・operator は snapshot 時の構造化条件を使用。**同一 asof で再実行 → 既存 outcome は不変**(訂正は amends 追記)。
- **DoD**: 未到来は採点しない。UNKNOWN を負け/不一致にしない。対DCA は UNKNOWN。**二度実行で同一**。
- **検証**: fixture で pending/採点済みの分岐、真理表どおりの matched、決定性。

### A-4 — `value-audit review`(較正・固定表示順)
- `aggregate` → `render_value_review`:**表示順固定**(§4.1)
  1. サンプル不足/UNKNOWN/欠損 → 2. 反証発火件数 → 3. 規律/集中度/最大DD → 4. checklist 一致率
  → 5. 対10% hit率 → 6. 対DCA hit率。**hit率を先頭に出さない。**
- **Phase A は対DCA hit率を出さない**(分母0=UNKNOWN)。サンプル<20 は「統計的結論は保留」。
  cheapness_reason と **anti_thesis の両方**を表示(両論併記)。
- **DoD**: 表示順が固定・hit率が先頭でない・UNKNOWN を分母に入れない・対DCA は UNKNOWN 表示。
- **検証**: fixture(数件)で順序・分母・保留表示を確認。

---

## 4. config 例(§9.0 初期値・宣言的)
```jsonc
"value_audit": {
  "annual_hurdle_pct": 10, "hurdle_basis": "pre_tax", "annualization_day_base": 365,
  "min_cycle_days": 45, "max_cycle_days": 200, "benchmark_index_ref": null, "min_metrics_for_audit": 3
}
```
- **変更は config 値 + schema_version に残す**(後から黙って書き換えない・再現性)。

---

## 5. 原則充足チェック(planner 自己監査)
| 原則 | 本プランでの担保 |
|---|---|
| 1 最終判断は人間 | 売買案を持たない。register=紙上の仮説。実売買は check→人間→log(別系統) |
| 2 規律破りは記録 | 仮説・反証・反対仮説を事前固定、訂正は amends 追記(原本不変) |
| 3 無知が最大の罪 | 不確実性先頭・欠損=UNKNOWN(0にしない)・対DCA は正直に UNKNOWN・サンプル不足を明示 |
| 4 参謀≠事務員 | cheapness_reason に対し anti_thesis を必須・両論併記 |
| 5 検証する道具 | register→score→review の閉ループ、年率10%/構造化一致率で事後測定 |
| 6 ファイル/宣言/未来不参照 | JSONL 真実・config 駆動・available_at<=asof・二度実行同一・stdlib のみ |

---

## 6. テスト計画(verifier / SPEC §8 と対応)
- **PIT 強制**: `available_at>asof` 混入で拒否/除外。未来価格で採点しない。
- **operator 真理表(§2.6.1)**: 各演算子の境界/tolerance、型不整合で拒否/停止、非数値/nan/inf=UNKNOWN(0にしない)。
- **集計 status(§2.0/§4.1)**: 分母=FACT/CALCULATION のみ。UNKNOWN を負け/不一致に数えない。
- **DCA 未算出**: benchmark/excess/beat_dca が null+UNKNOWN、review で対DCA hit率を出さない。
- **年率換算の極端値**: cycle_days 範囲外 → annualized/vs_target_10pct UNKNOWN、raw_return は出る、別枠。
- **必須/品質ゲート**: cheapness_reason/anti_thesis/falsification/checklist 欠落で拒否。anti_thesis 空・定型文で拒否。
- **買い意思フィールド禁止**: buy_intent 等で拒否。position_intent は許可値のみ。
- **path safety**: `../ / 空 制御 超長` 拒否、出力が outputs/value_audit/ を脱出しない。
- **イベント不変**: amends/supersedes で過去行不変。同一 asof で score 再実行 → 過去 outcome 不変(決定性)。
- **語彙ガード**: 出力に buy_candidate/ランキング/期待リターン順/「買うべき」「おすすめ」「上がる可能性が高い」
  「割安だから買い」が無い(否定免責の文脈は許容)。
- **review 表示順**: UNKNOWN→反証→リスク→一致率→対10%→対DCA、hit率が先頭でない。
- **既存非回帰**: mirror/check/log/score/review/target-check の CLI/I/O 不変(subprocess で --help と実行)。
- **書込スコープ**: 出力は outputs/value_audit/ と journal/value_*.jsonl のみ(data/raw 等を汚さない)。

---

## 7. 実装順・リリース・ゲート
- 順序: **A-0 → A-1(数理をテストまで固める)→ A-2 → A-3 → A-4**。各スライスは独立にコミット可。
- 各スライス完了で `python3 -m py_compile radar/*.py` + `python3 -m unittest -q` + 該当コマンド実行 + 既存非回帰。
- **Codex 監査ゲート**: 全スライス実装後(または A-2 と A-4 完了時)に Codex マルチパス監査
  (金商法 / 行動経済学 / 数理・PIT / 整合)を通してから merge。B4 と同じ運用。
- **注意(B4 の教訓)**: argparse の help 文字列に literal `%` を書かない(必要なら `%%`)。サブコマンド `--help` を必ずテスト。

---

## 8. ブロッカー / 範囲外(Phase A では触れない)
- 対DCA 算出(価格系列が無い・§9.1)、同業相対 universe、進捗率の自動取得、feature 式の確定 → **B/C**。
- J-Quants / EDINET DB 接続・sync・raw 保存 → **LICENSE_MATRIX の ToS 充足まで NO-GO**(A1/sync と同一ゲート)。
- 本 PLAN はコードを含まない。実装着手は人間ゲート承認後。

> ※本書は実装計画であり、投資助言・予測・売買指示・購入意思ではない。コードは本 PLAN と SPEC・上位原則の帰結に限る。
