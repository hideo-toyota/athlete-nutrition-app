# pitching_analysis — 投球復帰・コンディショニング長期検証

37歳右投手の復帰過程とコンディショニング戦略を、**データ蓄積 → 仮説検証 → 戦略更新**のサイクルで支える検証プロジェクト。Claude Code が検証パートナーとして分析・設計を担う。

## このフォルダの構成

| パス | 内容 |
|---|---|
| `project_charter.md` | 本プロジェクトの「憲法」。文脈・原則・仮説・依頼・制約を集約。新セッションはここから開始。 |
| `analysis_phase1.md` | （フェーズ1）批判的分析と盲点の発見 — **作成済（6本のリサーチで根拠付け）** |
| `hypotheses_priority.md` | （フェーズ2）仮説の整理と優先順位付け — **作成済v2（13仮説・確信度軸を追加して再スコア）** |
| `data_system_design.md` | （フェーズ3）データ記録システム設計書 — *未着手* |
| `templates/` | Obsidian用テンプレート（日次/週次/月次/ダッシュボード） — *未着手* |
| `examples/` | サンプルデータと記入例 — *未着手* |
| `scripts/` | 集計・可視化・トレンド分析スクリプト — *未着手* |

## 進行状況（2026-06-16 時点）

- [x] 憲法（charter）保存・環境制約の合意（保存先＝本リポジトリ内 `pitching_analysis/`）
- [x] 追加データ収集（身長体重/投球量/筋トレ実態/痛み/睡眠/栄養/Garmin睡眠）
- [x] **フェーズ1: 批判的分析**（`analysis_phase1.md`／5本＋心理1本の並列リサーチで根拠付け）← *あなたの検証待ち*
- [x] **フェーズ2: 仮説の優先順位付け**（`hypotheses_priority.md`／13仮説を5基準でスコアリング）← *あなたの検証待ち*
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
