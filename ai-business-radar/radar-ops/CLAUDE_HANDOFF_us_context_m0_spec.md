# CLAUDE_HANDOFF — 米国地合いレーン M0 実装仕様 v2(司令塔用・Phase 2b)

**v2改訂(2026-07-10)**: 設計審査パネル(Codex対抗提案・全12項目採用)を反映。v1(afed35f)を置換。
目的は不変 = 地合いの**観測**(ISSUE_MAP 論点5)。売買シグナルではない。

## 0. オーナー事前作業
- FRED無料APIキーを取得し、Macで .env に `FRED_API_KEY=...` を直接記入(チャットに貼らない)。

## 1. 実装順序(重要・v2で変更): まず契約書、次に実装
**D0 → SOURCE_CONTRACT確定 → 実装**、の3段。いきなり実装しない(Codex提案11)。
- **D0(読み取り・実測)**: 各系列のURL/ライセンス・ToS/更新時刻の実測/欠損時挙動/最新判定条件。
- **SOURCE_CONTRACT_us_context_m0.md を先に作成**(各系列の契約表)。裁定者が確認後に実装GO。

## 2. 二段階発火(Codex提案1・10採用)
- **07:00 JST = partial probe**(間に合う系列だけ取得)/ **08:30 JST = retry/finalize**。
- daily-update/brief は**最新の非stale runだけ**を読む。**全系列成功を待たない**(揃わない系列はUNKNOWN)。

## 3. 系列別の採用方針(Codex提案3・12 = M0-lite・信頼性順)
| 系列 | ソース | M0での扱い |
|---|---|---|
| 米10年/2年金利・長短差 | FRED(DGS10/DGS2) | **本採用**(更新が間に合う) |
| S&P500 | FRED(SP500) | **鮮度条件付き採用**(更新が07:00に間に合わない日はUNKNOWN・08:30で再取得) |
| VIX | Cboe日次CSV | **本採用・鮮度ゲート必須**(観測日=対象米セッション日の時のみ文言化。不一致はUNKNOWN(stale_source)) |
| ドル円 | FRED(DEXJPUS) | **stale注意付き**(NY正午値・遅延あり。鮮度が1営業日超なら文言生成禁止=UNKNOWN)。FX専用ソースは別裁定 |
| Nasdaq100・SOX | D0で安定CSVソースを探す。Stooqは**candidate/backup**(HTMLを返した実績あり) | 安定ソースが見つかるまで**UNKNOWN許容で開始**(誤ったFACT注入より安全) |
| 日経先物ナイト | J-Quants NK225F(EO/EC) | D0でプラン可否・更新時刻を実測 |

## 4. 鮮度とPIT(Codex提案4・7・8採用)
- **asofを3つに分離(必須)**: `run_date_jst` / `us_session_date` / `source_observation_date`。
  1日変化はカレンダー前日でなく「**前回有効観測日**」と比較。
- **正本は immutable な `market_context_runs.jsonl`**(追記専用・同日リトライも別行)。
  `<date>.json` は最新ビューの再生成扱い(上書き禁止の対象を明確化)。
- 各系列に `status: ok | stale | missing` を持たせ、statusがokの系列のみ文言化。

## 5. 文言(Codex提案5採用・最重要 — 推奨誤読の防止)
- 「追い風/逆風」は**廃止**。観測語に弱める:
  例) `SOX -2.1%(as_of 7/8): 半導体・電子材料に外部地合いの負圧を確認(推論/INFERENCE)`
  「観測上の圧力: positive/negative」「検証時の注意」の枠でのみ表現。
- **必ず実数・前日比・as_of を併記**(Codex提案6)。閾値補正(実現ボラ等)はM1送り。
- 固定の但し書き: 「本行は地合いの観測であり売買推奨ではない(ISSUE_MAP論点5)」。

## 6. 注入先(不変)
- daily-update サマリ1行 + investor-brief 冒頭3行以内。
- **codex_selection・検証優先度・シグナルへの接続は禁止**。観測のみ。

## 7. launchd実務(Codex提案9採用)
- LaunchAgentは対話シェル環境を読まない。スクリプトが .env を**明示ロード**すること。
- D0受領条件に「launchd実行時にキーが設定済み/未設定だけをログ(値は出さない)」を追加。

## 8. テスト
- 二段階発火(07:00で欠け→08:30で補完)/ 各系列のstale判定 / 3つのasof分離 /
  JSONL追記(上書きなし)/ 全系列欠損でもUNKNOWN表示で完走 / 文言に推奨語が出ない /
  FORBIDDEN非抵触 / 既存回帰なし。

## 9. DoD
- SOURCE_CONTRACT確定(裁定者確認)→ 実装 → 二段階発火の実発火目視 → 単独コミット →
  Obsidian記録 → 確認依頼MD(報告リポ経由)。

## 10. 位置づけ
- ISSUE_MAP論点5の計器 / judgment_lane の相場観採点の文脈データ。
- us_evidence(休眠)とは別物・不介入継続。RG-1は観測が溜まってから別裁定。

規律不変: PIT / UNKNOWN正直表示 / 推奨語禁止・シグナル接続禁止 / 秘密は.env / push無し(報告リポのみ)。
