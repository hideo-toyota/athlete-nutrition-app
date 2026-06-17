# EARNINGS_CYCLE_VALUE_AUDIT_SPEC — 「決算 to 決算 value audit」契約(設計のみ・実装前)

> 設計のみ。コードはこの契約の帰結。正は DESIGN_PRINCIPLES.md / SPEC.md / CLAIMS.md / CLAUDE.md /
> DATA_LAYER_SPEC.md / LICENSE_MATRIX.md / TARGET_CHECK_SPEC.md。
> これは **割安“仮説”を、決算から決算までの1サイクルで検証する道具**。
> **買い候補を作らない・銘柄を推奨しない・将来を予測しない。** research_item / evidence / score の系譜。
> v2(2026-06-15): 設計レビュー反映(DCA UNKNOWN 構造化 / checklist 構造化 / position_intent /
> ID・イベントソース確定 / path safety / 年率換算の極端値対策 / anti_thesis 必須 / review 表示順)。

---

## 0. 目的 / 非目的

- **目的**: 「この銘柄は割安だ」という**自分の仮説を、反証可能な形で事前固定**し、
  決算発表(available_at)で固定した snapshot から **次の決算 available_at までを1サイクル**として
  事後に検証する。検証軸は「年率10%換算(事後測定)」と「DCAインデックス(算出可能な場合)」。**過程 > 結果**(原則5)。
- **非目的(禁止)**: 銘柄ランキング / 期待リターン順 / `buy_candidate` / 「割安だから買い」 /
  「上がる可能性が高い」 / 売買推奨 / 利益保証 / 将来予測の断定(UNSAFE)。
- **結論の出し方**: 「買い/見送り」ではなく **「検証対象」「必要条件」「反証条件」「次決算で見る項目」**
  の4点に限定する(§4)。検証は「自分の割安解釈が DCA を上回れるか」を測るためにある(原則5・CLAUDE.md)。

### 0.1 年利10%の位置づけ(致命的に重要)
- 10% は **目標・比較軸(ASSUMPTION / config パラメータ)**。**予測でも保証でもない。**
- 用法は2つだけ:(a) **事後**に「実現リターンを年率換算したものが 10% を超えたか」を測る物差し、
  (b) DCAインデックスと並べる第2の物差し。**「10%が見込める」とは一切書かない。**
- 文面では常に「年率10%換算の**ハードル**を超えたか(事後測定)」と表現。**将来形で書かない。**

---

## 1. 既存原則との関係 / 非回帰

- **純加法的**:新規 CLI(`value-audit …`)とモジュールのみ。既存 `mirror/check/log/score/review/target-check`
  の CLI/I/O/既定挙動は不変(DATA_LAYER §1・D9 を継承)。
- **未来不参照(PIT)**:すべての metric・snapshot は `available_at <= asof` のみ採用(§5)。
- **claim 分類**(CLAIMS.md):財務数値=FACT(出典 docID + as_of)、比率/成長率/年率換算=CALCULATION、
  割安“理由”の分類=INFERENCE、10%ハードル=ASSUMPTION、欠損=UNKNOWN、売買断定/予測=UNSAFE(禁止)。
- **EDINET DB の analysis scores / AI所見は FACT 禁止 → INFERENCE/ASSUMPTION**(DATA_LAYER §12)。
- **discipline gate 前に売買提案を出さない**(CLAUDE.md 鉄の掟)。本機能は**検証専用**で、
  そもそも売買案を出さない。実保有判断は別途 `check` → 人間 → `log`(§7.1)。
- **欠損を 0 扱いしない**:欠損/nan/inf/非数値は当該値 **UNKNOWN 保持**(計算は止めず、その metric を除外/明示)。
- **API仕様・データ欠損を report 層で回避しない**:欠損は feature/source 層で UNKNOWN として表現し、
  report はそれをそのまま正直に出す(穴を埋めない)。

---

## 2. データ構造(=本体)

### 2.0 共通の値表現:`Measured`(status を持つ値)
**数値・判定は裸で持たず、必ず status 付き**で持つ(誤読防止・欠損を 0/false にしない)。
```jsonc
// Measured: 数値や bool を status とともに保持する共通形
{ "value": 12.3 | true | null, "status": "FACT|CALCULATION|INFERENCE|ASSUMPTION|UNKNOWN",
  "unit": "x|%|円|null", "note": "UNKNOWN の理由など(任意)" }
```
- **`status:"UNKNOWN"` のとき `value` は必ず `null`**(0 や false にしない)。
- hit率・一致率などの集計は **`status` が確定値(CALCULATION 等)の要素のみ**を分母にする(§4.1)。

### 2.1 `value_thesis`(検証対象の仮説。research_item の subtype・**買い候補ではない**)
DATA_LAYER §10 の **語彙ロックを継承**(`type:"research_item"` 固定、`buy_candidate` 等の語は禁止)。
```jsonc
{
  "type": "research_item",            // ★固定(buy_candidate 禁止)
  "subtype": "value_audit",           // 本機能の識別
  "schema_version": "2",
  "event_id": "ULID/uuid",            // ★この JSONL 行の一意 id(§2.4)
  "thesis_id": "短縮uuid",            // ★仮説の安定 id(amend されても不変)
  "created_at": "ISO8601(tz付)",      // 記録時刻(監査証跡)
  "asof": "YYYY-MM-DD",               // この記録が前提とした asof(再現性)
  "source": "manual",                 // Phase A=manual。B以降は sync:jquants 等(§2.4)
  "amends": null,                     // 修正時は元 event_id(原本は上書きしない・§2.4)

  // --- 立場の明示(買い意思に見せない・§3 / item3) ---
  "position_intent": "paper_only",    // paper_only | existing_holding_review のみ。既定 paper_only
                                      // ★ buy_intent / entry_plan 等“買い意思”フィールドは禁止
  "discipline_status": "未通過",      // ★固定・必須(検証専用。売買は別途 check)

  // --- entity(Phase A は ticker のみ必須・厳格検証 / §2.5) ---
  "ticker": "7203",                   // ★必須・厳格バリデーション(§2.5)。ファイル名は safe slug
  "securities_code": null, "edinet_code": null, "company_id": null, "isin": null, // 任意(B/C で mapping)
  "company_name": "...", "market": "...", "sector": "...",

  // --- サイクル定義(PIT) ---
  "snapshot_at": "ISO8601(tz付)",     // = 起点決算の available_at(§5)。これより新しいデータは使わない
  "cycle": {
    "start_available_at": "ISO8601",  // = snapshot_at
    "next_earnings_expected": "YYYY-MM-DD",        // earnings-calendar 予定(版を持つ・ASSUMPTION)
    "next_earnings_available_at": "ISO8601|null"   // 確報の available_at。出るまで null(=未採点)
  },

  // --- 割安の“定義”をベクトルで(単独指標で断定しない・§3) ---
  "valuation": {                      // 各 metric は §2.0 Measured(欠損は value:null + status:UNKNOWN)
    "ev_ebit": {}, "fcf_yield": {}, "roic": {}, "net_cash": {},
    "op_margin": {}, "revenue_growth": {}, "op_profit_growth": {},
    "progress_rate": {},              // 会社予想に対する進捗(会社予想の available_at に従う)
    "sector_relative": {}             // 同業相対(universe coverage 依存→不足は UNKNOWN)
  },

  // --- 安い理由(必須・構造劣化か一時要因かを分ける) ---
  "cheapness_reason": {               // ★必須。無ければ register 拒否
    "classification": "temporary_setback | structural_decay | mispricing_hypothesis | unknown",
    "explanation": "なぜ安いと考えるか(自由文)",
    "claim": "INFERENCE",             // 事実からの推論として明示・前提を書く
    "evidence_refs": [ /* provenance / EDINET docID / IR */ ]
  },

  // --- 反対仮説(必須・自己正当化の防止 / item7) ---
  "anti_thesis": {                    // ★必須。無ければ register 拒否
    "why_cheap_may_be_deserved": "安いのが正当かもしれない理由",
    "structural_risk_case": "一時要因ではなく構造劣化かもしれない理由",
    "intensifies_if": "次決算でそのリスクが強まる条件(できれば §2.6 の構造化条件に対応付け)",
    "claim": "INFERENCE"
  },

  // --- 反証条件(必須・事前固定・後知恵防止)= 構造化条件(§2.6) ---
  "falsification": [                  // ★必須・1件以上。無ければ register 拒否
    { "metric": "op_margin", "operator": "<", "threshold": 0.05, "tolerance": 0.0,
      "horizon": "next_earnings", "why": "仮説が壊れる線(自由文・補足)" }
  ],

  // --- 次決算で見る項目(必須・事前固定・構造化)= 構造化条件(§2.6) ---
  "next_earnings_checklist": [        // ★必須・1件以上。snapshot 時点で凍結(後から足さない)
    { "metric": "revenue_growth", "operator": ">=", "threshold": 0.10, "tolerance": 0.01,
      "expectation": "二桁成長の継続(自由文・補足)", "why": "仮説のどこを確かめるか",
      "qualitative_only": false }    // true の項目は一致率の分母に入れない(§4.1)
  ],

  "key_risks": [],                    // 必須
  "entry_rule": "next_trading_close", // §5.3: snapshot_at 翌取引日終値を基準(約定ではない・ASSUMPTION)
  "claim_tags": {},                   // 主張ごとの分類(CLAIMS §各主張)
  "disclaimer": "割安“仮説”の検証対象。買い推奨でも予測でもない。これは購入意思の表明ではない。売買は discipline check + 人間判断が必要。"
}
```
- **並べ替えキーは持たない。** どうしても順序が要る場合のみ `coverage_priority`(網羅度)を使い、
  **魅力度/期待リターン/割安度ランキングは禁止**(DATA_LAYER §10 を継承)。
- **禁止フィールド**:`buy_intent` / `entry_plan` / `target_price` / `position_size` / `recommendation`
  / `rank` / `score`(魅力度) など“買い意思・優劣・推奨”に見えるものは持たない。

### 2.2 `cycle_outcome`(採点結果・追記専用・後知恵禁止)
decision_log と同じ**イベントソース**思想(SPEC §1.5):snapshot を改変せず、結果は別行で追記。
数値・判定は **§2.0 Measured**(DCA・年率換算が未算出なら `value:null + status:UNKNOWN`、false にしない)。
```jsonc
{
  "type": "cycle_outcome", "schema_version": "2",
  "event_id": "ULID/uuid",           // ★この行の一意 id(= outcome_id)
  "outcome_id": "= event_id",        // 別名(参照用)
  "thesis_id": "対応する value_thesis の id",
  "scored_at": "YYYY-MM-DD", "asof": "YYYY-MM-DD", "source": "manual",
  "cycle_days": 0,                    // start→next_earnings available_at の実日数

  // 絶対リターン(価格・PIT)。raw は常に出す。年率換算は範囲外で UNKNOWN(item6)
  "raw_return": { "value": 0.0, "status": "CALCULATION", "unit": "%" },
  "annualized_return": { "value": null, "status": "UNKNOWN", "unit": "%",
    "note": "cycle_days が [min_cycle_days, max_cycle_days] 外のため年率換算は警告/除外" },
  "vs_target_10pct": { "value": null, "status": "UNKNOWN" }, // annualized が確定値のときのみ判定

  // 相対リターン(DCAインデックス・同一窓)。価格系列が無ければ UNKNOWN(item1)
  "benchmark": { "method": "dca_index", "index_ref": "...|null",
    "return": { "value": null, "status": "UNKNOWN", "note": "no_price_series(Phase A)" } },
  "excess_vs_dca": { "value": null, "status": "UNKNOWN" },
  "beat_dca": { "value": null, "status": "UNKNOWN" },        // ★null。false にしない=「負け」と誤読させない

  // リスク
  "max_drawdown_pct": { "value": null, "status": "UNKNOWN" },// 日足が要る→B/C 依存
  "concentration_note": "...",       // mirror の集中度文脈(任意・参考)

  // 再現性(事前仮説と次決算結果の対応)= 構造化判定(§2.6 / item2)
  "checklist_result": [
    { "metric": "revenue_growth", "operator": ">=", "threshold": 0.10, "tolerance": 0.01,
      "actual": { "value": null, "status": "UNKNOWN" }, "matched": null,
      "qualitative_only": false, "evidence_ref": "docID/...", "judge_basis": "構造化比較(operator)" }
  ],
  "falsification_triggered": [        // どの反証条件に触れたか(構造化条件の id/metric)
    { "metric": "op_margin", "operator": "<", "threshold": 0.05, "actual": {"value":0.03,"status":"CALCULATION"} }
  ],
  "cheapness_resolution": "temporary_confirmed | structural_confirmed | undetermined",
  "claim_tags": {}
}
```

### 2.3 `config` 追加(宣言的・コード直書き禁止)
```jsonc
"value_audit": {
  "annual_hurdle_pct": 10,           // ★ハードル(ASSUMPTION)。予測でない
  "hurdle_basis": "pre_tax",         // 🔸未決(§9-2)。post_tax なら target-check の t=0.20315/NISA と整合
  "annualization_day_base": 365,     // 年率換算の基準日数(固定・再現性)
  "min_cycle_days": 45,              // ★これ未満は年率換算を UNKNOWN/warning(短期外れ値対策・item6)🔸値は要決定
  "max_cycle_days": 200,             // ★これ超は同上(決算遅延・特殊サイクル)🔸値は要決定
  "benchmark_index_ref": null,       // DCA 比較に使う指数の“価格系列”。無ければ対DCA=UNKNOWN(item1/§9-1)
  "min_metrics_for_audit": 3         // valuation のうち status が確定値の数がこの数未満なら「評価不能」と明示
}
```

### 2.4 ID / イベントソース / 保存先(Phase A 前に確定 / item4)
- **イベントソース**:すべて**追記専用 JSONL**。1行=1イベント。**過去行は改変・削除しない**(SPEC §1.5・decision_log と同型)。
- **id 規約**:
  - `event_id` … 全イベント行に必須の一意 id(時刻順ソート可能な ULID 推奨。uuid 可)。
  - `thesis_id` … 仮説の安定 id。**amend されても不変**(系譜をたどる主キー)。
  - `outcome_id` … cycle_outcome 行の `event_id` の別名。
- **版・時刻・由来**:全行に `schema_version` / `created_at`(tz付) / `asof` / `source`(Phase A=`manual`)。
- **修正の扱い(原本不変)**:訂正は**新しい行を追記**し、`amends`(=元 event_id)で結ぶ。
  - `amends`:部分修正(同じ thesis_id・新 event_id)。**元行は残す**(後知恵防止)。
  - `supersedes`:仮説の全面差し替え(新 thesis を作り、旧 thesis_id を `supersedes` で参照して以後 inactive)。
  - 採点(score)・較正(review)は **有効版(最新の非 superseded)** を使うが、過去採点は再計算で変えない(§5.4 凍結)。
- **保存先**(`journal/` 配下・decision_log と並置):
  - `journal/value_thesis.jsonl`(個人データ)/ `journal/value_outcomes.jsonl`(個人データ)。
  - **サンプルは別ファイル**:`journal/value_thesis.example.jsonl`(追跡)/ 実データは **gitignore**。
- **gitignore 方針**:`journal/value_thesis.jsonl` と `journal/value_outcomes.jsonl` を `.gitignore` に追加
  (既存 `decision_log.jsonl` と同様)。`*.example.jsonl` と本 SPEC のみ追跡。

### 2.5 entity / ticker / path safety(Phase A の最低限 / item5)
- **ticker 厳格バリデーション(Phase A・必須)**:許可文字のみ(英数・`.` `_` `-`)、長さ上限(例 1–15)、
  **空文字・空白・`/`・`\`・`..`・制御文字を拒否**(SystemExit)。
- **path traversal 禁止**:出力ファイル名は **ticker を safe slug 化**(許可外文字を除去/置換)し、
  `outputs/value_audit/<slug>.md` に限定。**slug が空・`.`/`..` になる入力は拒否**。ディレクトリ脱出を許さない。
- **entity 識別子**:`ticker`(Phase A 主キー)、`securities_code`/`edinet_code`/`company_id`/`isin` は任意。
  **本格的な名寄せは DATA_LAYER §9 の entity mapping と合流(B/C)**。
- **上場廃止 / コード変更 / 社名変更 / コード再割当**:Phase A では解決しない →
  **`entity_status:"unresolved"` 相当の UNKNOWN として扱い、採点は保留/明示**(誤結合しない)。

### 2.6 構造化条件(falsification / checklist 共通スキーマ / item2)
仮説の「期待」と「反証」は**自由文に流さず構造化**し、一致/発火は**機械判定**する。
```jsonc
{ "metric": "op_margin",            // valuation/財務 metric 名(レジストリ語彙)
  "operator": ">= | <= | > | < | == | in_range | out_of_range",
  "threshold": 0.05,                // 数値(in_range は [lo,hi])
  "tolerance": 0.0,                 // 許容誤差(== や境界の揺れ吸収)
  "expectation": "自由文(補足のみ。判定には使わない)",
  "why": "仮説のどこを確かめるか(自由文・補足)",
  "qualitative_only": false }       // true=構造化不能。一致率/hit率の分母に入れない(§4.1)
```
- **score の一致率・発火判定は構造化フィールド(metric/operator/threshold/tolerance/actual)のみから計算**。
  `expectation`/`why` は**判定に使わない**(主観混入の遮断)。
- `actual` が UNKNOWN の項目、`qualitative_only:true` の項目は **一致率の分母から除外**(§4.1)。

---

## 3. 「割安」を曖昧にしない(定義契約)

- **割安は単一指標の判定ではなく、ベクトル + 文脈**で表す。PER/PBR 単独で「割安」と言わない。
- 各 metric は **2つの文脈**で提示(どちらも CALCULATION、coverage 不足は UNKNOWN):
  1. **自己時系列**:過去レンジに対する現在位置(歴史値は参考=ASSUMPTION 寄り、FACT 化しない)。
  2. **同業相対**:universe 内の相対位置(percentile)。**universe coverage が無ければ UNKNOWN**(B/C 依存)。
- **「安い理由」を必須項目**にし(`cheapness_reason`)、必ず
  **一時的悪材料(temporary_setback)/ 構造劣化(structural_decay)/ ミスプライス仮説(mispricing_hypothesis)**
  のいずれかに分類。**分類は INFERENCE**(前提を明示)。**「割安→買い」への飛躍は禁止**。
- **反対仮説を必須**(`anti_thesis`・item7):「安いのは正当かもしれない理由」「構造劣化かもしれない理由」
  「次決算でリスクが強まる条件」を**事前に書く**。これが無ければ register 拒否。
  cheapness_reason の自己正当化(構造劣化を“一時要因”と都合よく解釈)への歯止め。
- **次決算で確認する指標を事前固定**(`next_earnings_checklist`・構造化 §2.6)。snapshot 後に項目を足さない。
- **反証条件を必須**(`falsification`・構造化 §2.6)。「これが起きたら仮説は壊れた」を事前に書く(原則3・4)。

---

## 4. 出力契約(`outputs/value_audit/<slug>.md` / `outputs/value_audit_review.md`)

### 4.0 個別レポート(register)
**4点のみに限定**(これ以外の“結論”を出さない):
1. **検証対象(What we are testing)**:仮説の要旨 + snapshot_at + サイクル定義。先頭に**不確実性**(原則3)。
   `position_intent` を明示し、**「これは購入意思ではない/紙上の仮説」**と冒頭に置く(§7.1)。
2. **必要条件(What must hold)**:仮説が生きるために満たすべき条件(= checklist の事前期待・構造化)。
3. **反証条件(What would break it)**:`falsification` + `anti_thesis`。触れたら仮説棄却。
4. **次決算で見る項目(What to read next)**:metric と「仮説のどこを確かめるか」。
- レポート共通契約(SPEC §1.6)を継承:freshness header / uncertainty-first / two-sided / 断定しない。
- **valuation は claim 分類つき**で表示。欠損は「UNKNOWN(未取得/欠損)」と明示し、**0 で埋めない**。
- 免責:投資助言でない・予測でない・売買指示でない・利益保証でない・**購入意思でない**。

### 4.1 較正レポート(review)— 表示順は固定(ゲーミフィケーション防止 / item8)
**この順で出す。hit率を先頭に出さない。**
1. **サンプル不足 / UNKNOWN / データ欠損**(まず「分かっていないこと」。原則3)。
   サンプル < 20 は「統計的結論は保留」。決算は年≈4回でサンプルが貯まるのに**数年**かかる旨を明記(§9-9)。
2. **反証条件に触れた件数**(falsification 発火)。
3. **規律違反・集中度・最大DD**(リスク。max DD が UNKNOWN ならそう書く)。
4. **checklist 一致率**(構造化フィールドのみ・UNKNOWN/qualitative_only は分母から除外)。
5. **対10%ハードル hit率**(annualized が確定値の outcome のみが分母。年率換算 UNKNOWN/範囲外は除外)。
6. **対DCA hit率**(**benchmark が確定値の outcome のみが分母**。価格系列が無い Phase A は
   「対DCA=UNKNOWN(未算出)」と表示し、**hit率は出さない**)。
- **集計の鉄則**:`status` が確定値の要素だけを分母にする。**UNKNOWN を「負け」「不一致」に数えない**(§2.0)。
- **短期/長期の外れ値**(cycle_days が範囲外)は**別枠**で件数表示し、対10% hit率には混ぜない(item6)。

---

## 5. PIT(ポイントインタイム)ルール(致命・DATA_LAYER §6 を継承)

### 5.1 採用基準
- snapshot 構築・採点は **`available_at <= asof` のデータのみ**。latest は evidence 本文の参考表示のみ可、
  **検証(score)には使わない**。
- `available_at` は **datetime(tz付)**。日付粒度の dataset は「当日終端の時刻」。`asof` が日付のみなら当日末で比較。

### 5.2 dataset 別 available_at(DATA_LAYER §6 の表に従う)
- financials → disclosure_date(無ければ submit_date)。**snapshot_at = 起点決算の available_at**。
- prices(日足)→ 取引日(JST引け後)。会社予想/進捗率 → 公表日(改訂は版を持つ)。
- earnings-calendar(次決算予定)→ 公表日。**予定は ASSUMPTION**、確報 available_at で置換。

### 5.3 約定を装わない(look-ahead 回避)
- `entry_rule = next_trading_close`:snapshot_at の **翌取引日終値**を起点価格とする(同時刻の終値で“約定”しない)。
- これは**約定ではなく評価基準(ASSUMPTION)**と明記。サイクル終端も次決算 available_at の翌取引日終値で対称に。
- 決算跨ぎギャップの寄り/引けの細部は**要確認(§9-5)**だが、「翌取引日終値・対称」という前提は固定。

### 5.4 採点タイミング / 凍結
- `value-audit score` は **`next_earnings_available_at <= asof` のサイクルのみ採点**。未到来は `pending`。
- checklist / falsification の **構造化条件は snapshot 時に凍結**。採点時に閾値・operator を動かさない(後知恵禁止)。
- 訂正が要る場合は §2.4 の `amends`/`supersedes` で**新イベントを追記**(過去採点・過去仮説は不変)。

---

## 6. claim 分類マッピング(CLAIMS.md 準拠)

| 主張 | 分類 | 根拠/前提 |
|---|---|---|
| 財務生値(売上・営業利益・現金 等) | **FACT** | EDINET docID + as_of(原本遡及可) |
| EV/EBIT・FCF利回り・ROIC・成長率・進捗率・年率換算 | **CALCULATION** | feature レジストリの式 + 入力 as_of に依存 |
| 同業相対 percentile | **CALCULATION**(coverage 不足→**UNKNOWN**) | universe coverage に依存 |
| 歴史的レンジ(自己時系列) | **参考/ASSUMPTION** | FACT 扱いしない |
| EDINET DB analysis scores / AI所見 | **INFERENCE/ASSUMPTION** | FACT 禁止(DATA_LAYER §12)。原データに遡及 |
| 安い理由の分類 / 反対仮説 | **INFERENCE** | 事実からの推論・前提明示 |
| 年率10%ハードル | **ASSUMPTION** | config パラメータ。予測でない |
| 手入力 snapshot(Phase A) | **ASSUMPTION** | `source:"manual"`・概算と明示 |
| 欠損/nan/inf/未算出(DCA等) | **UNKNOWN** | 0/false にしない・分母から除外 or 明示 |
| 「買うべき/上がる」 | **UNSAFE** | **出力禁止** |

---

## 7. CLI 契約(既存6コマンド不変・追加のみ)

| cmd | 文法 | 出力 | network |
|---|---|---|---|
| `value-audit register` | `value-audit register <ticker> [--asof YYYY-MM-DD] [--from-file <json>]` | `outputs/value_audit/<slug>.md` + thesis 追記 | 自動取得は B 以降(A は手入力 json) |
| `value-audit score` | `value-audit score [--asof YYYY-MM-DD]` | cycle_outcome 追記(端末サマリ) | 価格取得は B 以降 |
| `value-audit review` | `value-audit review [--asof YYYY-MM-DD]` | `outputs/value_audit_review.md` | なし |

- `--asof` は厳密 `YYYY-MM-DD` 検証(既存 mirror/score/target-check と同実装)。
- 各コマンドは **入力 / 出力先 / 鮮度 / 欠損 / 注意**を表示(DATA_LAYER §13 を継承)。
- **thesis / cycle_outcome の保存先は §2.4 の追記専用 JSONL**(個人データ・gitignore。サンプルは `*.example.jsonl`)。
- `--from-file`(Phase A):**手入力 snapshot**(値は ASSUMPTION タグ)で**オフラインでも閉ループを回せる**。
  これは target-check / journal と同じく「データ層なしで設計・検証可能」にするための入口。
- ticker は §2.5 で**厳格検証**。出力名は safe slug。

### 7.1 register は「購入意思」ではない(item3)
- `value-audit register` は **紙上の仮説登録(paper)** であり、**買う意思の表明ではない**。CLI 出力・md 冒頭に明記。
- 実際に売買を検討する場合の正規ルートは **`radar check`(規律ゲート)→ 人間判断 → `radar log`(予測つき記録)**。
  value-audit はこの判断系統と**独立**(`position_intent` で立場だけ示す。買い案・金額・目標株価は持たない)。
- `position_intent:"existing_holding_review"` は「既に保有しているものの仮説点検」を表すだけで、
  **増し玉・利確の提案はしない**(それも check → 人間 → log)。

---

## 8. テスト計画(オフライン・fake clock・fixtures)

- **PIT 強制**:`available_at > asof` のデータを混入させたら**採点で除外/拒否**。未来価格で採点しない。
- **欠損 = UNKNOWN**:metric 欠損/nan/inf を **0 にしない**・UNKNOWN 保持・`min_metrics_for_audit` 未満で「評価不能」。
- **DCA 未算出 = UNKNOWN(item1)**:`benchmark_index_ref` 無し → `benchmark.return`/`excess_vs_dca`/`beat_dca`
  が **null + status UNKNOWN**(false にしない)。**review の対DCA hit率は出さない/分母に入れない**。
- **年率換算の極端値(item6)**:cycle_days が `min/max_cycle_days` 範囲外 → `annualized_return`/`vs_target_10pct`
  が UNKNOWN(または warning)。**raw_return は出る**。対10% hit率の分母に**入らない**。review で別枠表示。
- **checklist 構造化(item2)**:一致/発火は **operator/threshold/tolerance/actual のみ**から判定。
  `expectation`/`why` を変えても一致率が変わらない。`qualitative_only`/UNKNOWN は分母から除外。
- **必須項目**:`cheapness_reason` / `anti_thesis` / `falsification` / `next_earnings_checklist` の
  **いずれか欠落で register 拒否**(item7 含む)。
- **買い意思フィールド禁止(item3)**:`buy_intent`/`entry_plan`/`target_price`/`position_size` 等が
  入力にあれば**拒否**。`position_intent` は許可値のみ。
- **path safety(item5)**:`../`・`/`・空・制御文字・超長 ticker を**拒否**。出力名が
  `outputs/value_audit/` を脱出しない(slug 化)。
- **イベントソース不変(item4)**:`amends`/`supersedes` で**過去行が書き換わらない**。
  同一 asof で score 再実行 → 過去 outcome 不変(決定性・後知恵禁止)。
- **語彙ガード**:出力に **`buy_candidate` / ランキング / 期待リターン順 / 「買うべき」「おすすめ」
  「上がる可能性が高い」「割安だから買い」が無い**こと(target-check のテスト方式。否定免責の文脈は許容)。
- **review 表示順(item8)**:UNKNOWN/サンプル不足 → 反証発火 → リスク → checklist → 対10% → 対DCA の順。
  **hit率が先頭に出ない**ことを検証。
- **EDINET scores を FACT にしない**:analysis score 由来は INFERENCE/ASSUMPTION タグ。
- **既存非回帰**:`mirror/check/log/score/review/target-check` の CLI/I/O 不変(subprocess で --help と実行)。
- **書込スコープ**:検証出力は `outputs/value_audit/` と `journal/value_*.jsonl` のみ(data/raw 等を汚さない)。

---

## 9. コード前に決めるべき未確定事項(🔸 / 要・人間判断)

> v2 で **DCA UNKNOWN 化(1)/ checklist 構造化(2)/ journal 分離(旧6)/ ID・保存先(旧7)/ 起点価格(旧5の前提)**
> は**設計確定**(§2・§5.3)。残るのは下記。

1. 🔸**ハードルの税基準**(`hurdle_basis`):pre-tax(暫定)か post-tax か。post-tax にするなら target-check の
   `t=0.20315` / NISA 非課税分岐と整合させる。**要決定**。
2. 🔸**DCA 価格系列の入手**:`benchmark_index_ref` に入れる**指数の価格系列**をどこから持つか
   (代替 ETF 終値の手入力 fixture か / B の sync 後か)。確定まで A は**対DCA=UNKNOWN**で進める(§4.1)。
3. 🔸**`min_cycle_days` / `max_cycle_days` の値**:何日を外れ値とみなすか(暫定 45 / 200)。**要決定**。
4. 🔸**進捗率(progress_rate)の入力**:会社予想(ガイダンス)が PIT で取れるか・改訂版管理。
   取れない場合は UNKNOWN 固定。**要確認**(データ層 B)。
5. 🔸**同業相対の universe**:coverage が無いと sector_relative は常に UNKNOWN。
   universe 構築は sync 依存(C)。A/B でどこまで「相対なし」で意味を持たせるか。**要決定**。
6. 🔸**決算跨ぎギャップの細部**:翌取引日の寄り/引けのどちらか(§5.3 は「終値・対称」を暫定固定)。**要確認**。
7. 🔸**feature 式の確定**:EV/EBIT・FCF・ROIC・ネットキャッシュ の**具体式・必須入力 field・UNKNOWN 条件**は
   DATA_LAYER §8 の feature レジストリに合流(Phase C の前提)。本 SPEC は式を**レジストリ参照**に委ねる。
8. 🔸**検証に必要な最小 N と期間**:決算は年≈4回。意味ある hit率/一致率に必要なサンプル数と年数の目安。**要決定**。

---

## 10. Phase 分割(A1/sync 未解禁でも進める範囲を分離)

- **Phase A(GO 可・ネットワーク無し)**
  - **手入力 snapshot(`--from-file`)での閉ループ**:`value_thesis` / `cycle_outcome` schema(§2)、
    register/score/review の純計算(raw_return・年率換算※範囲内のみ・対10%・**対DCA=UNKNOWN**・構造化一致率)、
    report 4点 + review 固定表示順(§4)、claim 分類、PIT 検証(asof 比較)、ID/イベントソース/path safety、
    オフラインテスト一式。
  - **手入力値は ASSUMPTION タグ**。データ層に触れない。target-check / journal と同列の「データ層なしで動く」機能。
  - **対DCA hit率は出さない**(価格系列が無い間は UNKNOWN・§4.1)。
  - 完了条件:手入力 fixture で thesis 登録 → 採点 → 較正が再現可能・推奨/予測語ゼロ・既存非回帰・
    全主張 claim 分類・**UNKNOWN を負けに数えない**・path safety・イベント不変。
- **Phase B(NO-GO / ToS 充足 + A1・sync 後)**
  - financials / prices を sync(DATA_LAYER B)から **available_at つき**で取り込み、snapshot を**自動構築**。
    DCA 価格系列が入れば対DCA を UNKNOWN から CALCULATION に昇格。
  - 完了条件:raw + provenance から PIT 準拠で snapshot・採点が再現(raw_hash 一致)。
- **Phase C(NO-GO / ToS 充足後)**
  - feature レジストリ合流(EV/EBIT・FCF・ROIC 等)+ **同業相対(universe coverage)** + EDINET text-block を
    cheapness_reason/anti_thesis の evidence に。analysis scores は INFERENCE 固定。entity mapping 合流。
  - 完了条件:相対評価つき value_audit が生成・売買断定無し・全主張 claim 分類・原本(docID)遡及可。

> **ToS ブロッカー(LICENSE_MATRIX)**:B/C は J-Quants/EDINET DB の **raw 保存・第三者LLM入力・再配布**が
> 許容と確認できるまで **NO-GO**(DATA_LAYER §16・D1 と同一ゲート)。Phase A は**この層と独立**で進められる。

---

## 11. 受け入れ基準(セルフチェック)

- [x] 年利10%は**目標・比較軸(ASSUMPTION)**で、予測/保証になっていない(§0.1・§6)。
- [x] research_item は**買い候補に見えない**(語彙ロック・`position_intent`・買い意思フィールド禁止・
  discipline_status 未通過・免責・並べ替えキー無し)(§2.1・§7.1)。
- [x] **`available_at <= asof` 必須**で未来データ混入を防ぐ(§5)。
- [x] 割安の理由・**反対仮説**・反証条件・次決算確認項目が**必須**(欠落で register 拒否)(§2.1・§3・§8)。
- [x] **DCA は算出可能時のみ**比較。未算出は **UNKNOWN(false/負けにしない)**・hit率を出さない(§2.2・§4.1・§8)。
- [x] **一致率/hit率は構造化フィールドのみ**から計算・UNKNOWN を分母に入れない(§2.6・§4.1)。
- [x] **年率換算の極端値**を UNKNOWN/別枠化し 10% hit を煽らない(§2.2・§4.1・item6)。
- [x] **イベントソース・原本不変**(amends/supersedes、過去採点不変)(§2.4・§5.4)。
- [x] **path safety / ticker 厳格検証**(traversal 不可・safe slug)(§2.5・§8)。
- [x] **discipline check 前に売買提案を出さない**(検証専用・売買案を持たない)(§1・§7.1)。
- [x] CLAIMS の **FACT/CALCULATION/INFERENCE/ASSUMPTION/UNKNOWN** を守る(§6)。欠損を 0 にしない。
- [x] コード前に**曖昧点・ブロッカーを明示**(§9)。

---

## 12. 報告(設計者所見)

### 実装 GO/NO-GO
- **設計:GO**(v2 で前回レビューの設計穴=DCA UNKNOWN 化 / checklist 構造化 / position_intent /
  ID・イベントソース・保存先 / path safety / 年率換算の極端値 / anti_thesis 必須 / review 表示順 を反映)。
- **実装:Phase A は GO**(本 v2 の設計が反映された前提)。範囲は
  **手入力 snapshot + schema + 純計算 + テスト、ネットワーク無し・stdlib**。
  - **対DCA は UNKNOWN で進める**(価格系列が無い間は hit率を出さない・§4.1)。
  - 着手前に **§9-1(税基準)/ §9-3(min/max_cycle_days の値)** の暫定値を確定(暫定: pre_tax / 45・200)。
- **Phase B / C:NO-GO**。LICENSE_MATRIX の ToS(raw 保存・第三者LLM入力・再配布)が埋まるまで凍結
  (データ層 A1/sync と同一ブロッカー)。

### Phase 順序
- **A(オフライン閉ループ)→ B(sync で snapshot 自動構築・対DCA 昇格)→ C(feature/同業相対/EDINET text)**。
  A は B/C と独立に価値を出す(手入力でも「仮説→次決算検証→較正」が回る)。

### Phase A 実装前に残る未決事項(優先順)
1. ハードルの税基準(pre/post-tax、target-check との整合)— 暫定 pre_tax。
2. DCA 価格系列の入手方針(無い間は対DCA=UNKNOWN で確定)。
3. `min_cycle_days` / `max_cycle_days` の値 — 暫定 45 / 200。
4. 進捗率・同業相対の入手可否(B/C 依存、無ければ UNKNOWN 固定)。
5. 検証に必要な最小 N と期間の目安(年4回=数年かかる前提の明示)。

### 実装状況
- **本対応はコードを書いていない。** EARNINGS_CYCLE_VALUE_AUDIT_SPEC.md(設計メモ)の改訂のみ。
  既存コード(radar/*, tests/*)・他 SPEC は変更していない。

> ※本書は設計メモであり、投資助言・予測・売買指示・購入意思ではない。実装は本契約と上位原則の帰結に限る。
