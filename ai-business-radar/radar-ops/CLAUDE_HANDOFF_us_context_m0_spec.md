# CLAUDE_HANDOFF — 米国地合いレーン M0 実装仕様(司令塔用・Phase 2b発効)

クラウド側裁定者より。棚卸し(CONFIRM_us_sector_inventory_20260709)の確定事実
「**米国マクロ市況の取得実体は現状ゼロ・us_evidenceは休眠孤立レーン(不介入継続)**」を前提に、
新規レーンとして設計する。目的は**地合いの観測**(ISSUE_MAP 論点5の計器)であり、
売買シグナルではない。「大きく負ける日を避ける」ためのBT-1系防御思想の延長。

## 0. オーナーの事前作業(1つ・5分)
- FRED(セントルイス連銀)の**無料APIキー**を登録取得し、Macのターミナルで .env に
  `FRED_API_KEY=...` を直接記入(いつもの流儀: チャットに貼らない)。

## 1. データソース(全て無料・日次・遅延許容)
| 系列 | ソース | 備考 |
|---|---|---|
| 米10年金利・2年金利・長短差 | FRED API(DGS10/DGS2) | 公式・無料キー |
| ドル円 | FRED(DEXJPUS) | 同上 |
| S&P500 | FRED(SP500) | 同上 |
| VIX | Cboe公式の日次履歴CSV | 遅延/日次で十分と裁定済み |
| Nasdaq100・SOX | 実装D0で無料日次ソースを選定(候補: Stooq等)。出典+as_of必須・ToS確認 | 取れない系列はUNKNOWN表示で開始してよい(全系列揃うまで待たない) |
| 日経先物ナイトセッション | J-Quants /derivatives/bars/daily/futures(NK225F・EO/EC列) | D0でプラン可否と更新時刻を実測 |

## 2. 実装
- `scripts/automation/us_market_context.py` + LaunchAgent `com.radar.us-context`
  (**平日07:00 JST** = 米市場クローズ後・東京寄り前)。
- 出力: `data/derived/market_context/<date>.json`(PIT追記・上書きしない)
  形式例: asof / sp500_1d / nasdaq_1d / sox_1d / vix_level / vix_1d / us10y_bp_1d /
  us2y_bp_1d / usdjpy_1d / nk_futures_night(EO→EC) / sources(出典+取得時刻) / missing[]
- **翻訳ルール(固定文言・INFERENCE明記・変更は裁定のみ)**:
  - SOX ±2%超 → 「半導体・電子材料: 追い風/逆風」
  - Nasdaq ±1.5%超 → 「グロース系: 追い風/逆風」
  - ドル円 ±1円超 → 「輸出(自動車等): 追い風/逆風・内需輸入コスト: 逆/順」
  - 米10年金利 ±10bp超 → 「高PER系: 逆風/追い風」
  - VIX 25超 or 前日+20%超 → 「ボラ上昇: 新規検証は縮小が既定」
  - 閾値はconfig(`us_context.*`)・ハードコード禁止。該当なしの日は「特記なし」
- **注入先(2箇所のみ)**: daily-update サマリに1行(「米地合い: SOX+2.1% 半導体追い風 /
  VIX 14.8 特記なし」形式)+ investor-brief 冒頭に3行以内のセクション。
  **codex_selection・検証優先度・シグナルへの接続は禁止**(観測のみ)。
- 欠損の扱い: 取得失敗した系列は前日値を出さず **UNKNOWN(取得失敗)** と正直表示
  (educationの完全性ゲートと同思想)。

## 3. テスト(合成)
- 各翻訳ルールの閾値境界 / 全系列欠損日でもUNKNOWN表示で完走 / PIT追記(上書きなし) /
  FORBIDDEN非抵触 / 既存テスト回帰なし

## 4. D0(実装前・30分)
- FREDキー疎通 / Cboe CSVの形式 / Nasdaq・SOXの無料ソース選定(ToS・出典明記) /
  NK225F のEO/EC更新タイミング実測(07:00発火で前夜分が取れるか)

## 5. DoD
- 初回実発火で market_context.json 生成+daily-update/briefへの注入を目視 /
  全テスト通過 / 単独コミット(D0報告含む) / Obsidian記録 / 確認依頼MD(報告リポ経由)

## 6. 位置づけの明記
- ISSUE_MAP 論点5の計器。judgment_lane の相場観採点(MV系)の文脈データにもなる。
- us_evidence(休眠)とは別物・不介入継続。RG-1(レジーム定式化)は本レーンの観測が
  溜まってから別途裁定(観測なしにレジーム式を作らない)。

規律不変: PIT / UNKNOWN正直表示 / シグナル接続禁止 / 秘密は.env / push無し(報告リポのみ)。
