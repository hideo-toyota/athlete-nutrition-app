# CLAUDE_HANDOFF — スイング分析基盤ロードマップ v2(backtest + data + confluence + regime)

> v2 (2026-07-02): Codex レビューを反映。追加: 市場環境フィルター / 損失制御 / 決算跨ぎルール /
> 流動性(参加率)制約 / exit schema 固定 / 結果のバケット分解 / 過剰最適化ガード強化 / no-trade計測。
> 方針: **「勝つ」より先に「続ける」ためのルールを仕様に入れる。**

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
  終値依存なら同日終値エントリーは先読み=禁止)。
- APIキー/.env/raw本文を表示・LLM投入しない。ネットは radar/sources/ に閉じる。
- canonical root guard の対象に含める。既存コマンドのI/Oを壊さない。テスト無し実装はマージ禁止。
- 自動売買はしない(恒久)。

---

## Phase BT-1: バックテスト基盤(最優先)

### 目的
事前登録 setup の**歴史的期待値(R単位)**を、取得済み J-Quants 日足から測る。
「シグナル=歴史的に期待値プラスと検証済みの事前登録条件」を実データで運用可能にする。

### 入力
- `data/raw/jquants/bulk/equities/bars/daily/premium`(取得済み日足。ネット不要)
- `fins/summary` の DiscDate(**過去の決算発表日**。決算跨ぎ判定に使う。DT-1を待たない)
- setup registry(新規): `radar/backtest/setups.py` に**コードで事前登録**。日足で定義可能な3つから:
  1. `pullback_in_trend` — 60日リターン上位分位 かつ 直近5日で-5%以上の押し → 翌日寄付
  2. `range_break` — 直近60日高値を終値更新 かつ 出来高が20日平均の1.5倍以上
  3. `overheat_fade`(ショート・紙上のみ) — 20日+40%超 かつ 高値から2日連続陰線
- 各 setup = {entry条件(**最大4条件**), stop規則, exit規則, フィルター群(下記)}

### ユニバース/流動性制約(実運用で執行可能なものだけ検証する)
- 除外: ETF/REIT(`その他`)、split_artifact_warning、データ品質フラグ
- `min_avg_turnover_jpy_20d`: 売買代金20日平均 5,000万円未満は除外
- **参加率制約**: 想定売買代金(サイズ×価格)が平均売買代金の **1%以内** に収まらない銘柄・
  サイズはイベント無効(理論上勝てても滑って再現できないため)

### 市場環境フィルター(事前登録された機械的ルールとして)
- regime 定義(RG-1 と共通実装): TOPIX or 全銘柄breadth から
  `risk_on`(positive_rate_20d>0.6 かつ 20日median>0) / `risk_off`(<0.4 かつ <0) / `neutral`
- ボラ急上昇フラグ: 指数の日次リターン標準偏差(20日)が 60日比 1.5倍超
- 各 setup は許可 regime を**事前宣言**(例: pullback_in_trend は risk_off で新規エントリー無効)
- **注意**: フィルターは裁量ではなく事前登録ルール。ただしフィルター追加=自由度追加なので
  **attempts_log に1試行として数える**。フィルター有/無の両方を train で計測し差を記録する。

### 決算・イベントの扱い(明記必須。曖昧=バックテストと実運用の乖離)
- **基準ルール: 決算跨ぎ禁止**。DiscDate の **3営業日前〜翌1営業日** はエントリー禁止、
  保有中に決算日が来る場合は **前営業日終値で強制イグジット**(exit_reason=event)。
- 「跨ぎ許可」バリアントを検証したい場合は**別 backtest_id**として実行(混ぜない)。
- 紙上トライアル側の earnings_acknowledged ルールと整合させる。

### exit schema(今すぐ固定・BT-1で実装するのは2つだけ)
`exit_reason` enum を今固定: `time | stop | trailing | event | thesis_broken | manual`
- BT-1 実装: `time`(保有日数上限) と `stop`(事前固定価格) と `event`(決算前強制)のみ
- `trailing` / `thesis_broken` は schema 予約のみ(実装は後続。台帳・出力の互換を先に確保)

### 損失制御(「続ける」ためのルール)
- イベント単位: リスク1%/トレード(swing_paper_trial と同一)
- **ポートフォリオシミュレーション**(同時保有2件・資金100万円で逐次実行)に以下を実装:
  - 日次損失 **-2R** で当日新規停止 / 月間 **-5R** で当月新規停止 /
    累積DD **-10R** で backtest 内でも「実験停止」を記録(=実運用なら退場ラインだった事実を残す)
- これらの発動回数・停止日数も結果に出す(下記 no-trade 計測)

### 検証規律(本体)
1. **仮説文の事前固定**: 各 setup は実行前に「なぜ効くと考えるか」を1段落で registry に固定。
   **後から条件を変えたら別 backtest_id**(value-audit と同じ思想)。
2. **train/test分割**: train=先頭〜2025-06 / test=2025-07〜直近。調整は train のみ。
   **test は各 backtest_id につき1回だけ**。結果の改変・再実行禁止。
3. **多重比較の記録**: 試した setup/パラメータ/フィルター有無は**全て**
   `outputs/backtests/attempts_log.jsonl` に append-only(お蔵入り禁止)。
   出力に「n個試行中k個が正」を明記。
4. **コスト**: 往復0.2%。**サンプル下限**: イベント<50 は sample_too_small。

### 結果の分解(バケット別・どこで勝ちどこで負けるか)
以下の軸で分解して出力(**各セルのイベント数<20 は UNKNOWN 表示**。細切れの偽精度を出さない):
- regime別(risk_on/off/neutral) / 時価総額帯(小型<500億/中型/大型>3000億) /
  PER帯・PBR帯(分位3分割) / momentumバケット(20日リターン分位) /
  決算後経過(直後5営業日以内か否か) / 出来高急増の有無
※ 全軸同時のクロスは出さない(セルが細かすぎる)。**1軸ずつ**の分解に限定。

### no-trade を正式な結果として計測
metrics に必ず含める: `no_trade_days`(シグナル無し日数) / `risk_off_blocked_days`
(地合いフィルターで見送った日数) / `event_blocked_count`(決算除外件数) /
`loss_halt_days`(損失制御による停止日数)。
**シグナルが無い日は失敗ではなく正常な防御**、と出力ヘッダに明記。

### 出力
- `outputs/backtests/<backtest_id>_<train|test>.md/json`:
  期待値(R)/勝率/平均勝ちR/負けR/最大DD(R)/イベント数/年別/バケット別/no-trade計測/停止発動履歴
- **銘柄リストは出さない**(setup統計のみ。例示は匿名化数件まで)
- CLI: `python3 -m radar backtest --setup <name> --period train|test [--dry-run]`

### テスト要件(合成データ)
- 先読み検出(翌日寄付エントリー) / train・test分離 / コスト・R計算 /
  決算跨ぎ強制イグジット / 参加率制約の除外 / regimeフィルターの発動 /
  損失制御(日次-2R停止)の発動 / sample_too_small・バケット<20のUNKNOWN / 禁止語

### 完了条件(DoD)
py_compile / unittest 全通過。3 setup(フィルター有無 各2系統)の train 結果と attempts_log。
**test は人間の承認後、backtest_id ごとに1回だけ。**

---

## Phase DT-1: J-Quants 未使用データの解放
1. **決算発表予定日(将来分)**【最優先・小さい】 — derived: `jquants_earnings_calendar_v1`。
   紙上トライアルの事前登録時、time_stop 内に決算があれば**警告必須**
   (登録は `earnings_acknowledged: true` で可能。黙って跨ぐのを防ぐ)。
   ※過去分は BT-1 が DiscDate から導出済み。ここは**将来日程**の取得。
2. **信用残(週次)** — `jquants_margin_v1`。信用倍率・買い残/売り残前週比。evidence の需給欄に反映。
3. **空売り比率 / 業種別指数 / 投資部門別** — プラン内のみ。プラン外は「未取得(プラン外)」と正直に記録。
- 取得系は既存の流儀(raw+provenance+PIT+redact+tos_personal_use_confirmed gate)。
- **まず `fetch-jquants-bulk list` でプラン内容を実確認してから SPEC を書く。**

## Phase RG-1: レジーム実装の共通化
- BT-1 の市場環境フィルターと同一実装を investor-brief / 紙上台帳タグに供給(regime 1行表示)。
- 用途は「事前登録フィルター」と「事後の分解タグ」のみ。裁量トリガーにしない。

## Phase SG-1: シグナル合流(confluence)
- 検証入口の条件 = データ品質フラグ無し(必須) + 独立レーン(価格出来高/株探注目/日経イベント)の
  2-of-3 一致。1つだけなら監視のみ。
- 出力は既存 investor-brief / selection の枠内。フィルタ効果(合流有無別のその後5日リターン分布)を
  月次で較正記録(予測ではない)。

## 実装順序
1. **BT-1**(市場環境フィルター・損失制御・決算跨ぎ・流動性制約を含む本体)
2. **DT-1-1 決算カレンダー(将来分)**(小さく即効)
3. **DT-1 残り(信用残→空売り→指数)**
4. **RG-1 共通化** → 5. **SG-1**

## 各フェーズの進め方(共通)
1. SPEC 草案(入力/出力/PIT保証/テスト一覧/DoD)を出して**停止**、人間の承認を待つ
2. 実装+テスト → 全通過 → 3. Codex逆監査(先読み/多重比較/禁止語/コスト/決算跨ぎ/既存I/O)
4. Obsidian に開発ログ → 5. 次フェーズ

## この基盤が答えるべき問い
「どの銘柄が上がるか」ではない。
**「自分の setup は、コスト控除後・検証期間・執行可能な流動性・地合いフィルター込みで、期待値プラスか」**。
そして同じ重みで:**「どんな日はやらないか。どこまで負けたら止めるか。」**
全 setup マイナスならスイング見送りの根拠になる(検証の成功)。
