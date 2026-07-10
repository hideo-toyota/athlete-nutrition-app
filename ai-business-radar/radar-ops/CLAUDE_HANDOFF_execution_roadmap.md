# CLAUDE_HANDOFF — 実行ロードマップ(司令塔・Codex共用・常時参照)

クラウド側裁定者より。J-Quants V2 全体戦略(v2_full_strategy.md, 827178a…)を受けた
**実行順序の正本**。以後、着手順・担当・ゲートはこの文書に従う。
変更できるのはクラウド裁定のみ(勝手な順序入替・先回り着手は並行コミッタ事案と同じ扱い)。

## 運用原則(全フェーズ共通)
1. **1タスク=単独コミット=確認依頼MD=クラウド監査**のリズムを崩さない。
2. フェーズ間には**ゲート**がある。前フェーズの監査合格(クラウドのGO)なしに次へ進まない。
3. Codex と司令塔の並行作業は**ファイル領域が重ならない場合のみ**可
   (Codex=宣言されたファイルのみ / 司令塔=それ以外。同一ファイル同時編集は禁止)。
4. 新データはすべて「防御ルール計測・value-audit FACT化・RG-1」のため。
   **シグナル探索のためのデータ漁り・閾値いじりは全フェーズで禁止**(setupは事前登録制)。
5. push禁止(no_push)/ PIT追記型 / 履歴append-only / レートリミット尊重は全タスク共通。
6. **第2監査役(デスクトップ)の所見は本ロードマップを変更しない**。順序・内容の変更は
   オーナー経由のクラウド裁定のみ(所見→オーナー→裁定→INDEX の一本鎖)。

## Phase 0 — 進行中(並行可・順不同)
| # | タスク | 書き手 | 状態/根拠文書 |
|---|---|---|---|
| 0-1 | 是正①(コード照合端ケース+3テスト)・是正②(131vs130の1行説明) | 司令塔 | dt1a_acceptance_dt1b_go.md §1-2 |
| 0-2 | D0-R: V2実測(範囲は v2_full_strategy.md §8 で縮小済み。Premium確定を前提に、edinet系・breakdown・fins/details・margin/short系の可否と、margin-interest の公表ラグを実測) | 司令塔(読み取りのみ) | d0r_v2_reprobe.md + v2_full_strategy.md §8 |
| 0-3 | watchlist REST V2移行(R0限定) | **Codex**(オーナー宣言済み) | v2_migration_facts.md §2 + v2_full_strategy.md §5 |
| 0-4 | education 自動化 DoD 最終クローズ(webhook記入済み・受信確認済みの記録) | 司令塔 | education_acceptance.md §2 |

**ゲートG0**: 0-1〜0-4 の完了報告をまとめた確認依頼MD → クラウド監査 → DT-1b GO発行。

## Phase 1 — DT-1b: 信用残(週次)
- 仕様: v2_full_strategy.md **§3**(margin-interest 主データ + margin-alert 規制フラグ補助)。
- 書き手: 司令塔(または オーナーが宣言すれば Codex)。D0(公表ラグ実測)→実装→単独コミット。
- 出力は観測とカバレッジ報告のみ(briefに出さない)。
**ゲートG1**: 確認依頼MD → クラウド監査 → DT-1c GO。

## Phase 2 — DT-1c: 空売り(3層)
- 仕様: v2_full_strategy.md **§4**(①業種別short-ratio ②breakdownから銘柄別をCALCULATION
  ③short-sale-report大口イベント)。層②の定義式は実装前に固定し、確認依頼MDに明記。
**ゲートG2**: 確認依頼MD → クラウド監査 → Phase 3 の対象選定裁定。

## Phase 3 — 中期value-audit強化(1件ずつ個別裁定)
優先順(クラウドが1件ずつ仕様を発行する。まとめて着手しない):
1. fins/details の役割裁定(EDINET班の原文パースとの分担)→ 実装
2. edinet/major-shareholders・cross-shareholdings(Premium 20年。
   cross-shareholdings は LLM修正データ=FACT禁止・裏取り必須の縛りで)
3. fins/dividend の ExDate(日程管理)
- 小粒の任意項目(司令塔判断で隙間に実施可): earnings-calendar の T+1 クロスチェック1行
  (v2_full_strategy.md §2)。

## Phase 4 — バックテスト/RG-1 基盤(クラウドが仕様発行後に着手)
1. PITマスタ(master の date パラメータ)によるユニバース再構成
2. UL/LL(ストップ高安フラグ)の BT engine への組込み検証
3. 33業種別指数 → RG-1 のセクター文脈
4. investor-types(市場フロー観測)
- このフェーズは**新setupの事前登録が具体化するまで急がない**(基盤だけ先に作らない。
  必要になった時に、必要な分だけ)。

## 並行して続く定常運用(ロードマップの外・止めない)
- 日次: daily-update / investor-brief(防御ルール警告)/ 観測5班 / education 19:00
- 週次: EDINETカバレッジ拡大バッチ(400→全上場)/ 司令塔の相互監査1行
- 月次: education 弱点マップ / newspicks「二重過熱」タグの自己較正

## 現在地(2026-07-05時点)
Phase 0 実行中。次のクラウド裁定は G0(Phase 0 完了報告の監査)で行う。
確認依頼MDには本文書の # 番号(0-1等)でタスクを参照すること。
