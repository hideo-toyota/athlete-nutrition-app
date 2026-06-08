# SPEC — Personal Equity Research Radar(契約: データ構造とインターフェイス)

> 本書は [[DESIGN_PRINCIPLES]] の帰結としての**契約**。実装(コード)はこの契約の自動的な帰結。
> 契約と原則が矛盾したら、原則が優先。未決点は「🔸未決(要・人間判断)」として残す。
> 起草: spec-architect 役 / 承認: 人間ゲート(未承認)

## 0. スコープと非目標
- **MVPの心臓は2つ**:(1) **honest mirror**(look-through集中度=“見えない総集中度”の可視化)、(2) **decision log**(判断→結果→学びの閉ループ)。指標分析・バックテストは**後段**。
- 非目標:自動発注 / リアルタイム株価 / 投資助言の断定 / 公開サービス。
- 既存の `opportunity_radar.py` 等は**spike(原則発見のための試作)**。本SPECの実装は**それを参照しつつ作り直す**(レトロフィットしない)。🔸未決(下記 D8)

---

## 1. データ構造(=この道具の本体)

### 1.1 `config.json`(宣言的設定 / 原則6)
```jsonc
{
  "principles_ref": "DESIGN_PRINCIPLES.md",
  "measure_currency": "JPY",            // 支出通貨で測る(原則3)。🔸D2
  "policy": {
    "core_satellite": { "core_pct": 90, "satellite_pct": 10 },
    "satellite": {
      "max_pct_of_total": 10,           // サテライト上限(総資産比)
      "min_names": 3, "max_names": 5,
      "max_pct_per_name": 2.5,          // 1銘柄上限(総資産比)。🔸D3
      "max_pct_per_sector": 5,          // セクター分散の上限。🔸D4
      "size_is_conviction_proof": true  // 確信で上限を緩めない(c対策)
    },
    "discipline": {
      "no_chase": true,                 // 過熱/急騰時は新規・買い増し禁止(a対策)
      "averaging_down": {               // ナンピンの3条件(原則: 価格でなく仮説)
        "require_thesis_intact": true,
        "never_breach_cap": true,
        "require_predeclared_powder": true
      },
      "sell_triggers": ["thesis_break", "rebalance_to_cap", "cash_need"],
      "override_requires_reason": true  // 規律破りは理由を記録(原則2)
    }
  },
  "benchmark": { "type": "dca_index", "index_ref": "...", "note": "同一CFのDCA" }, // 原則5
  "accounts": [
    { "id": "self_nisa_growth", "owner": "self", "type": "nisa_growth", "loss_offset": false },
    { "id": "self_nisa_tsumitate", "owner": "self", "type": "nisa_tsumitate", "loss_offset": false },
    { "id": "spouse_nisa", "owner": "spouse", "type": "nisa_growth", "loss_offset": false },
    { "id": "taxable", "owner": "self", "type": "taxable", "loss_offset": true }
  ],
  "data_source": { "type": "csv|jquants", "price_dir": "...", "index_composition_ref": "..." } // 🔸D1
}
```

### 1.2 `portfolio.json`(保有=真実 / 原則6)
```jsonc
{
  "as_of": "YYYY-MM-DD",
  "holdings": [
    {
      "ticker": "NVDA", "name": "NVIDIA", "sector": "US-Tech/AI",
      "region": "US", "currency": "USD",
      "account": "self_nisa_growth",
      "kind": "individual_stock",        // index_fund | etf | individual_stock | cash
      "sleeve": "satellite",             // core | satellite(ラベルは正直に。単一株は集中扱い)
      "quantity": 0, "cost_basis_jpy": 0, "market_value_jpy": 0
    },
    {
      "ticker": "EIDX", "name": "全世界株インデックス", "kind": "index_fund",
      "sleeve": "core", "composition_ref": "indices/acwi.json", "market_value_jpy": 0
    }
  ]
}
```

### 1.3 `indices/*.json`(指数の構成=look-throughの材料 / 🔸D1)
```jsonc
{
  "name": "ACWI(概算)", "as_of": "YYYY-MM",
  "region_weights": { "US": 0.62, "JP": 0.05, "other": 0.33 },
  "sector_weights": { "US-Tech/AI": 0.28, "...": 0.0 },
  "top_holdings": { "NVDA": 0.045, "AAPL": 0.04, "TSLA": 0.018 }  // 概算でよい(原則3: 粗くても正直に)
}
```

### 1.4 `thesis/<ticker>.json`(個別銘柄の仮説と出口)
```jsonc
{
  "ticker": "NVDA",
  "thesis": "未成熟で成長余地、AI/データセンターの優位",
  "edge_claimed": "selection(2) / behavioral(3)",     // どのエッジに賭けるか
  "priced_in_check": "市場は既にどこまで織り込んでいるか(正しい≠織り込まれていない)",
  "falsifiable": {                                     // 反証可能な事前予測(原則3/5)
    "claim": "...", "metric": "...", "threshold": "...", "horizon": "YYYY-MM-DD"
  },
  "exit_conditions": [                                 // 仮説崩壊の引き金(価格でなく事業)
    "成長が構造的に停止 / 成熟期入り",
    "AI優位の喪失・競合にシェアと利益率を奪われる"
  ],
  "bear_case": "...", "kpis_to_watch": ["..."],
  "sizing": { "target_pct": 0, "max_pct": 2.5 }
}
```

### 1.5 `decision_log.jsonl`(追記専用・心臓 / 原則2・5)
**不変条件**: 1行=1判断、**追記のみ・編集/削除不可**。`prediction` は結果が出る前に書く。`outcome` は**期日にツールが機械記入**(人は触らない)。**見送り(pass)も記録**(後知恵対策)。
```jsonc
{
  "id": "uuid", "ts": "ISO8601(書込時刻=固定)",
  "ticker": "NVDA", "account": "self_nisa_growth",
  "action": "buy_new|add|trim|exit|pass|hold_review|override",
  "rationale": "...",
  "prediction": { "claim": "...", "metric": "...", "threshold": "...", "horizon": "YYYY-MM-DD" },
  "vs_discipline": "in_discipline|override",
  "override_reason": "規律を破る理由(overrideなら必須)",   // 原則2
  "size": { "amount_jpy": 0, "resulting_total_pct": 0, "within_cap": true },
  "emotion_note": "任意(較正用の心理状態)",
  "outcome": null   // 後でツールが {scored_at, realized_return, benchmark_return, excess_vs_dca, hit:bool, thesis_status} を機械記入
}
```

### 1.6 レポート契約(全レポート共通 / 原則3・4・1)
- **freshness header(必須)**: `as_of` / データ遅延 / 欠損 / 前提。古ければ**大きく警告**。
- **uncertainty-first**: 先頭セクション=「分かっていないこと・不確実・低信頼」。
- **two-sided**: 仮説は必ず**反証・弱気シナリオと対**で表示。
- **断定しない**: 「買い候補/見送り」等は**出発点ラベル**。売買指示にしない。

---

## 2. モジュール境界と関数契約(=インターフェイス)

| モジュール | 責務 | 主要関数(契約) | 純粋性 |
|---|---|---|---|
| `data` | 価格・指数構成・ポートフォリオ読込 | `load_portfolio()`, `load_index(ref)`, `load_prices(asof)` | I/Oのみ・未来不参照 |
| `concentration` | look-through集中度算出 | `look_through(portfolio, indices) -> Exposure` | 純粋・決定論 |
| `discipline` | 規律判定 | `check(portfolio, config, proposed_action) -> Verdict` | 純粋 |
| `journal` | 判断ログ | `append(entry)`(予測必須を検証), `score_due(asof)`(機械採点・未来不参照), `review() -> Calibration` | 追記専用 |
| `report` | 契約準拠の出力 | `render(kind, data) -> md/csv`(freshness/uncertainty/two-sided強制) | 純粋 |

- `Exposure`: `{ by_name, by_sector, by_region, by_currency, individual_stock_pct, satellite_cap_status }`(direct + 指数look-through合算)。
- `Verdict`: `{ ok: bool, breaches: [rule], notes }`(例: `over_cap`, `chase`, `sector_concentration`, `averaging_down_blocked`)。
- `Calibration`: `{ n, hit_rate, brier_like, excess_vs_dca, override_vs_discipline }`(過程>結果)。

---

## 3. CLI コマンド(入出力契約)

| コマンド | 入力 | 出力 | 何のため |
|---|---|---|---|
| `mirror` | portfolio + indices | `outputs/honest_mirror.md` + csv | **第一の仕事**: 真の集中度(look-through)を映す |
| `check "<action>"` | portfolio + config + 提案 | `Verdict`(端末+md) | 売買前に規律に通す(size/chase/sector/ナンピン) |
| `log "<decision>"` | 判断+事前予測 | decision_log.jsonl に追記 | 予測の事前固定(反証可能でなければ拒否) |
| `score` | decision_log + 価格(asof) | outcome を機械記入 | 後知恵抜きの採点 |
| `review` | decision_log | `outputs/journal_review.md` | 較正・DCA比・「裁量 vs 規律」 |
| (後段) `analyze` / `backtest` | — | — | 個別の分析・検証 |

---

## 4. 不変条件(原則6)
- **未来を見ない**: 時系列計算は `asof` のみ。`score` も判断日時点で入手可能な情報だけで採点。
- **ファイル=真実**: 状態は JSON/JSONL/MD/CSV。**二度実行で同一出力**。
- **宣言的**: 規律・方針・配分は `config.json`。挙動変更はコードでなく設定で。
- **依存最小**: 標準ライブラリ中心・ローカル完結。

---

## 5. 🔸未決事項(あなたのゲート=ここを決めて)
- **D1 指数のlook-throughデータ源**: 指数構成をどう得る? 案=**まず手入力の概算**(`indices/*.json`、粗くても原則3的に正直)。精緻化は後。
- **D2 測定通貨**: **JPY(支出通貨)**で測る、で確定?(推奨: はい)
- **D3 1銘柄上限**: 総資産比 **2.5%**(=10%÷4)で良い? 別の数字?
- **D4 セクター分散**: サテライト内セクター上限(例 5%)を置く? 値は?
- **D5 採点の“当たり”基準**: 期日で **DCAインデックス超過**を hit とする?(推奨)/ 絶対リターン?
- **D6 decision_log 保存形式**: JSONLを真実とし **Obsidianへエクスポート**?(推奨)/ Obsidian直書き?
- **D7 MVP順序**: `mirror → check → log/score → review` を先、`analyze/backtest` は後。これで良い?
- **D8 既存コードの扱い**: spike(参照のみ・作り直し)で確定? それとも一部流用?
