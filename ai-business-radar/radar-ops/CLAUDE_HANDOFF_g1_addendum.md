# CLAUDE_HANDOFF — G1追補: WIP整理・EDINET停滞診断・0-3クローズ条件(司令塔用)

クラウド側裁定者より。Codex実装役の未完了タスク棚卸しを受理し、以下をG1スコープに追補する。
いずれも既発行の裁定(g0_pass / audit1_remediation / p6_verification_and_holds)と矛盾しない。

## 1. 作業ツリーの所有者別トリアージ(P0・queue衛生§3の拡張)
現在の未コミット/未追跡を**所有者別に分類**して処置(孤児WIP事案の前例どおり「中身で裁く」):
- NewsPicks deep-read 系(SKILL.md / newspicks_read.py / *_headless.sh / plist):
  作成主体を特定(不明ならUNKNOWN明記)。**説明可能+テスト緑なら単独コミットで採用**
  ([writer:] 署名付き)、未完成なら stash 退避。放置しない。
- radar-ops/CLAUDE_HANDOFF_sector_analyst_spec.md: **コミットしない**。棚卸しタスク
  (us_sector_inventory)で全文転記の上、裁定待ち。ROLES命名規則により、正規化する場合は
  接頭辞を変えて取り込む(裁定後)。
- queue/ 一時ファイル・outbox残骸・education_state バックアップ: 既指示(§3)どおり整理。
- .gitignore 差分: 意図を1行説明の上コミット。
- 完了条件: `git status --short` クリーン+分類表を確認依頼MDに転記。

## 2. EDINET financials カバレッジ停滞の診断(P0・故障診断)
derived 400/3837 が班指示(2026-07-05)以降**増えていない**。拡大バッチの状態を診断:
1. バッチ(1000件/日想定)は実在するか(LaunchAgent/スクリプトのpath)・最終実行日時・
   エラーログの有無
2. 止まっている原因(未実装/未スケジュール/レート制限/認証/失敗放置)の特定
3. **原因が設定・軽微バグなら修理して再開してよい**(単独コミット・テスト付き)。
   設計変更が必要なら停止して差し戻し。
4. 報告: 現在値→再開後の日次増加見込み(3837到達の見込み日)を1行。

## 3. 0-3(watchlist V2)クローズの条件追加
正式監査(検証役の独立検証を含む)PASS後のクローズ時に、以下を同時に処置:
- **v1認証の残骸整理**: JQUANTS_REFRESH_TOKEN/MAILADDRESS/PASSWORD 前提のコード・
  エラーメッセージ・ドキュメント記述を V2(API key)前提に更新(削除でなく非推奨明記でも可)。
- クローズをもって Codex の書き手宣言は失効(ROLES §3)。

## 4. 情報の訂正(Codex棚卸しへの回答・オーナー作業の取消し)
- **DT-1b に JPXページの人間確認は不要**。D0-Rで /markets/margin-interest(V2)=200 確定、
  G0裁定 §5 で V2 API実装をGO済み。Codex側の「JPX 403・ブラウザ確認待ち」は旧情報。
- 採点ループ(decisions=1/outcomes=0)は所見6で採用済み。**週次の判断記録レーン**として
  バッチ改版で仕様発行予定(司令塔の現時点の作業なし)。P6検証がPASSすれば
  checkpoint がその採点エンジンになる。
- P5(貸借コスト感度表)は保留のまま(ショート戦略の再検討時)で正しい。

## 5. 報告
本追補の§1〜§3はG1確認依頼MDに相区分で同梱。§2の診断結果は独立の見出しで。

規律不変: push無し / append-only / [writer:] 署名 / 作者でなく中身 / 売買推奨なし。
