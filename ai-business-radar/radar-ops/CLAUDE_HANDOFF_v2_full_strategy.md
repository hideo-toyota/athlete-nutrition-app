# CLAUDE_HANDOFF — J-Quants V2 全体戦略と実装追補(司令塔・Codex共用)

クラウド側裁定者より。オーナーが V2 公式ドキュメント一式(Resources全般・Bulk・アドオン)を
提示し、クラウド側で全読した。以下は確定裁定と、進行中タスクへの追補。
本文書は v2_migration_facts.md(79cba5f…)を置き換えず追補する。

## 1. 全体像の確定(1つのAPI・鍵1本・エンドポイント別)
認証は全エンドポイント共通 `x-api-key`。レスポンスは `{"data":[...], "pagination_key":...}` に統一。
用途マッピング(裁定):

| 区分 | エンドポイント | 裁定 |
|---|---|---|
| 今使う(基盤) | equities/master, equities/bars/daily, fins/summary, fins/dividend, markets/calendar, bulk/* | 継続(Bulk主力) |
| 今使う(DT-1b/c) | markets/margin-interest, markets/margin-alert, markets/short-ratio, markets/short-sale-report, markets/breakdown | §3/§4 の仕様で実装 |
| 後で使う(個別裁定待ち) | fins/details, edinet/major-shareholders, edinet/cross-shareholdings, indices/bars/daily(+topix), equities/investor-types, equities/earnings-calendar(T+1確認用) | §6 のキューへ |
| 使わない | derivatives系全部, equities/bars/minute, equities/trades(過去2年・アドオン), bars/daily/am | 中期レーンに不要 |
| オーナー判断保留 | td/*(TDnet適時開示。**別料金アドオン**) | 提案は§7 |

## 2. 確定: DT-1a は JPX Excel 維持(最終)
V2 の equities/earnings-calendar は**翌営業日分のみ・3月期/9月期のみ・REIT除外**と公式明記。
5営業日窓は構造的に不可能 → **JPX Excel 実装が正解として最終確定**。変更しない。
- 任意W項目(低優先): earnings-calendar を「翌営業日の直前確認」として daily-update に
  1行追加する軽量クロスチェック(JPX Excel との不一致検出)。実装は司令塔判断でよい。

## 3. DT-1b(信用残)仕様確定
- **主データ: /markets/margin-interest**(銘柄別・週末残高・申込日付=通常金曜)。
  フィールド: ShrtVol/LongVol + 一般/制度の内訳(ShrtNegVol/ShrtStdVol/LongNegVol/LongStdVol)+ IssType。
- **補助データ: /markets/margin-alert**(日々公表銘柄のみ・日次)。PubReason の6フラグ
  (規制措置/日々公表/特別注意/日証金貸株制限/貸株注意喚起/不明確情報)と TSEMrgnRegCls は
  **「空売り摩擦・規制状態」の直接観測値**。BT-1 で overheat_fade を割引いた摩擦が測れる。
- 設計の縛り(dt1_spec.md のまま): raw+provenance / PIT追記型 / コーポレートアクション遡及調整
  なし(公式明記)に注意 / 営業日2日以下の週は欠測(正直にUNKNOWN) / まず観測とカバレッジ報告のみ、
  brief には出さない / シグナル化・ランキング化禁止。
- D0で実測すること: プラン利用可否 / 公表タイミング(申込日付から何営業日遅れで取得可能になるか
  — PITのas_of設計に必須。「提供データの更新タイミング」ページ未入手のため実測で)。

## 4. DT-1c(空売り)仕様変更 — 3層構造に
公式仕様により、銘柄別の日次空売り比率は存在しない。以下の3層で設計する:
1. **業種別(市場文脈)**: /markets/short-ratio(33業種・日次・円単位)。
   業種の空売り圧力 = レジーム/セクター文脈の観測値。
2. **銘柄別(日次・実測)**: /markets/breakdown の ShrtNoMrgnVa / MrgnSellNewVa 等
   (売りの約定代金の内訳)から銘柄別の空売り系比率を **CALCULATION として自前算出**
   (定義式を明記して保存。例: short_share = (ShrtNoMrgnVa+MrgnSellNewVa)/売り合計)。
3. **大口ポジション(イベント)**: /markets/short-sale-report(残高割合0.5%以上・
   公表日/計算日ベース・報告が無い日はデータ無し=欠測と区別)。
- 縛りは§3と同じ。層2の定義式は事前に固定し、後から最適化しない。

## 5. watchlist V2移行(Codex)への追補 — カラム対応表
v2_migration_facts.md §2 の条件はそのまま。本文書で対応表を確定する(実装で使う分のみ):
- **bars/daily**: Date/Code は同名。O,H,L,C(調整前)/ Vo(取引高)/ Va(代金)/
  AdjO,AdjH,AdjL,AdjC,AdjVo(調整済)/ AdjFactor / **UL,LL(ストップ高安フラグ・新規)**。
  V1の Close→C, AdjustmentClose→AdjC 等。前後場系(M*/A*)は Premium のみ→未使用。
- **equities/master**: CompanyName→CoName / Sector17Code→S17 / Sector33Code→S33 /
  MarketCode→Mkt / ScaleCategory→ScaleCat / 貸借信用区分=Mrgn(1:信用/2:貸借/3:その他・新規)。
- **fins/summary**: NetSales→Sales / OperatingProfit→OP / OrdinaryProfit→OdP(IFRSは空欄) /
  Profit→NP / Equity→Eq / EquityToAssetRatio→EqAR / BPS / EPS / 予想系は F接頭辞(FSales, FOP…)。
  ※ fins/summary・fins/details には**個別レートリミット**あり — 歴史一括はBulk、日次増分のみREST。
- 4桁code指定=普通株のみ返却(公式仕様)— 是正①の設計と整合、テストで固定済みのこと。

## 6. 新資産キュー(実装しない。D0-R後に1件ずつ裁定)
優先順に:
1. **PITマスタ**(master の date パラメータ・2008-05-07まで): 将来バックテストの
   ユニバース再構成。BT-1の「2008-12ユニバース構成の時代差」注記を消せる。
2. **UL/LL(ストップ高安フラグ)**: BT-1 engine の gap-fill/S高張り付きの実測検証材料。
   バックテスト基盤の改善タスクとして別途仕様化。
3. **fins/details**: value-audit の FACT 供給(EDINETタクソノミ英ラベルkey)。EDINET班の
   原文パースと役割分担を裁定してから。
4. **edinet/major-shareholders・cross-shareholdings**: **Standardプラン以上**・API限定。
   cross-shareholdings は公式が「LLMにてデータ修正」と明記 → **FACT扱い禁止、
   INFERENCE(vendor処理済み)として扱い、材料になる時はEDINET原文で裏取り**。
5. **業種別指数**(indices/bars/daily・33業種2008〜): RG-1 のセクター文脈。
6. **fins/dividend の ExDate(権利落日)**: 中期レーンの日程管理。RefNo訂正はappend型=PIT向き。
7. **investor-types**(週次・市場別フロー): 観測のみ。過誤訂正が2023-04以降は新旧両方
   提供される点はPIT設計に好都合。

## 7. TDnet アドオン(オーナー判断・急がない)
td/list は開示インデックス(タイトル・開示番号)を構造化取得でき、日経班の「イベント供給」を
公式データで置き換え/補強できる。ただし**別料金アドオン+過去5年のみ**。
現行の観測班で回っているため、**中期レーンが軌道に乗ってから費用対効果を再評価**を推奨。

## 8. D0-R の位置づけ更新
ドキュメントで「何が存在するか」は確定した。残る不確実性は
**「自分の契約プランでどれが叩けるか・データ格納期間」だけ**(該当ページ未入手)。
→ D0-R(299f478…)は §1 の「今使う」欄のエンドポイントに絞って実測でよい。
edinet系(Standard以上)と breakdown・fins/details のプラン可否を必ず含める。
レートリミット順守(1エンドポイント1リクエスト+バックオフ)。

## 9. オーナーへの依頼(3点)
1. 本ドキュメント一式(公式仕様のmarkdown)を Mac 側の参照ディレクトリへ保存
   (例: radar-ops/reference/jquants-v2/ — **gitignore対象にし、public リポへコミットしない**)
2. 契約プラン名の確認(Standard/Premium のどちらか)を司令塔に一言
3. watchlist V2移行の writer 宣言(未実施なら)

規律不変: push無し / PIT / 履歴append-only / 新データはシグナル探索でなく
「防御ルール計測・value-audit FACT化・RG-1」に紐づく範囲のみ / 売買推奨・ランキングなし。
