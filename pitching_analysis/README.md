# pitching_analysis — 投球復帰・コンディショニング長期検証

37歳右投手の復帰過程とコンディショニング戦略を、**データ蓄積 → 仮説検証 → 戦略更新**のサイクルで支える検証プロジェクト。Claude Code が検証パートナーとして分析・設計を担う。

## このフォルダの構成

| パス | 内容 |
|---|---|
| `project_charter.md` | 本プロジェクトの「憲法」。文脈・原則・仮説・依頼・制約を集約。新セッションはここから開始。 |
| `analysis_phase1.md` | （フェーズ1）批判的分析と盲点の発見 — *未着手* |
| `hypotheses_priority.md` | （フェーズ2）仮説の整理と優先順位付け — *未着手* |
| `data_system_design.md` | （フェーズ3）データ記録システム設計書 — *未着手* |
| `templates/` | Obsidian用テンプレート（日次/週次/月次/ダッシュボード） — *未着手* |
| `examples/` | サンプルデータと記入例 — *未着手* |
| `scripts/` | 集計・可視化・トレンド分析スクリプト — *未着手* |

## 進行状況（2026-06-16 時点）

- [x] 憲法（charter）保存・環境制約の合意（保存先＝本リポジトリ内 `pitching_analysis/`）
- [ ] **追加データ収集中**（体重実数 / 投球量 / 筋トレ量 / 痛み部位 / 睡眠・栄養ベースライン）← *次はここ*
- [ ] フェーズ1: 批判的分析
- [ ] フェーズ2: 仮説の優先順位付け
- [ ] フェーズ3: データ記録システム設計

## 独立リポジトリへの切り出し（将来）

このフォルダは自己完結設計。独立させたくなったら次のいずれか:

```bash
# 方法1: 履歴ごと切り出す
git subtree split -P pitching_analysis -b pitching-only
# 新リポジトリを作成・追加後
git push <new-repo> pitching-only:main

# 方法2: 単純コピー（履歴不要なら）
cp -r pitching_analysis /path/to/new-repo/
```

## Obsidian への取り込み

本リポジトリを `git pull` するか、`pitching_analysis/` をコピーして Obsidian vault に配置する。テンプレート・タグ設計はフェーズ3で確定。
