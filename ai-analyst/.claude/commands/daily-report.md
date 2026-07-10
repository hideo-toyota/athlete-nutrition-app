---
description: 日次の投資分析レポートを生成し、Discordへ通知・Obsidianへ記録する
---

以下の手順で本日の分析を実行してください。CLAUDE.md の方針に従うこと。

1. (任意) `recorder` サブエージェントで前日の Obsidian 判断ログを読み、文脈を把握する。
2. `data-fetcher` サブエージェントで、対象銘柄($ARGUMENTS があればそれ、無ければ
   `strategies/*.yaml` の watchlist)のデータを J-Quants から取得する。
3. `data-analyst` サブエージェントで指標を計算し、必要なら可視化する。
4. `invest-analyst` サブエージェントで戦略ルールに基づくシグナル判定と簡易バックテストを行う。
5. `reporter` サブエージェントで結果を整形し、Discord に通知 + `reports/` に保存する。
6. (Phase 5) `recorder` サブエージェントで本日の判断・根拠を Obsidian に記録する。

各ステップで「データの時点」と「取得元」を明示し、最後に免責文を必ず添えること。
推奨・断定はせず、事実とシグナルの提示に徹すること。
