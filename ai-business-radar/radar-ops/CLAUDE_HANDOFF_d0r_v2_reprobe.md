# CLAUDE_HANDOFF — D0-R: V2正式名での再プローブ(前回D0の判定を訂正の可能性)(司令塔用)

クラウド側裁定者より。オーナーが J-Quants **V2 API ドキュメントの目次**を提示し、
前回D0(1ebd73d)の「403=プラン除外で確定」判定に**系統的な誤りの疑い**が見つかった。

## 0. 訂正の根拠(裁定者も前回これを見逃した。正直に記録する)
前回D0で 200 だったパス(equities/master, equities/bars/daily, fins/summary, fins/dividend,
markets/calendar)は**すべてV2正式名**。403 だったパス(fins/announcement,
markets/weekly_margin_interest, markets/short_selling)は**すべてV1旧名**。
V2では名称が変更されている:
- 決算発表予定日: `/equities/earnings-calendar`(旧 fins/announcement)
- 信用取引週末残高: `/markets/margin-interest`(旧 markets/weekly_margin_interest)
- 業種別空売り比率: `/markets/short-ratio`(旧 markets/short_selling)
→ **403はプラン除外ではなく旧名の可能性が高い。**

## 1. D0-R(読み取りのみ・実装しない・1時間以内)
Bulk(/bulk/list?endpoint=)と、可能ならREST直で、**V2正式名**を再プローブし
ステータスと(200なら)レスポンス構造・データ horizon を報告:
1. `/equities/earnings-calendar` … 何日先まで返るか(前回のJPX判断に影響)
2. `/markets/margin-interest`(週末残高・銘柄別か)
3. `/markets/short-ratio`(業種別)・`/markets/short-sale-report`(空売り残高報告)・
   `/markets/margin-alert`(日々公表信用残)
4. `/fins/details`(BS/PL/CF)・`/edinet/major-shareholders`・`/edinet/cross-shareholdings`
5. `/indices/bars/daily/topix`
6. `/markets/breakdown`・`/equities/investor-types`(優先度低・ステータスのみ)
※ V2の「エンドポイント・パラメータの変更」「契約ごとに利用可能なAPI」のドキュメント頁も
参照し、プラン表の記載をレスポンスの実測と突き合わせる(文書と実測の両方を報告)。

## 2. D0-R の結果ごとの方針(先に決めておく)
- **earnings-calendar が200かつ5営業日窓を満たす** → DT-1a は**JPX実装を維持**したまま、
  J-Quants を**第2ソース(クロスチェック)**として追加する提案を出す(置き換えは急がない。
  二重ソースの不一致検出は価値。earnings_calendar_v1 は source 列で両立可能な設計済み)。
- **margin-interest / short 系が200** → DT-1b/c は**JPXスクレイピングではなくV2 APIで実装**
  (構造化APIが上位。仕様は dt1_spec.md §DT-1b/c の縛りのまま、取得部だけ差し替え)。
- 403のままなら前回判定が確定 → JPX公式路線を継続。

## 3. 未活用エンドポイントの棚卸し(D0-Rと同時に、現行レーンとの対応だけ報告)
実装はしない。「どのレーンに効くか」の1行マッピングのみ:
- `/fins/details`(BS/PL/CF) → value-audit の FACT 供給(EDINET原文パースの補完・
  カバレッジ加速の可能性。EDINET班の任務との関係を整理)
- `/edinet/major-shareholders`・`/edinet/cross-shareholdings` → value-audit の
  ガバナンス/需給観点(大株主・政策保有)
- `/indices/bars/daily/topix` → RG-1(レジーム共通化)の市場系列
- Add-ons(分足・ティック・TDnet) → 現時点で不要(追加契約領域。中期レーンに分足は不要)
- cursor差分取得・Gzip・レートリミット頁 → 既存フェッチャの運用改善メモとして読む

## 4. 変わらないもの
- **新データ≠新シグナル**。取得はすべて「防御ルールの計測」「value-auditのFACT化」
  「RG-1」に紐づく範囲のみ。シグナル探索のためのデータ漁りはしない(setupは事前登録制)。
- DT-1a のJPX実装・PIT追記型・鮮度ゲートはそのまま稼働継続。
- 是正①②(コード照合端ケース・131vs130説明)は本D0-Rと並行してよい(先に済ませても可)。
- watchlist REST の V2移行(別件・Codex提案)は書き手宣言が出たら着手可。ファイル重複なし。

## 5. 報告様式
D0-R結果表(エンドポイント/ステータス/構造・horizon/プラン表の記載)+
§2のどの分岐に入るかの判定 + §3の1行マッピング + 前回D0判定の訂正有無を明記。

規律不変: push無し / 実装なし(読み取りのみ)/ 秘密非表示 / レートリミット尊重(プローブは最小限)。
