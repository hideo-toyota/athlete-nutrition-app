# CLAUDE_HANDOFF_phase2c1_snapshot_spec.md — Phase 2c-1「financial snapshot」実装 SPEC(発行)

- doc-id: `CLAUDE_HANDOFF_phase2c1_snapshot_spec`
- as_of: 2026-07-11
- writer: クラウド裁定者(cloud adjudicator)
- 位置: `ai-business-radar/radar-ops/CLAUDE_HANDOFF_phase2c1_snapshot_spec.md`
- 上位: `ANALYSIS_QUALITY_RULES.md` / 順序: `CLAUDE_HANDOFF_reading_layer_integrity.md`(2c-1→2c-2→2c-3→(指数取得)→2c-4)/ 投入根拠: 月次投入ゲート §5 の**振替条項発動**(M0 v2 は契約確認+FRED キー未充足のため、当月投入枠を 2c-1 に振替)
- 状態: **発行(実装 GO)**。書き手=司令塔(既定)。単独コミット+テスト+CONFIRM_ 報告。

---

## 0. 目的と問題設定(2c 裁定の核心の再掲)
問題は取得層でなく**読み取り層**にある: EDINET financials は 3818 社分取得済みだが、読む側が**直近400スライスのみ参照**しており、(a) 銘柄によって参照される財務の as_of がバラつく、(b) 同一 asof を意図した複数の読み手が別の値を見る、が起こり得る。2c-1 は**単一 asof で全ユニバースを整合的に読む snapshot 層**を作り、以後の readiness(2c-2)・判断採点(2c-4)の土台にする。

## 1. D0(読み取りのみ・実装前に実測)
裁定者は Mac のコードを直接見られないため、**ファイルパス・関数名は D0 で確定**する(本 SPEC の名称は指示的)。
1. derived financials の**読み手を全列挙**(grep: 直近400スライス参照箇所を file:line で特定)。
2. 現行の不整合の**実例を1件以上採取**(同一銘柄で読み手により異なる財務 asof が使われる、または スライス外銘柄が財務欠損扱いになる例)。
3. 全取得コーパスの実勢を計数: 社数・銘柄別の最新 filing asof 分布・重複 filing の有無。
→ D0 結果を CONFIRM_ に添付(実装と同便で可)。

## 2. 実装契約
### 2.1 snapshot ビルダ(決定論・LLM 不使用)
- 新規 `radar/…/build_financials_snapshot`(CLI: `build-financials-snapshot --asof <date>`)。
- **選定規則(PIT)**: 各社につき「**filing asof ≤ snapshot asof の最新 filing**」を1件選ぶ。asof より後の filing は**参照しない**(look-ahead 禁止)。
- 出力 `data/derived/financials_snapshot/<asof>.(jsonl|json)`: 1社1行 — code / 採用 filing の asof / 出典 doc 識別子 / 採用フィールド群 / `missing_reason`(該当 filing 無し等)。**既存 asof の上書き禁止**(PIT 追記)。
- 決定論: 同一入力での再ビルドは**バイト同一**。乱数・現在時刻を選定に使わない(asof は引数)。

### 2.2 読み取りアクセサ(単一入口)
- 新規 `load_financials_snapshot(asof)` を**唯一の読み取り入口**とし、D0 で列挙した読み手を順次これへ差替(2c-1 では**既存出力に影響しない読み手から最小限**。全面切替は 2c-2 以降の裁定)。
- **サイレントフォールバック禁止**: snapshot 不在時に旧スライスへ黙って落ちない(明示エラーまたは UNKNOWN 表示)。

### 2.3 不変条件
1. **単一 asof 整合**: 同一 asof を指定した全読み手は同一値を見る(2c 停止条件①の裏返し)。
2. **look-ahead 禁止**: snapshot asof 超の filing 混入ゼロ。
3. **欠損の正直表示**: filing 無し銘柄は理由付き `missing_reason`(前値・近傍値で埋めない)。カバレッジ(n/全社)を doctor か CONFIRM_ に計上。
4. **既存出力形式の不変**: 差替済み読み手の出力は**バイト等価または明示的改善のみ**(差分は CONFIRM_ に開示)。

## 3. テスト(最低限・合成コーパス)
(a) 複数 filing から「asof 以下の最新」を選ぶ / (b) asof 境界: 当日=採用・翌日=除外 / (c) filing 無し銘柄= missing_reason 付き非補間 / (d) 再ビルドのバイト同一(決定論) / (e) アクセサ経由の読みが snapshot と一致・フォールバック非発生 / (f) 既存読み手差替の回帰(バイト等価 or 開示差分) / +フルスイート回帰。

## 4. DoD
① D0 報告(読み手列挙・不整合実例・コーパス計数) ② 実装+テスト全通過・フルスイート回帰 OK ③ **実データで最新 asof の snapshot を1本ビルド**し、カバレッジ実数(採用/欠損内訳)を報告 ④ CONFIRM_ 配送。

## 5. 非スコープ(明示)
readiness ゲート(2c-2)/ CA 隔離(2c-3)/ 判断採点(2c-4)/ TOPIX·33業種指数の取得(別小仕様)/ **新規データ取得ゼロ**(既取得の読み方のみ)/ 売買推奨・順位・価格目標なし。

## 6. 停止条件(2c 裁定を継承)
snapshot 値の単一 asof 読み不一致 / readiness の偽 OK / 正常行巻き込み / 既存出力形式の非互換破壊 → **停止・差し戻し**。D0 で「400スライス参照」の前提自体が事実と異なる場合も**着手前に停止・報告**(推測で前提を作らない)。
