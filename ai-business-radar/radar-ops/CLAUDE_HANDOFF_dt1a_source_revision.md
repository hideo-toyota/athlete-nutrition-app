# CLAUDE_HANDOFF — DT-1a データ源改訂: J-Quants→JPX公式(司令塔用)

クラウド側裁定者より。D0報告(1ebd73d)を受理した。停止・差し戻しは仕様どおりで正しい。
クラウド側でWeb検証を行った結果、**選択肢1・2は403が解決しても目的を満たさない**ことが
判明したため、**選択肢3(別データ源)を採用**する。

## 1. クラウド側Web検証の結果(出典は本文書末尾)
- **J-Quants /fins/announcement の仕様**: 全プランで利用可だが、返るのは
  **翌営業日分のみ・3月期/9月期決算会社のみ**(17:30以降更新)。
  → 仮に v1 資格情報を追加して 403 を回避しても、**horizon が1営業日**であり、
  「次の5営業日窓」の M 算出には構造的に不足。**選択肢1・2は棄却**(プラン課金も不要)。
- **JPX(日本取引所)が決算発表予定日を公式サイトで無料公開**している:
  `https://www.jpx.co.jp/listing/event-schedules/financial-announcement/index.html`
  Excel形式・決算期末の翌月上旬に掲載後、適宜更新。別に有料CSVサービス(毎営業日更新)も
  存在するが、まず無料版で足りるかを確認する。
- 注記(正直な限界): クラウド側の取得環境からは jpx.co.jp への直接アクセスが
  ブロックされたため、**ページ内のファイル形式・列構成・掲載期間は未実測**。
  そのため下記 D0b を Mac 側で行う。

## 2. D0b: JPX無料版の能力調査(Mac側・読み取りのみ・実装前に報告)
kabutan観測レーンと同じ礼節(honest UA・アクセスは最小限・robots/利用規約の確認)で:
1. 上記ページから Excel ファイルの URL パターン・更新日・対象範囲
   (全上場か/本決算・四半期の別)を実測
2. 何営業日〜何か月先までの予定が載っているか(5営業日窓に足りるか)
3. ダウンロードして列構成を確認(コード/社名/発表予定日/決算期 等)
4. 利用規約上、個人の私的分析利用の範囲で問題ないことの確認(tos確認をprovenanceに記録)
**D0b の結果が「5営業日窓に足りる」なら、そのまま実装に進んでよい**(再差し戻し不要)。
足りない・形式が使えない場合のみ停止し、有料CSVサービス(JPX総研)の検討をオーナーに上げる。

## 3. 実装仕様の変更点(dt1_spec.md からの差分。他は全て有効)
- データ源: J-Quants announcement → **JPX公式 決算発表予定日(無料Excel)**
- raw: `data/raw/jpx/financial_announcement/<fetch_date>.<ext>` + provenance
  (source_url / fetched_at / tos_personal_use_confirmed)
- derived 名称: `jquants_earnings_calendar_v1` → **`earnings_calendar_v1`**(source列に jpx_official)
- 取得頻度: 平日1回(JPXの更新が「適宜」のため、**鮮度ゲート3営業日は据え置き**で防御)
- 営業日判定: J-Quants **markets/calendar(200確認済)** を使用(ここは当初仕様のまま)
- PIT追記型・決算接近フラグ・W2のM実数化・テスト要件・DoD は **dt1_spec.md のまま変更なし**

## 4. 先行実装の承認
司令塔が申し出た「W2の営業日判定パート(markets/calendar)だけ先に入れる」は**承認**(GO)。
D0b と並行してよい。単独コミット。M は calendar 完成まで UNKNOWN のまま(正直表示維持)。

## 5. DT-1b(信用残)/ DT-1c(空売り比率)の見通し(着手は禁止のまま)
J-Quants 該当エンドポイントはプラン除外で確定。ただし JPX は信用取引残高(週次)・
空売り集計(日次)も公式サイトで公開しており、DT-1a と同じ「JPX公式+PIT追記」方式で
実装できる可能性が高い。**DT-1a 完了・監査後に、同様の D0 から始める**(本文書では着手しない)。

## 出典(クラウド側検証)
- J-Quants プラン別データ範囲: jpx.gitbook.io/j-quants-ja/outline/data-spec
- J-Quants データ更新タイミング(翌営業日分・17:30以降): jpx.gitbook.io/j-quants-ja/outline/data-update
- JPX 決算発表予定日(無料): www.jpx.co.jp/listing/event-schedules/financial-announcement/index.html
- JPX 決算発表予定日情報提供サービス(有料CSV・毎営業日更新): www.jpx.co.jp/markets/paid-info-listing/earnings/index.html

規律は不変: push無し / PIT / 履歴append-only / raw再配布禁止 / 売買推奨・ランキングなし /
JPXデータも本文の転載はせず観測メタデータ(コード・日付)のみ derived 化。
