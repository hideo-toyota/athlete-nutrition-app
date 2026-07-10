# CLAUDE_HANDOFF — remote実態への裁定: push無効化とブランチ分離(司令塔用)

クラウド側裁定者より。停止報告を受理した。**停止判断は正しい**。sha256ゲートの運用・
python3 urllib への透明な代替・push未実行の維持、すべて適切だった。

## 0. 裁定者自身の訂正(正直な記録)

acc.md §4 の前提「equity-radar-live は GitHub 非接続の独立ローカルリポ」は**私の記述が古かった**。
auto_pull(クラウド→Mac の配送機構)を設計した時点で、canonical root が
athlete-nutrition-app の clone として origin を持つことは設計上の帰結であり、
「接続そのもの」は異常ではない。よって選択肢3への回答: **リポジトリ対応関係は設計意図どおり(正)**。
ただし「push 可能なままでよい」と裁定したことは一度も無い。今回のゲート発火で、
未裁定だった穴(push能力)を塞ぐ。停止には価値があった。

## 1. 裁定: 選択肢1の変形を採用(fetchは残し、pushだけ無効化)

選択肢2(人手規律のみ)は不採用 — 規律は機構で担保する。origin を remove すると
配送機構(auto_pull/fetch)が死ぬため、**push URL のみ無効化**する:

```
git remote set-url --push origin no_push
git remote -v   # push 側が no_push になったことを確認(報告に転記)
```

以後、`git push origin HEAD` は解決不能エラーで失敗する。有料ソース由来の観測系
ドキュメント・journal・コード差分が誤って public に出る経路を機構的に遮断する。

## 2. 併せて裁定: 共有ブランチへの直接コミット禁止(ブランチ分離)

新たな発見への対処。Mac が配送ブランチ(claude/discord-ai-agent-setup-NCvKl)の上に
ローカルコミットを積んだため履歴が分岐し、**ff-only の auto_pull は既に機能停止していたはず**
(クラウド側裁定が自動で届かなかった構造的原因)。以下で分離する:

```
# 現HEAD(ローカル5コミット)を作業ブランチとして確保(作業ツリーは変化しない)
git branch mac/live
git checkout mac/live

# 配送ブランチを origin の純粋なミラーに戻す(ローカル5コミットは mac/live に保持済み)
git branch -f claude/discord-ai-agent-setup-NCvKl origin/claude/discord-ai-agent-setup-NCvKl

# クラウド側の最新(本裁定を含む)を作業ブランチへ取り込む
git fetch origin
git merge origin/claude/discord-ai-agent-setup-NCvKl
```

- merge で衝突した場合: `radar-ops/CLAUDE_HANDOFF_*` は **origin 側を正**として解決
  (ファイル側が常に正、の原則)。それ以外の衝突は解決せず停止して報告。
- 以後の運用: **Mac のコミットはすべて mac/live に積む**。配送ブランチには二度と
  直接コミットしない(ミラー専用)。
- auto_pull.sh を修正: `git pull --ff-only` → **`git fetch origin` のみ**に変更
  (新着があればログに記録)。取り込み(merge)は司令塔がセッション開始時に手動で行う。
  この修正は §1 のレーンコミットに含めてよい。

## 3. 実行順序(再開)

1. §1 push無効化 → 2. §2 ブランチ分離+merge → 3. adj.md §6 の残り
   (①レーン単位コミット ②防御ルール接続 ③5班配布 — すべて mac/live 上で)→
   4. 確認依頼MD(adj.md §7 様式+本裁定の §1/§2 の実行結果転記)。
- 承認済みの権限境界は不変: ローカルコミットのみ / push しない(no_push化で機構保証)/
  webhook・Discord自動投稿はオーナー側作業。

## 4. 将来メモ(今回は実行しない)

Mac ローカル作業(mac/live)のバックアップが欲しくなった場合は、**private リポを
新設して第2 remote に**する(public への push 解禁ではなく)。オーナー判断が出たら別途裁定。

規律は不変: 売買推奨・ランキング・価格目標なし / APIキー・webhook・raw本文の非表示 /
有料ソース観測メタデータを public に出さない / test期間封印継続。
