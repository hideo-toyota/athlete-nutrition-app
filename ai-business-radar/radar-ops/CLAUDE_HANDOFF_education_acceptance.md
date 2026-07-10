# CLAUDE_HANDOFF — education自動化の受理裁定と残指示(司令塔用)

クラウド側裁定者より。782dbcb の完了報告を監査した。結果: **条件付き受理**。
単独コミット / unittest 17件OK / plistテンプレのみコミット / E2E実発火(guard clean・解答漏れ0) /
webhook不在時はinertという安全デフォルト — いずれも仕様適合。material-guard 誤検知の
正直な報告と修正記録も良い。以下3点だけ対応すること。

## 1. ガード裁定: 「非致命化」は文脈付き一致に限定する(二層構造)

免責行の「価格目標」を拾った誤検知への対処として文脈対応は正しい。ただし
**全検知を警告どまりにしたなら弱体化**であり、二層に分けること:

- **文脈付き一致**(否定・免責・引用の中に出る語): 警告+投稿続行 — 今回の修正でよい
- **素の売買断定**(肯定文脈での「買い推奨」「〜を買うべき」等): **Discord投稿をブロック**。
  ノート生成と state 前進は続行してよいが、公開部から当該部分を隔離し、
  ブロックした事実をログと翌日リマインド行に残す
- テスト追加: 公開部に素の売買断定を混ぜた合成教材が**投稿されない**こと

既に二層になっているなら、その旨(該当テスト名)の報告だけでよい。修正不要。

## 2. 投稿先のオーナー判断(確定)

**専用チャンネル + `.discord_webhook_education` 方式を採用**(実装デフォルトのまま。コード変更不要)。
- オーナーが Discord に教育用チャンネルを作成し、webhook URL を **Mac 上で直接**
  `.discord_webhook_education` に記入する(チャット・Discord にURLを貼らせない。gitignore 確認)。
- 記入後の翌日19:00発火で投稿を目視確認し、DoD最終項目をクローズして報告。

## 3. 順序の再確認: 「残り95件は指示待ち」は誤り — 指示は発行済み

STATUS v2 への裁定は既に公開済み(レーン単位コミット GO を含む):

```
https://raw.githubusercontent.com/hideo-toyota/athlete-nutrition-app/claude/discord-ai-agent-setup-NCvKl/ai-business-radar/radar-ops/CLAUDE_HANDOFF_status_v2_adjudication.md
```

未取得なら取得し、記載の §6 の順で進める:
**①レーン単位コミット(§1の仕様・unittestを§2のとおり前後実行)→ ②防御ルール接続(単独コミット)→
③5班差分配布 → 確認依頼MD(§7様式)**。education(④)は先に完了したのでそのままでよいが、
以降は裁定の順序を崩さないこと。

## 4. 確認事項1件(次回の確認依頼MDに含める)

報告に「リポジトリのブランチ claude/discord-ai-agent-setup-NCvKl に本セッションで計5コミット」
とあるが、equity-radar-live は GitHub 非接続の独立ローカルリポというのが確定済みの前提。
次回報告に以下の出力を転記すること:
- `git remote -v`
- `git branch --show-current`
万一 public リポ(athlete-nutrition-app)へ push できる remote が設定されているなら、
**push せず停止して報告**(有料ソース由来の観測メタデータを public に出さないため)。
単なるローカルブランチ名の一致なら、その旨の1行でよい。

規律は不変: 売買推奨・ランキング・価格目標なし / APIキー・webhook URL・raw本文の非表示 /
未回答でも教材生成を止めない / test期間封印継続。
