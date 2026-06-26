# outputs/obsidian/ — 自動メモ/ログ置き場(Obsidian同期)

このフォルダは **エージェント(私)が記録を書いて push し続ける場所**です。
セッションの決定・設計・判断ログはここに溜まります。あなたは **一度だけ** 下記を設定すれば、
**以後は私の push が自動であなたのObsidian保管庫に反映**されます(= 実質、私が書き込んでいる状態)。

## 一度だけの設定(Mac・約2分)— Obsidian Git
1. リポジトリを clone(済みなら pull):
   ```bash
   git clone -b claude/discord-ai-agent-setup-NCvKl https://github.com/hideo-toyota/athlete-nutrition-app.git
   ```
2. Obsidian を開く →「**別の保管庫を管理**」→ **このフォルダ**
   (`athlete-nutrition-app/ai-business-radar/outputs/obsidian`)を**保管庫として開く**
   ※ 既存の保管庫に混ぜたい場合は、この obsidian フォルダを保管庫内へ配置するか、別保管庫として併用。
3. 設定 → コミュニティプラグイン → **Obsidian Git** をインストール・有効化。
4. Obsidian Git の設定:
   - **Pull updates on startup**: ON
   - **Auto pull interval (minutes)**: 例 `10`
5. 完了。以後、私が push するたびに(最大10分後に)**自動で保管庫に現れます**。

> 補足: `DESIGN_PRINCIPLES.md` 等の本体ドキュメントも `[[リンク]]` で繋ぎたい場合は、
> 保管庫を `ai-business-radar/` 全体にすると wikilink が解決しやすい。

## 運用上の注意(機微情報)
- このフォルダは**公開リポジトリ上**。**実際の保有額の精緻値・APIキー・口座番号などの機微情報は書かない**方針。
- 実トレードの生ログ `decision_log.jsonl` は **gitignore 済・ローカル限定**(ここには来ない)。
- ここに来るのは「設計・決定・考察」の記録。

## 現在のノート
- [[2026-06-07-投資哲学と規律の設計ログ]] — 原則・投資哲学の壁打ち
- [[2026-06-14-開発と監査の記録]] — 実装・Codex監査・データ層・target-check
- [[2026-06-17-target-checkとvalue-audit実装]] — target-check / value-audit Phase A の実装・監査
- [[2026-06-19-有料データ層とfeature生成の進捗]] — J-Quants Premium / EDINET DB Pro の取得・棚卸し・feature生成
- [[2026-06-25-コード点検と改善点の洗い出し]] — セキュリティ/PIT/再現性/テスト改善の対応記録
- [[2026-06-26-改善点対応と今後の記録ルール]] — 改善実装の要約と、今後の自動記録ルール
- [[2026-06-26-相対価格整合性監査の追加]] — ジェーンストリート型の相対価格思考を、予測ではなく監査観点として追加
- [[2026-06-26-AI回答監査レイヤーの追加]] — AI回答を根拠・前提・論理飛躍・反論・採用判定で監査するローカルCLI
- [[2026-06-26-日本市場試走分析]] — 2026-06-22時点の日本市場スナップショット、watch changes、人間レビュー候補
- [[2026-06-26-canonicalガード追加]] — 複数checkoutによる旧データ参照ミスを防ぐため、分析系コマンドを正本パスに限定

> ※投資助言ではない。検証・規律・記録のための自分用ログ。
