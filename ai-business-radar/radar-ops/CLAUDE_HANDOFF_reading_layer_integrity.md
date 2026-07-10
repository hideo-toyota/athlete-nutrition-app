# CLAUDE_HANDOFF — 読み取り層の整合性(Phase 2c)裁定(司令塔用)

クラウド側裁定者より。アップグレード版Codexの「分析品質と市場超過検証の次期優先順位」提案を
受理。核心の発見=**問題は取得層でなく読み取り層**(全3818取得済みなのに読む側が直近400スライス
しか見ていない)。前回のEDINET 400裁定(取得は良性)を補完する。全6指摘を確定と認定。

## 1. 新フェーズ Phase 2c「読み取り層の整合性」を新設(P0)
実装順と担当:

### 2c-1. edinet_latest_known_snapshot_v1(最優先・SPEC発行予定)
- 目的: 全asofディレクトリから**全社の最新既知財務値**を組み立てる読み取り層。value-auditと
  research queueが直近400でなく全3818(最新既知)を見るようにする。
- PIT厳守: 各値に source as_of を保持(「いつ時点の最新か」を偽らない)。
- 受け入れ: 既存の単一asof読みと同一銘柄で値一致・カバレッジ3818・古い値はas_of明示。
- 担当: 司令塔(radar/コア読み取り層)。SPECは裁定者が別途発行。

### 2c-2. analysis_readiness_manifest_v1(SPEC発行予定)
- 目的: daily-updateが「分析日/株価日/財務日/決算カレンダー日」の整合を検査し、
  ズレがあれば「完了」と言わず不整合を明示(educationの完全性ゲートと同型・「正直な完了」)。
- 出力: brief/daily-update冒頭に readiness 行(全整合=OK / ズレ=どの系列が何日古いか)。
- 担当: 司令塔。

### 2c-3. corporate_action_quarantine_v1 = 既存「分割・CA補正」タスクに統合
- BATCH_REVISION_QUEUE の分割補正ワークストリームを拡張: split_artifact行を統計から**隔離**し、
  codex_analysis_log にも適用(R1-1のbrief表面化の先の段階)。二重管理しない・1タスクに統合。
- 担当: 司令塔。

### 2c-4. 判断採点レーン = judgment_lane_spec(ドラフト済)をバッチで発効
- **依存**: TOPIX・33業種指数の取得が前提(未取得)。→ 指数取得を 2c の一部として先行させる
  (J-Quants indices/bars/daily・M0とは別・Premium確認済み)。採点はこれが揃ってから。

## 2. P1/P2 の裁定
- **P1 米国M0**: v2確定済み・SOURCE_CONTRACT先行で進行中(重複・再発行不要)。
- **P1 機械可読統治manifest**: 一部採用。まずバッチのROLES v2/INDEX v2(人間可読)で
  指摘6のstale不一致を解消。機械可読化はその後の改善(過剰設計を避け段階導入)。
- **P2 決算修正setup**: **論点2そのもの**。仮説バックログ HB-003 として登録(下記)。
  事前登録・設計審査パネル経由。**BT-1再調整・bucket掘りは行わない**を全面堅持。

## 3. 優先順位と依存(まとめ)
```
Phase 2c(P0・読み取り層):
  2c-1 snapshot ─┐(value-audit品質・独立)
  2c-2 readiness ┤(honest completion・独立)
  2c-3 CA隔離   ┘(分割補正と統合・独立)
  2c-4 判断採点 ← 指数取得(TOPIX/33業種)が前提 → 指数取得を先行
バッチ改版(裁定者): ROLES v2 / INDEX v2(指摘6解消)/ judgment・gate発効
Phase 2b: 米国M0(SOURCE_CONTRACT→実装)
Phase G2以降: DT-1c / HB検証
```

## 4. GO条件と停止条件
- GO: G1残務の是正完了後、2c-1から着手。各項目は単独コミット+テスト+報告リポ経由の確認依頼MD。
- 停止: snapshotの値が単一asof読みと不一致 / readinessが誤ってOKを出す / 隔離が正常行を巻き込む
  → いずれも停止して差し戻し。
- 不変: 読み取り層の変更は既存出力形式を壊さない(バイト等価または明示的な改善のみ)。

## 5. 発行予定SPEC(裁定者)
- SPEC_edinet_latest_known_snapshot_v1 / SPEC_analysis_readiness_manifest_v1
- 指数取得の小仕様(judgment採点の前提)
- HB-003(決算修正setup)は hypothesis_backlog に登録(本裁定と同時)

規律不変: PIT / append-only / [writer:]署名 / 推測で前提を作らない(file:lineで確定)/
市場超過は前提でなく判断ログで検証する仮説 / push無し(報告リポのみ)。
