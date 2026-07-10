# CLAUDE_HANDOFF — V2移行の確定事実(公式移行ガイドをオーナーが提示)(司令塔・Codex共用)

クラウド側裁定者より。オーナーが J-Quants 公式「V1→V2変更点」文書を提示した。
D0-R(299f478…)の前提仮説は**公式に確定**した。本文書は D0-R と watchlist V2移行の
両タスクに適用する確定事実の補足であり、D0-R の指示自体は変更しない(sha256も従来のまま)。

## 1. 確定: 前回D0の403は「V1旧名」が原因(プラン除外ではない)
公式対応表より(D0-R対象分の抜粋・事実):
| データ | V1(前回403) | V2正式名(D0-Rで叩く) |
|---|---|---|
| 決算発表予定日 | /v1/fins/announcement | **/v2/equities/earnings-calendar** |
| 信用取引週末残高 | /v1/markets/weekly_margin_interest | **/v2/markets/margin-interest** |
| 日々公表信用残 | /v1/markets/daily_margin_interest | **/v2/markets/margin-alert** |
| 業種別空売り比率 | /v1/markets/short_selling | **/v2/markets/short-ratio** |
| 空売り残高報告 | /v1/markets/short_selling_positions | **/v2/markets/short-sale-report** |
| 財務諸表BS/PL/CF | /v1/fins/fs_details | **/v2/fins/details** |
| TOPIX指数 | /v1/indices/topix | **/v2/indices/bars/daily/topix** |
| 認証トークン発行 | /v1/token/auth_* | **廃止**(x-api-key ヘッダー) |
※ D0-R は依然必要(**プラン別の提供範囲**は別問題。公式の「契約ごとに利用可能なAPI」
頁と実測の両方で確認する)。ただし結果は200側に倒れる公算が大きくなった。

## 2. 実装上の最重要注意: V2はカラム名が短縮形(watchlist移行の事故ポイント)
株価四本値の例: Close→**C**、Open→**O**、High→**H**、Low→**L**、Volume→**Vo**、
AdjustmentClose→**AdjC**、AdjustmentFactor→**AdjFactor** 等。
レスポンスは原則 `{"data":[...], "pagination_key":"..."}` 構造に統一。
→ **watchlist V2移行の必須条件(再掲・強化)**: V1カラム名→V2短縮名のマッピングは
クライアント内で吸収し、**derived / fetch-jquants の出力形式は1文字も変えない**。
テストは V2形式の合成レスポンス(短縮カラム+dataエンベロープ+pagination_key)で書く。

## 3. レートリミット(プラン別・分あたり): Free 5 / Light 60 / Standard 120 / Premium 500
- D0-R のプローブは最小限に(1エンドポイント1リクエスト+失敗時のみ再試行)。
- watchlist R0 は人間指定銘柄のみの設計なので上限に触れない見込みだが、
  リトライは指数バックオフで実装(429を握りつぶさない・ログに記録)。

## 4. 重要な制度変更: V2 Premium は「過去20年分まで」(V1は無制限だった)
含意(裁定):
- BT-1 の全期間 train(2008-05〜)は**ローカル data/raw に保存済みのため影響なし**。
- ただし今後、APIの提供窓が転がる(2028年頃には2008年分がAPIから消え始める)。
  → **「data/raw・derived を消さない」既存ルールの重要度が上がった**。ローカルrawは
  再取得不能になり得る一次資産である。バックアップ(Time Machine等)の状態を
  次回STATUSで1行報告すること。
- 将来の再バックテストは「APIから再取得」でなく「ローカルraw再利用」を前提に設計する
  (precompute/cacheの設計はこの方針と既に整合)。

## 5. 適用先
- **D0-R**(司令塔): §1の表のV2名でプローブ。手順・報告様式は 299f478… のまま。
- **watchlist V2移行**(Codex・オーナーの書き手宣言後): §2のカラム吸収+§3のバックオフを
  実装条件に追加。単独コミット+全テスト。
- 期間20年制限(§4)は STATUS 報告項目に追加。

規律不変: push無し / 秘密非表示 / レートリミット尊重 / 出力形式の互換維持 /
売買推奨・ランキングなし。
