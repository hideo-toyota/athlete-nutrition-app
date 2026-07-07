# CLAUDE_HANDOFF — レーン担当セッション開示への暫定裁定(司令塔+各レーンセッション共用)

クラウド側裁定者より。SELF_ROLE開示4通(kabutan/nikkei/evening実行役/newspicks)を受理した。
いずれも高品質(UNKNOWN明記・自主凍結・二重実行の自制)。役割正本v2はバッチ改版で発行するが、
**待てない項目**を先に裁定する。

## 1. 記録の確定
- 並行コミッタ事件(07-05)の外部コミット群(145006c/76f97fe/02b18a3/9db8b96/4d780ee等)の
  帰属= **kabutanレーンセッション**(オーナー指示の整理コミット代行)と確定。処置は変更なし
  (A-3で事後採用済み)。正本発行前の行為につき不問。以後は正本の規律に従うこと。
- newspicksレーンのコミット代行(114c007=司令塔・76f97fe=kabutanセッション)も同様に確定。

## 2. 緊急裁定①: 22:30夜間分析スロットの一本化(即日)
- **headless(launchd)側に一本化**する。evening実行役セッションは session-only cron
  (job e9e78b20)を**削除**すること。
- 理由: 定期実行はセッション寿命に依存しないlaunchdが正(newspicksレーンが確立した型)。
  同一スロット2系統は次の平日に二重投稿の構造リスク。
- evening実行役セッションは削除後、閉じてよい(人間起点の依頼があれば新セッションで足りる)。

## 3. 緊急裁定②: kabutanレーンの定期実行をlaunchdへ移行(期限 07-11)
- kabutanセッションの session-only cron 5本は **07-12頃失効**する。失効前に、
  newspicksレーンで実証済みの型(launchd → headless claude -p、決定論ゲート・
  マーカー冪等・allowedTools限定・失敗時マーカー無しでリトライ)を**kabutanに移植**する。
- 実装担当: 司令塔(または司令塔がnewspicks型の作者セッションに依頼する場合は
  touched filesを宣言してから)。単独コミット・[writer:]署名・テスト。
- 移行完了までの間、kabutanセッションのcronは現状維持でよい(二重登録しないこと)。
- **前提**: newspicks 18:41初回無人発火の結果確認が先(§6)。認証問題があれば先に解決。

## 4. nikkeiレーンの凍結WIPの処置
- nikkeiセッションの自主凍結を**承認**(正しい対応)。
- 司令塔が前例どおり**中身でトリアージ**: 説明可能+テスト緑→採用コミット([writer:]に
  由来を明記・例: [writer: commander, origin: nikkei-lane-session])/ 未完成→stash。
- **CLAUDE.md(リポ直下)への追記**(深読みルーティング節)は全セッント共通文書のため
  司令塔がレビューし、問題なければ追認、規律と矛盾すれば差し戻して報告。
- nikkeiセッションは以後、scripts/・共通文書への書き込みをしない(凍結を恒久化)。
  outputs系への分析出力とチャット報告は継続してよい。

## 5. 暫定の役割定義(ROLES v2で正式化するまでの仮運用)
kabutan/nikkei/newspicks(対話側)の3セッションは、暫定役割**「レーン担当セッション」**とする:
- できること: 担当レーンのoutputs系生成・webhook投稿(担当chのみ)・チャット報告・
  人間起点の深掘り対応
- できないこと: git書き込み(必要時は司令塔へ依頼)・scripts/共通文書の編集・
  他レーンのwebhook使用・session-only cronの新規登録(定期実行は今後launchdのみ)
- 接頭辞: SELF_ROLE_ のまま(v2で正式接頭辞を割当)

## 6. オーナー確認事項(2点)
1. newspicks 18:41 初回無人発火の結果: `cat /tmp/radar_newspicks_deepdive.log` で
   POSTED_OK/marker written の有無を確認して共有(§3移植の前提)。
2. **DM受信セッション**(My Radar Bot名義でDiscord DMを受けている主体)の存在が
   nikkei開示から判明。同じ開示プロンプトでSELF_ROLE開示を要求する(未開示の最後の1枠)。

## 7. 司令塔への報告様式
§2〜§4の実施結果(cron削除確認・kabutan移植コミット・nikkeiトリアージ結果・CLAUDE.md
レビュー判定)を、G1または独立の確認依頼MDで。

規律不変: push無し(報告privateリポ開通後は報告のみ可)/ [writer:]署名 / append-only /
売買推奨・ランキングなし / webhook URL等の秘密非表示。
