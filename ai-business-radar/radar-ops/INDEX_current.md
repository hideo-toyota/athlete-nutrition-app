# INDEX_current — 有効文書の目次と現在の優先順位(司令塔・Codex共用)

クラウド側裁定者が維持する**正本の目次**。ここに載っている文書だけが現在有効。
取得方法は従来どおり(fetch + git show、または raw URL)+ 下記 sha256 と照合。
BASE = https://raw.githubusercontent.com/hideo-toyota/athlete-nutrition-app/claude/discord-ai-agent-setup-NCvKl/ai-business-radar/radar-ops/

## 0. オーナー宣言の記録(2026-07-06 確定・転記)
- J-Quants 契約プランは **Premium**。
- **watchlist REST V2移行(タスク0-3)に限り、Codex が radar/sources/jquants_rest_client.py と
  対応テストの書き手**。司令塔はこの2箇所に触らない。完了後、書き手権限は司令塔に戻る。
- 0-3 の実装条件: R0限定(人間指定銘柄の確認のみ・ランキング/候補生成に使わない)、
  下記 (D) §2 と (E) §5 に従う、実装前にV2エンドポイント実測、単独コミット+全テスト通過。

## 1. 常設(常時参照・全セッション必読)
| # | ファイル | sha256 | 役割 |
|---|---|---|---|
| A | COMMANDER_BOOT.md | 7e10c14663f86164ed7f5357e332e8da7f6317eb11cb43abad5c1045d71c7d23 | 司令塔の役割・恒久ルール10ヶ条・起動手順 |
| B | CLAUDE_HANDOFF_execution_roadmap.md | 97132ca2649719d01360f0f6944472ad59c22ee6fd1707e9a05832db1a94f972 | 実行順序の正本(Phase 0〜4・ゲート) |

## 2. 現行タスクの文書(Phase 0)
| # | ファイル | sha256 | 対応タスク |
|---|---|---|---|
| C | CLAUDE_HANDOFF_education_empty_post_fix.md | bac5a642db465e349c9d96fe960a3252a2f602909bc4bf2607f25910962712d6 | **最優先**(19:00発火前に)。0-4を置換 |
| D | CLAUDE_HANDOFF_v2_migration_facts.md | 79cba5f51835c153568a45d4ef3dd43a9a7c1bd7d9f5f50a423dbec847c46931 | 0-3の実装条件 / 全タスクの共通事実 |
| E | CLAUDE_HANDOFF_v2_full_strategy.md | 827178a09caf843b9123fb7660f84b4fd3a270bfa148132d9e95ea80b6806e20 | V2全体戦略。**D0-Rの範囲縮小は§8** |
| F | CLAUDE_HANDOFF_d0r_v2_reprobe.md | 299f478d59058a29d690bb1d20c0d042d21ec4157bae68fe1a6fffc2c7caedd4 | 0-2 D0-R本体(§8で範囲縮小済み) |
| G | CLAUDE_HANDOFF_dt1a_acceptance_dt1b_go.md | f59edf36cbf196d8d333fc97c5af4add4bac04adbfe509cf89d1aba05c8728fc | 0-1 是正①②(§1-2)+共存ガードレール(§3) |

## 3. 司令塔の作業順(いま)
1. **(C) education空投稿の診断・修正** — 時間依存(次の19:00発火前に完全性ゲートを入れる)
2. (G)§1-2 是正①②(未実施なら)
3. (F)+(E)§8 D0-R 実測(Premium前提。読み取りのみ)
4. G0報告: 0-1〜0-4 まとめて確認依頼MD(ロードマップのタスク番号で参照)

## 4. Codex の作業(0-3 のみ)
- 対象: (D)§2 + (E)§5 + (B)の 0-3 行 + §0 の宣言。
- 宣言されたファイル以外に触らない。完了したら単独コミット→司令塔に報告→書き手権限返却。

## 5. 完了・歴史文書(再取得不要。参照したい時だけ)
status_v2_adjudication / remote_isolation / concurrency_triage / single_writer_and_wip /
education_acceptance / education_automation / daily_education(基盤設計・Mac取込済み) /
defensive_rules_wiring(実装済み c73810a) / squad_updates_post_bt1(配布済み) /
dt1a_source_revision(JPX採用・実装済み) / dt1_spec(**DT-1b/c着手時に再参照**)

## 6. 運用ルール(この目次自体について)
- 本目次はクラウド裁定者だけが更新する。新しい指示が出るたび、オーナーには
  「INDEXのURL+新しいsha256」1つだけが渡される。
- 目次と個別文書が矛盾したら、**新しい方(目次)を正**とし、確認依頼MDで矛盾を指摘すること。
