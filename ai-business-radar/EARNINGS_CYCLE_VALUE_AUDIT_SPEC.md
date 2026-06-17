# EARNINGS_CYCLE_VALUE_AUDIT_SPEC — 「決算 to 決算 value audit」契約(設計のみ・実装前)

> 設計のみ。コードはこの契約の帰結。正は DESIGN_PRINCIPLES.md / SPEC.md / CLAIMS.md / CLAUDE.md /
> DATA_LAYER_SPEC.md / LICENSE_MATRIX.md / TARGET_CHECK_SPEC.md。
> これは **割安“仮説”を、決算から決算までの1サイクルで検証する道具**。
> **買い候補を作らない・銘柄を推奨しない・将来を予測しない。** research_item / evidence / score の系譜。

---

## 0. 目的 / 非目的

- **目的**: 「この銘柄は割安だ」という**自分の仮説を、反証可能な形で事前固定**し、
  決算発表(available_at)で固定した snapshot から **次の決算 available_at までを1サイクル**として
  事後に検証する。検証軸は「年率10%換算」と「DCAインデックス」。**過程 > 結果**(原則5)。
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
  そもそも売買案を出さない。実保有判断は別途 `check` → 人間。
- **欠損を 0 扱いしない**:欠損/nan/inf/非数値は当該値 **UNKNOWN 保持**(計算は止めず、その metric を除外/明示)。
- **API仕様・データ欠損を report 層で回避しない**:欠損は feature/source 層で UNKNOWN として表現し、
  report はそれをそのまま正直に出す(穴を埋めない)。

---

## 2. データ構造(=本体)

### 2.1 `value_thesis`(検証対象の仮説。research_item の subtype・**買い候補ではない**)
DATA_LAYER §10 の **語彙ロックを継承**(`type:"research_item"` 固定、`buy_candidate` 等の語は禁止)。
```jsonc
{
  "type": "research_item",            // ★固定(buy_candidate 禁止)
  "subtype": "value_audit",           // 本機能の識別
  "schema_version": "1",
  "thesis_id": "短縮uuid",
  "ticker": "7203", "company_name": "...", "market": "...", "sector": "...",

  // --- サイクル定義(PIT) ---
  "snapshot_at": "ISO8601(tz付)",     // = 起点決算の available_at(§5)。これより新しいデータは使わない
  "cycle": {
    "start_available_at": "ISO8601",  // = snapshot_at
    "next_earnings_expected": "YYYY-MM-DD",        // earnings-calendar 予定(版を持つ・ASSUMPTION)
    "next_earnings_available_at": "ISO8601|null"   // 確報の available_at。出るまで null(=未採点)
  },

  // --- 割安の“定義”をベクトルで(単独指標で断定しない・§3) ---
  "valuation": {                      // 各 metric: {value|null, unit, claim, basis, evidence_ref, status}
    "ev_ebit": {}, "fcf_yield": {}, "roic": {}, "net_cash": {},
    "op_margin": {}, "revenue_growth": {}, "op_profit_growth": {},
    "progress_rate": {},              // 会社予想に対する進捗(会社予想の available_at に従う)
    "sector_relative": {}             // 同業相対(universe coverage 依存→不足は UNKNOWN)
    // status ∈ FACT|CALCULATION|UNKNOWN。欠損は null + status:"UNKNOWN"(0 にしない)
  },

  // --- 安い理由(必須・構造劣化か一時要因かを分ける) ---
  "cheapness_reason": {               // ★必須。無ければ register 拒否
    "classification": "temporary_setback | structural_decay | mispricing_hypothesis | unknown",
    "explanation": "なぜ安いと考えるか(自由文)",
    "claim": "INFERENCE",             // 事実からの推論として明示・前提を書く
    "evidence_refs": [ /* provenance / EDINET docID / IR */ ]
  },

  // --- 反証条件(必須・事前固定・後知恵防止) ---
  "falsification": [                  // ★必須・1件以上。無ければ register 拒否
    { "claim": "...", "metric": "op_margin", "threshold": "...", "direction": "below|above",
      "horizon": "next_earnings" }    // horizon は原則「次決算 available_at」
  ],

  // --- 次決算で見る項目(必須・事前固定) ---
  "next_earnings_checklist": [        // ★必須・1件以上。snapshot 時点で凍結(後から足さない)
    { "metric": "revenue_growth", "expectation": "...", "why": "仮説のどこを確かめるか" }
  ],

  "key_risks": [],                    // 必須
  "entry_rule": "next_trading_close", // §5.3: snapshot_at 翌取引日終値を基準(約定ではない・ASSUMPTION)
  "discipline_status": "未通過",      // ★固定・必須(検証専用。売買は別途 check)
  "claim_tags": {},                   // 主張ごとの分類(CLAIMS §各主張)
  "disclaimer": "割安“仮説”の検証対象。買い推奨でも予測でもない。売買は discipline check + 人間判断が必要。"
}
```
- **並べ替えキーは持たない。** どうしても順序が要る場合のみ `coverage_priority`(網羅度)を使い、
  **魅力度/期待リターン/割安度ランキングは禁止**(DATA_LAYER §10 を継承)。

### 2.2 `cycle_outcome`(採点結果・追記専用・後知恵禁止)
decision_log と同じ**イベントソース**思想(SPEC §1.5):snapshot を改変せず、結果は別行で追記。
```jsonc
{
  "type": "cycle_outcome", "thesis_id": "対応する value_thesis の id",
  "scored_at": "YYYY-MM-DD",
  "cycle_days": 0,                    // start→next_earnings available_at の実日数
  // 絶対リターン(価格・PIT)
  "price_return": 0.0,               // entry_rule → next_earnings available_at 基準
  "annualized_return": 0.0,          // (1+price_return)^(365/cycle_days)-1  [CALCULATION]
  "vs_target_10pct": false,          // annualized_return >= hurdle(ASSUMPTION) を満たしたか
  // 相対リターン(DCAインデックス・同一窓)
  "benchmark_return": 0.0,           // 同一窓の DCA インデックス(§7・要 index 価格系列=ブロッカー)
  "excess_vs_dca": 0.0, "beat_dca": false,
  // リスク
  "max_drawdown_pct": null,          // サイクル中の最大DD(日足が要る→B/C 依存。無ければ UNKNOWN)
  "concentration_note": "...",       // mirror の集中度文脈(任意・参考)
  // 再現性(事前仮説と次決算結果の対応)
  "checklist_result": [ { "metric": "...", "expected": "...", "actual": "...|UNKNOWN", "matched": true } ],
  "falsification_triggered": [ "...どの反証条件に触れたか..." ],
  "cheapness_resolution": "temporary_confirmed | structural_confirmed | undetermined",
  "claim_tags": {}
}
```

### 2.3 `config` 追加(宣言的・コード直書き禁止)
```jsonc
"value_audit": {
  "annual_hurdle_pct": 10,           // ★ハードル(ASSUMPTION)。予測でない
  "hurdle_basis": "pre_tax|post_tax",// 🔸未決(§9)。target-check の t=0.20315 と整合させるか
  "annualization_day_base": 365,     // 年率換算の基準日数(固定・再現性)
  "benchmark_index_ref": "indices/…",// DCA 比較に使う指数(価格系列が必要=ブロッカー §7)
  "min_metrics_for_audit": 3         // valuation のうち status!=UNKNOWN がこの数未満なら「評価不能」と明示
}
```

---

## 3. 「割安」を曖昧にしない(定義契約)

- **割安は単一指標の判定ではなく、ベクトル + 文脈**で表す。PER/PBR 単独で「割安」と言わない。
- 各 metric は **2つの文脈**で提示(どちらも CALCULATION、coverage 不足は UNKNOWN):
  1. **自己時系列**:過去レンジに対する現在位置(歴史値は参考=ASSUMPTION 寄り、FACT 化しない)。
  2. **同業相対**:universe 内の相対位置(percentile)。**universe coverage が無ければ UNKNOWN**(B/C 依存)。
- **「安い理由」を必須項目**にし(`cheapness_reason`)、必ず
  **一時的悪材料(temporary_setback)/ 構造劣化(structural_decay)/ ミスプライス仮説(mispricing_hypothesis)**
  のいずれかに分類。**分類は INFERENCE**(前提を明示)。**「割安→買い」への飛躍は禁止**。
- **次決算で確認する指標を事前固定**(`next_earnings_checklist`)。snapshot 後に項目を足さない(後知恵防止)。
- **反証条件を必須**(`falsification`)。「これが起きたら仮説は壊れた」を事前に書く(原則3・4)。

---

## 4. 出力契約(`outputs/value_audit/<ticker>.md` / `outputs/value_audit_review.md`)
**4点のみに限定**(これ以外の“結論”を出さない):
1. **検証対象(What we are testing)**:仮説の要旨 + snapshot_at + サイクル定義。先頭に**不確実性**(原則3)。
2. **必要条件(What must hold)**:仮説が生きるために満たすべき条件(= checklist の事前期待)。
3. **反証条件(What would break it)**:`falsification`。触れたら仮説棄却。
4. **次決算で見る項目(What to read next)**:metric と「仮説のどこを確かめるか」。
- レポート共通契約(SPEC §1.6)を継承:freshness header / uncertainty-first / two-sided / 断定しない。
- **valuation は claim 分類つき**で表示。欠損は「UNKNOWN(未取得/欠損)」と明示し、**0 で埋めない**。
- review は **対10%ハードル hit率 / 対DCA hit率 / 再現性(checklist 一致率)** を**事後測定**として出す。
  サンプル < 20 は「統計的結論は保留」(原則3、review の既存挙動に合わせる)。
- 免責:投資助言でない・予測でない・売買指示でない・利益保証でない。

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

### 5.4 採点タイミング
- `value-audit score` は **`next_earnings_available_at <= asof` のサイクルのみ採点**。未到来は `pending`。
- checklist / falsification の値は **snapshot 時に凍結**。採点時に閾値を動かさない(後知恵禁止)。

---

## 6. claim 分類マッピング(CLAIMS.md 準拠)

| 主張 | 分類 | 根拠/前提 |
|---|---|---|
| 財務生値(売上・営業利益・現金 等) | **FACT** | EDINET docID + as_of(原本遡及可) |
| EV/EBIT・FCF利回り・ROIC・成長率・進捗率・年率換算 | **CALCULATION** | feature レジストリの式 + 入力 as_of に依存 |
| 同業相対 percentile | **CALCULATION**(coverage 不足→**UNKNOWN**) | universe coverage に依存 |
| 歴史的レンジ(自己時系列) | **参考/ASSUMPTION** | FACT 扱いしない |
| EDINET DB analysis scores / AI所見 | **INFERENCE/ASSUMPTION** | FACT 禁止(DATA_LAYER §12)。原データに遡及 |
| 安い理由の分類 | **INFERENCE** | 事実からの推論・前提明示 |
| 年率10%ハードル | **ASSUMPTION** | config パラメータ。予測でない |
| 欠損/nan/inf | **UNKNOWN** | 0 にしない・除外 or 明示 |
| 「買うべき/上がる」 | **UNSAFE** | **出力禁止** |

---

## 7. CLI 契約(既存6コマンド不変・追加のみ)

| cmd | 文法 | 出力 | network |
|---|---|---|---|
| `value-audit register` | `value-audit register <ticker> [--asof YYYY-MM-DD] [--from-file <json>]` | `outputs/value_audit/<ticker>.md` + thesis 追記 | 自動取得は B 以降(A は手入力 json) |
| `value-audit score` | `value-audit score [--asof YYYY-MM-DD]` | cycle_outcome 追記(端末サマリ) | 価格取得は B 以降 |
| `value-audit review` | `value-audit review [--asof YYYY-MM-DD]` | `outputs/value_audit_review.md` | なし |

- `--asof` は厳密 `YYYY-MM-DD` 検証(既存 mirror/score/target-check と同実装)。
- 各コマンドは **入力 / 出力先 / 鮮度 / 欠損 / 注意**を表示(DATA_LAYER §13 を継承)。
- **thesis / cycle_outcome の保存先は追記専用 JSONL**(個人データ・git除外候補。decision_log と同様)。
- `--from-file`(Phase A):**手入力 snapshot**(値は ASSUMPTION タグ)で**オフラインでも閉ループを回せる**。
  これは target-check / journal と同じく「データ層なしで設計・検証可能」にするための入口。

---

## 8. テスト計画(オフライン・fake HTTP/clock・fixtures)

- **PIT 強制**:`available_at > asof` のデータを混入させたら**採点で除外/拒否**される。未来価格で採点しない。
- **欠損 = UNKNOWN**:metric 欠損/nan/inf を **0 にしない**・UNKNOWN 保持・`min_metrics_for_audit` 未満で「評価不能」。
- **必須項目**:`cheapness_reason` / `falsification` / `next_earnings_checklist` の**いずれか欠落で register 拒否**。
- **語彙ガード**:出力に **buy_candidate / ランキング / 期待リターン順 / 「買うべき」「おすすめ」「上がる可能性が高い」
  「割安だから買い」が無い**こと(target-check のテスト方式を踏襲・否定免責の文脈は許容)。
- **年率換算の正しさ**:既知 fixture で `(1+r)^(365/days)-1`、サイクル日数の境界(短/長)。
- **対10% / 対DCA**:hit 判定が両軸とも出る。DCA 比較が**必ず**入る。
- **再現性スコア**:checklist の expected vs actual 一致率、falsification 発火検出。
- **凍結**:snapshot 後に checklist/閾値を変えても**過去 thesis の採点が変わらない**(後知恵禁止)。
- **決定性 / asof 再現**:同一 asof で二度実行 → 同一出力。
- **EDINET scores を FACT にしない**:analysis score 由来は INFERENCE/ASSUMPTION タグ。
- **既存非回帰**:`mirror/check/log/score/review/target-check` の CLI/I/O 不変(subprocess で --help と実行)。
- **source 層の書込スコープ**:検証出力は `outputs/value_audit/` と所定 JSONL のみ(data/raw 等を汚さない)。

---

## 9. コード前に決めるべき未確定事項(🔸ブロッカー / 要・人間判断)

1. 🔸**DCA ベンチマークの価格系列**:現状 `indices/*.json` は**構成比のみで価格履歴が無い**。
   決算 to 決算の不規則窓で DCA リターンを出すには**指数の価格系列**が要る。
   → 代替指数(ETF 終値)を別 dataset で持つか、A では「ベンチマーク未算出(UNKNOWN)」で設計するか。**要決定**。
2. 🔸**ハードルの税基準**(`hurdle_basis`):pre-tax か post-tax か。post-tax にするなら target-check の
   `t=0.20315` / NISA 非課税分岐と整合させる。**要決定**。
3. 🔸**進捗率(progress_rate)の入力**:会社予想(ガイダンス)が PIT で取れるか・改訂の available_at 版管理。
   取れない場合は UNKNOWN 固定。**要確認**(データ層 B)。
4. 🔸**同業相対の universe**:coverage が無いと sector_relative は常に UNKNOWN。
   universe 構築は sync 依存(C)。A/B でどこまで「相対なし」で意味を持たせるか。**要決定**。
5. 🔸**起点価格の定義**:`next_trading_close`(翌取引日終値)で確定。
   ただし「決算跨ぎのギャップをどう扱うか(寄り/引け)」の細部は**要確認**(約定を装わない前提は固定)。
6. 🔸**journal/decision_log との関係**:value_thesis は**紙上の検証**で、保有判断とは独立に保つ。
   実保有と紐付けるか(別 id で参照のみ)・**買い候補に見えないための分離方針**を明文化。**要決定**。
7. 🔸**thesis/outcome の保存先**:個人データとして git 除外(decision_log と同様)か、サンプルのみ追跡か。**要決定**。
8. 🔸**feature 式の確定**:EV/EBIT・FCF・ROIC・ネットキャッシュ の**具体式・必須入力 field・UNKNOWN 条件**は
   DATA_LAYER §8 の feature レジストリに合流(Phase C の前提)。本 SPEC は式を**レジストリ参照**に委ねる。

---

## 10. Phase 分割(A1/sync 未解禁でも進める範囲を分離)

- **Phase A(GO 可・ネットワーク無し)**
  - 設計の確定 + **手入力 snapshot(`--from-file`)での閉ループ**:`value_thesis` / `cycle_outcome` schema、
    register/score/review の純計算(年率換算・対10%・対DCA※指数系列がある場合・再現性スコア)、
    report 4点出力、claim 分類、PIT 検証ロジック(asof 比較)、オフラインテスト一式。
  - **手入力値は ASSUMPTION タグ**で正直に。データ層に触れない。target-check / journal と同列の「データ層なしで動く」機能。
  - 完了条件:手入力 fixture で thesis 登録 → 採点 → 較正が再現可能・推奨/予測語ゼロ・既存非回帰・全主張 claim 分類。
- **Phase B(NO-GO / ToS 充足 + A1・sync 後)**
  - financials / prices を sync(DATA_LAYER B)から **available_at つき**で取り込み、snapshot を**自動構築**。
  - 完了条件:raw + provenance から PIT 準拠で snapshot・採点が再現(raw_hash 一致)。
- **Phase C(NO-GO / ToS 充足後)**
  - feature レジストリ合流(EV/EBIT・FCF・ROIC 等)+ **同業相対(universe coverage)** + EDINET text-block を
    cheapness_reason の evidence に。analysis scores は INFERENCE 固定。
  - 完了条件:相対評価つき value_audit が生成・売買断定無し・全主張 claim 分類・原本(docID)遡及可。

> **ToS ブロッカー(LICENSE_MATRIX)**:B/C は J-Quants/EDINET DB の **raw 保存・第三者LLM入力・再配布**が
> 許容と確認できるまで **NO-GO**(DATA_LAYER §16・D1 と同一ゲート)。Phase A は**この層と独立**で進められる。

---

## 11. 受け入れ基準(セルフチェック)

- [x] 年利10%は**目標・比較軸(ASSUMPTION)**で、予測/保証になっていない(§0.1・§6)。
- [x] research_item は**買い候補に見えない**(語彙ロック・discipline_status 未通過・免責・並べ替えキー無し)(§2.1)。
- [x] **`available_at <= asof` 必須**で未来データ混入を防ぐ(§5)。
- [x] 割安の理由・反証条件・次決算確認項目が**必須**(欠落で register 拒否)(§2.1・§3・§8)。
- [x] **DCA インデックス比較**が入っている(§2.2・§4・§7。価格系列はブロッカー §9-1)。
- [x] **discipline check 前に売買提案を出さない**(検証専用・売買案を持たない)(§1)。
- [x] CLAIMS の **FACT/CALCULATION/INFERENCE/ASSUMPTION/UNKNOWN** を守る(§6)。欠損を 0 にしない。
- [x] コード前に**曖昧点・ブロッカーを明示**(§9)。

---

## 12. 報告(設計者所見)

### 実装 GO/NO-GO
- **設計:GO**(本 SPEC が成果物)。
- **実装:Phase A のみ GO**(手入力 snapshot + schema + 純計算 + テスト、ネットワーク無し・stdlib)。
  ただし **§9 の未決(特に 1=DCA価格系列、2=税基準、6=journal 分離)を先に確定**すること。
  DCA 価格系列が無い間は、A は「対DCA=UNKNOWN(未算出)」で出す設計に倒す(正直に欠く)。
- **Phase B / C:NO-GO**。LICENSE_MATRIX の ToS(raw 保存・第三者LLM入力・再配布)が埋まるまで凍結
  (データ層 A1/sync と同一ブロッカー)。

### Phase 順序
- **A(オフライン閉ループ)→ B(sync で snapshot 自動構築)→ C(feature/同業相対/EDINET text)**。
  A は B/C と独立に価値を出す(手入力でも「仮説→次決算検証→較正」が回る)。

### コード前に決めるべき未確定事項(再掲・優先順)
1. DCA ベンチマークの価格系列をどう持つか(無ければ A は対DCA=UNKNOWN)。
2. ハードルの税基準(pre/post-tax、target-check との整合)。
3. value_thesis と decision_log の分離方針(買い候補に見せない)。
4. thesis/outcome の保存先(git 除外 or サンプル追跡)。
5. 進捗率・同業相対の入手可否(B/C 依存、無ければ UNKNOWN 固定)。

> ※本書は設計メモであり、投資助言・予測・売買指示ではない。実装は本契約と上位原則の帰結に限る。
</content>
