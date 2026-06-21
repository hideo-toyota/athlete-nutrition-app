# 自動 pull(私の実装を Mac へ自動で届ける)

クラウド側 Claude が push したコードを、Mac 側が**30分ごとに自動取り込み**する仕組み。
**コードが届くだけ**で、`fetch-jquants`/`build`/分析の自動実行はしない(実行は手動・許可制のまま)。

## 安全設計(これは守る)
- **fast-forward のみ**。ローカルに未push のコミット(Codexの作業)や未コミット変更があれば**スキップ**。
  reset も force も clobber も**しない**。
- ログは `$TMPDIR/radar_auto_pull.log`(リポ外)。作業ツリーを汚さない。
- 秘密情報は読まない・出さない。ネットは `git fetch` のみ。

## 一度だけの導入(Mac で実行)
`<REPO_ROOT>` = Mac 上のリポ絶対パス(`ai-business-radar` の1つ上)。

```bash
cd <REPO_ROOT>
chmod +x ai-business-radar/scripts/auto_pull.sh
# 動作確認(1回手動実行 → ログ確認)
bash ai-business-radar/scripts/auto_pull.sh && cat "${TMPDIR:-/tmp}/radar_auto_pull.log"
# LaunchAgent を生成して登録(30分ごと + ログイン時)
sed "s|__REPO_ROOT__|$(pwd)|g" ai-business-radar/scripts/com.radar.autopull.plist.template \
  > ~/Library/LaunchAgents/com.radar.autopull.plist
launchctl load ~/Library/LaunchAgents/com.radar.autopull.plist
```

## 停止
```bash
launchctl unload ~/Library/LaunchAgents/com.radar.autopull.plist
```

## 注意
- これで「私の実装は自動で Mac に届く」。ただし**分析を空でなくする**には、別途
  `fetch-jquants`(取得→derived生成)を Mac で実行する必要がある(コード配布≠データ生成)。
- ブランチは既定 `claude/discord-ai-agent-setup-NCvKl`。変えるなら `RADAR_BRANCH` 環境変数で上書き。
