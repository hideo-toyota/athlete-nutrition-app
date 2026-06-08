# PLAN — 実装計画(Personal Equity Research Radar)

> [[DESIGN_PRINCIPLES]] と [[SPEC]](承認済み)から起草。起草: planner役 / 承認: 人間ゲート(未承認)。
> 方針: 標準ライブラリのみ・ファイル=真実・未来を見ない・宣言的設定。コードはSPECの契約を一字一句満たす。
> 既存コードは `spike/` へ退避(D8)。実装は新規 `radar/` に作る。

## モジュール構成(SPEC §2 に一致)
```
ai-business-radar/
├── radar/
│   ├── __init__.py
│   ├── config.py          # config.json の読込・検証(宣言的設定)
│   ├── data.py            # load_portfolio / load_index / load_prices(asof)
│   ├── concentration.py   # look_through() -> Exposure(純粋・決定論)
│   ├── discipline.py      # check() -> Verdict(純粋)
│   ├── journal.py         # append / score_due(asof) / review()(追記専用)
│   └── report.py          # render()(freshness/uncertainty/two-sided 強制)
├── radar.py               # CLI: mirror / check / log / score / review
├── config.json            # 宣言的設定(SPEC §1.1)
├── portfolio.json         # 保有=真実(SPEC §1.2)
├── indices/*.json         # 指数構成(手入力概算 / D1)
├── thesis/<ticker>.json   # 銘柄の仮説と出口(SPEC §1.4)
├── decision_log.jsonl     # 追記専用・心臓(SPEC §1.5)
├── outputs/               # honest_mirror.md 等(生成物)
└── spike/                 # 旧コード(参照のみ・D8)
```

## フェーズ(各スライスは独立して価値を出し、原則準拠+検証ゲートを通す)

### Phase 0 — 足場とデータ契約
- `radar/config.py`:`config.json` 読込+検証(必須キー・型・合計100%等)。
- `data.py`:`load_portfolio()` / `load_index(ref)`。サンプル `portfolio.json`(NVDA/TSLA + 全世界指数 = あなたの実状を反映)、`indices/acwi.json`(手入力概算)。
- **DoD**:不正configで明確に失敗。サンプル読込が通る。
- **検証**:二度読込で同一(files=truth)。

### Phase 1 — `mirror`(第一の価値=正直な鏡)★最初
- `concentration.py`:`look_through(portfolio, indices) -> Exposure`。direct + 指数構成を**合算**し、`by_name / by_sector / by_region / by_currency / individual_stock_pct / satellite_cap_status` を算出。
- `report.py`:freshness header + uncertainty-first + 「あなたは look-through で US-Tech ◯◯%」を提示。
- CLI:`mirror` → `outputs/honest_mirror.md`(+csv)。
- **DoD**:あなたの実ポートフォリオで「真の集中度」が出る。サテライト上限(2.5%/銘柄・5%/セクター・10%/総)超過を**赤表示**。
- **検証**:手計算と一致。二度実行で同一。NVDA/TSLA が per-name 5% / sector ~5% で**超過警告**が出る。

### Phase 2 — `check`(規律のブレーキ)
- `discipline.py`:`check(portfolio, config, proposed_action) -> Verdict`。判定=`over_cap` / `chase`(過熱) / `sector_concentration` / `averaging_down_blocked`(価格でなく仮説+上限+余力)。
- CLI:`check "buy 7203 100000"` → Verdict。
- **DoD**:「NVDAを¥10万買い増し」→ `over_cap` で却下。「過熱日に新規」→ `chase` で却下。
- **検証**:各ルールの真陽性/偽陰性をスモークテスト。

### Phase 3 — `log` / `score`(閉ループの記録と機械採点)
- `journal.py`:`append(entry)`(**反証可能な事前予測が無ければ拒否**、override は理由必須)。`score_due(asof)`(期日到来分の `outcome` を**機械記入**=DCA超過で hit、**未来不参照**)。
- CLI:`log` / `score`。`decision_log.jsonl` は**追記専用**(編集・削除コード無し)。見送り(pass)も記録。
- **DoD**:予測の無いlogは拒否。score後に outcome が入り、人は触れない。
- **検証**:追記専用の不変条件。score が判断日時点の価格のみ使用(look-ahead無し)。

### Phase 4 — `review`(過程>結果の較正)
- `journal.review() -> Calibration`:`hit_rate / brier_like / excess_vs_dca / override_vs_discipline`。
- CLI:`review` → `outputs/journal_review.md` + Obsidianエクスポート(D6)。
- **DoD**:十分なログがあれば「裁量はDCAに勝てているか」を提示。少なければ「サンプル不足・判断保留」と正直に表示(原則3)。

### 後段(MVP外)
- `analyze`(日本中小型の財務スクリーニング/仮説支援)、`backtest`。**安全と正直の土台ができてから**。

## 原則充足チェック(planner自己監査)
| 原則 | 本プランでの担保 |
|---|---|
| 1 最終判断は人間 | 自動発注なし。出力はラベル/検証のみ |
| 2 規律破りは記録 | `append` が override 理由を必須化 |
| 3 無知が最大の罪 | mirror(look-through)・freshness header・uncertainty-first・サンプル不足の正直表示 |
| 4 参謀≠事務員 | report が two-sided(仮説⇔反証)を強制 |
| 5 検証する道具 | log→score→review の閉ループ、採点=DCA超過 |
| 6 ファイル/宣言/未来不参照 | JSON(L)真実・config駆動・asof厳守・二度実行同一・stdlibのみ |

## テスト計画(verifier)
- **再現性**:全コマンド二度実行で出力一致。
- **look-ahead無し**:`score` を過去asofで実行し、未来価格を使っていないことを確認。
- **不変条件**:decision_log への手編集をコードが行わない/追記のみ。
- **鮮度**:古いデータで mirror が警告を出す。
- 各 Verdict ルールのスモークテスト。

## 段階リリース
Phase 1 が動いた時点で**即・実用**(あなたの真の集中度が見える)。以降は1フェーズずつ追加。各フェーズ完了で `python3 -m py_compile` + 該当コマンド実行で確認。
