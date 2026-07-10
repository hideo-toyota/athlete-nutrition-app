# ISSUE_MAP.md — value-audit 論点マップ（正本 v1）

- doc-id: `ISSUE_MAP`
- version: v1（2026-07-09 配備 `205fe01`。バッチ改版v2で本文据置・INDEX/ROLES/ROADMAP と整合確認のうえ正本化）
- as_of: 2026-07-10
- writer: クラウド裁定者（cloud adjudicator）
- 位置: `ai-business-radar/radar-ops/ISSUE_MAP.md`（正本）
- 目的: value-audit（銘柄の記述的精査）の**論点を固定**し、出力様式・判断記録の理由付けを論点番号で参照可能にする。ISSUE_MAP は**分析の骨格**であって推奨の道具ではない（ANALYSIS_QUALITY_RULES R2/R5 に劣後）。

---

## 使い方
- value-audit は本マップの**7論点の順に7節**で出力する（ANALYSIS_QUALITY_RULES R5）。
- 各論点は **FACT / INFERENCE / UNKNOWN** を分離して記述する。データが無い論点は**節を省略せず UNKNOWN 明記**。
- 判断記録レーンの「理由」は本マップの**論点番号**（I1〜I7）で記載する。

## 7論点

| # | 論点 | 主に見るもの（記述のみ・推奨しない） | 一次ソース（例） |
|---|---|---|---|
| **I1** | バリュエーション | PER / PBR / EV·EBITDA の水準と自社ヒストリカル・同業との相対。割安/割高の**断定はしない**、位置の記述に留める | J-Quants derived、`/fins/details` |
| **I2** | 収益性・資本効率 | ROE / ROIC / 各利益率とその趨勢・変動要因 | EDINET financials、`/fins/details` |
| **I3** | 財務健全性 | ネットキャッシュ/有利子負債、自己資本比率、インタレストカバレッジ、流動性 | EDINET financials |
| **I4** | キャッシュフロー・資本配分 | 営業/フリーCF、設備投資、配当・自己株買いの実績（**将来予測はしない**） | EDINET financials |
| **I5** | 事業の質・競争環境 | 事業構成、市場地位、需給・構造要因（記述的・出典明示） | 開示資料、ニュースレーン（FACT 部のみ） |
| **I6** | ガバナンス・株主還元姿勢 | 政策保有（cross-shareholdings）、大株主構成、資本政策の姿勢 | `/markets`・`/equities` の major-shareholders / cross-shareholdings |
| **I7** | 触媒・リスク | 決算近接（earnings-calendar）、開示イベント、既知リスク（UNKNOWN を隠さない） | earnings-calendar、開示カレンダー |

## 未活用エンドポイントの論点マッピング（D0-R §3 由来・実装しない記録）
- `/fins/details` → I1/I2/I3/I4 の FACT 供給（EDINET パース補完）
- `major-shareholders` / `cross-shareholdings` → I6 ガバナンス（政策保有）
- `/indices/bars/daily/topix` → 市場系列（RG-1／value-audit 論点外・別レーン）

## 非適用（明示）
- ISSUE_MAP は**銘柄選定・順位付けの道具ではない**。論点は精査の網羅性を担保するためのチェックリストであり、7節すべてが「良い」ことが買い理由になるわけではない（ANALYSIS_QUALITY_RULES R2）。
