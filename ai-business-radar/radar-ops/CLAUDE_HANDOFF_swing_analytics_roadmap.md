# CLAUDE_HANDOFF — スイング分析基盤ロードマップ(backtest + data + confluence + regime)

あなた(Codex / Mac側 Claude)は ai-business-radar のシニア実装者兼・安全設計の監査役です。
目的: スイング紙上トライアル(`CLAUDE_HANDOFF_swing_paper_trial.md`)の setup 選定を、
勘ではなく**歴史的期待値**に基づかせる分析基盤を作る。

進め方は本システムの流儀を厳守:
**原則確認 → SPEC → PLAN → 実装 → Codex監査**。各フェーズで SPEC 草案を出して停止し、
人間の承認を得てから実装する。勝手に次フェーズへ進まない。

## 正(必ず読む)
DESIGN_PRINCIPLES.md / CLAIMS.md / DATA_LAYER_SPEC.md / LICENSE_MATRIX.md /
radar-ops/CLAUDE_HANDOFF_swing_paper_trial.md / radar/features/jquants_bulk.py(既存PIT実装)

## 絶対制約(全フェーズ共通・違反は不合格)
- 出力は **setup単位の統計**と**検証入口リスト**まで。買い候補・推奨・ランキング・価格目標・
  将来断定を出さない(FORBIDDEN_OUTPUT_TOKENS ガードを全出力に適用)。
- **PIT厳守**: シグナル計算は当日以前のデータのみ。**エントリーは翌営業日の値**(シグナルが
  終値依存なら同日終値でのエントリーは先読み=禁止)。
- APIキー/.env/raw本文を表示・LLM投入しない。ネットは radar/sources/ に閉じる。
- canonical root guard の対象に含める(分析系コマンドは正本でのみ実行)。
- 既存コマンドのI/Oを壊さない。テスト無しの実装はマージしない。
- 自動売買はしない(恒久)。

---

## Phase BT-1: バックテスト基盤(最優先)

### 目的
事前登録された setup の**歴史的期待値(R単位)**を、取得済み J-Quants 日足から測る。
「シグナル=歴史的に期待値プラスと検証済みの事前登録条件」の定義を実データで運用可能にする。

### 入力
- `data/raw/jquants/bulk/equities/bars/daily/premium`(取得済み日足。ネット不要)
- setup registry(新規): `radar/backtest/setups.py` に**コードで事前登録**
  - 初期実装は swing_paper_trial と同じ語彙: `vwap_reclaim` は日足では近似不能のため除外し、
    日足で定義可能な3つから開始:
    1. `pullback_in_trend` — 60日リターン上位分位 かつ 直近5日で-5%以上の押し → 翌日寄付エントリー
    2. `range_break` — 直近60日高値を終値で更新 かつ 出来高が20日平均の1.5倍以上
    3. `overheat_fade`(ショート想定・紙上のみ) — 20日+40%超 かつ 高値から2日連続陰線
  - 各 setup は {entry条件, stop規則(例: エントリー価格-2ATR相当 or 直近安値), exit規則(target R / time_stop日数)} を持つ
- 除外: ETF/REIT(`その他`)、split_artifact_warning、流動性下限(例: 売買代金20日平均 5,000万円未満)

### 検証規律(ここが本体)
1. **train/test分割**: 期間を分ける(例: train=データ先頭〜2025-06、test=2025-07〜直近)。
   パラメータ調整は train のみ。**test は各 setup につき1回だけ実行**し、結果を改変しない。
2. **多重比較の記録**: 試した setup・パラメータは**全て** `outputs/backtests/attempts_log.jsonl` に
   append-only 記録(お蔵入り禁止)。「10個試して1個勝った」は偶然と区別できないことを出力に明記。
3. **コスト**: 往復0.2%を全トレードに課す。
4. **サンプル下限**: イベント数 < 50 の setup は `sample_too_small` として期待値を表示しない。

### 出力
- `outputs/backtests/<setup>_<train|test>.md/json`:
  期待値(R)/勝率/平均勝ちR/平均負けR/最大DD(R)/イベント数/年別内訳/(RG-1後: レジーム別内訳)
- **銘柄リストは出さない**(setup統計のみ)。例示は匿名化した数件まで。
- CLI: `python3 -m radar backtest --setup <name> --period train|test [--dry-run]`

### テスト要件(合成データで)
- 先読み検出: シグナル翌日エントリーになっているか(終値シグナル同日約定はテストで落とす)
- train/test 分離: test期間のデータが train 実行に混入しない
- コスト適用・R計算の正否 / sample_too_small / 禁止語 / ETF・警告銘柄の除外

### 完了条件(DoD)
py_compile / unittest 全通過。3 setup の train 結果が生成され、attempts_log に記録が残る。
**test 期間は人間の承認後に1回だけ実行。**

---

## Phase DT-1: J-Quants 未使用データの解放

### 目的
契約済みプランに含まれるデータを使い切る。**新規課金の前に必ずここを終える。**

### 対象(優先順)
1. **決算発表予定日**(earnings calendar)【最優先・小さい】
   - derived: `jquants_earnings_calendar_v1/<asof>/calendar.jsonl`
   - 連携: swing_paper_trial の事前登録時、**time_stop 期間内に決算がある場合は警告を必須表示**
     (登録自体は人間の明示 `earnings_acknowledged: true` で可能。黙って決算跨ぎを防ぐ)
2. **信用残(週次)** — derived: `jquants_margin_v1`。feature: 信用倍率・買い残/売り残の前週比。
   research/evidence の需給欄に「UNKNOWN → 実数」で反映。2737 で手動確認した項目の自動化。
3. **空売り比率 / 業種別指数 / 投資部門別売買動向** — プラン内で取得可能なものだけ。
   **プランに無いものは「未取得(プラン外)」と正直に記録し、勝手に上位プラン前提の設計をしない。**

### 規律
- 取得系は既存 sync/fetch の流儀(raw+provenance+PIT+redact+tos_personal_use_confirmed gate)。
- まず `fetch-jquants-bulk list` 等で**プランに何が含まれるか実確認**してから SPEC を書く。

---

## Phase RG-1: レジーム(地合い)タグ

- 入力: jquants manifest の分布(return_20d/60d の median・positive_rate)
- 単純規則で3値: `trend_up`(positive_rate_20d>0.6 かつ median>0) / `trend_down`(<0.4 かつ <0) / `range`(それ以外)
- 用途: バックテスト結果と紙上トレード台帳に regime を**タグとして付与**するだけ。
  レジーム自体で売買を判断しない(タグ=後の分解分析用)。
- 出力: investor-brief の Market Snapshot に regime 1行を追加。

---

## Phase SG-1: シグナル合流(confluence)

- 定義: 検証入口に上げる条件を「**独立レーンの N-of-M 一致**」にする:
  ① 価格・出来高(J-Quants derived) ② 観測レーン注目(株探 trigger_families)
  ③ ニュースイベント(日経 metadata の event_type) ④ データ品質フラグ無し(必須条件)
- 例: ④を満たし、①〜③のうち2つ以上が同方向 → 検証入口。1つだけ → 監視のみ。
- 出力は既存 investor-brief / selection の枠内(新しい推奨形式を作らない)。
- 効果測定: 合流あり/なしの検証入口それぞれの「その後5日リターン分布」を月次で比較記録
  (これも予測ではなく、フィルタの較正)。

---

## 実装順序と理由
1. **BT-1**(核。紙上トライアルの setup を歴史的期待値で選べるようになる)
2. **DT-1 の決算カレンダー**(小さく即効。決算跨ぎ事故を塞ぐ)
3. **DT-1 残り(信用残→空売り→指数)**
4. **RG-1**(BT-1の結果を分解できるようになる)
5. **SG-1**(全レーンが揃ってから)

## 各フェーズの進め方(共通)
1. SPEC 草案(入力/出力/PIT/テスト一覧/DoD)を出して**停止**、人間の承認を待つ
2. 実装+テスト → 全テスト通過
3. Codex逆監査(観点: 先読み/多重比較/禁止語/コスト/既存I/O非破壊)
4. Obsidian に開発ログ(何を/なぜ/検証結果/残課題)
5. 完了後に次フェーズへ

## この基盤が答えるべき問い(忘れないこと)
「どの銘柄が上がるか」ではない。
**「自分の setup は、コスト控除後・検証期間で、期待値プラスか」**。
答えが全 setup マイナスなら、それはスイング参入を見送る立派な根拠になる(検証の成功)。
