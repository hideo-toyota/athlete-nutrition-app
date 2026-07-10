# HANDOFF_OPEN_ITEMS — 未完タスク引き継ぎ一覧(2026-07-10・セッション世代交代時点)

このセッション(裁定者・旧世代)で扱った全案件の**未完のもの**を一箇所に集約。
新世代裁定者は BATCH_REVISION_QUEUE.md と本書を読めば、取りこぼしなく引き継げる。
※完了済み(0-3クローズ・G1本体・R3検証・日経dedup・報告配送実装・防御ルール・DT-1a・EDINET 400裁定)は
  再掲しない(git log と各CONFIRM MDに記録済み)。

## A. 裁定者(新世代)が発行する宿題 ★最優先
1. **バッチ改版一式**(BATCH_REVISION_QUEUE §1-4の全部):
   ROLES v2 / INDEX v2 / ロードマップ v2 / 判断記録レーン発効 / 月次投入ゲート発効 /
   session-starters改訂配布 / オーナー日課ガイド / 出力スタイル規約+用語集。
   → **INDEX v2 が特に急ぎ**(十数本の新正本が未掲載=陳腐化)。
2. **Phase 2c の SPEC 3本**(reading_layer_integrity 裁定済み・SPEC未発行):
   SPEC_edinet_latest_known_snapshot_v1 / SPEC_analysis_readiness_manifest_v1 / 指数取得小仕様。
3. これらは新世代裁定者が athlete-nutrition-app に書いて push する。

## B. Mac側(司令塔)が実装待ち(SPEC/GO発行済み・着手待ち)
- **G1残務の是正**: §7-4(grader二重行の正典指定=751536a後・(date,serial)キー化)= g1_residuals_accept §2。
- **米国地合いM0 v2**(96843fc): D0→SOURCE_CONTRACT作成→裁定者確認→実装。前提=FREDキー記入(オーナー)。
- **Phase 2c 実装**: A-2のSPEC発行後。順=2c-1 snapshot→2c-2 readiness→2c-3 CA隔離→指数取得→2c-4判断採点。
- **kabutan launchd**: 土10:41 calibration初回・catchupの結果確認(継続監視)。
- **session-starters 改訂**(session_starters_revision 6220437): 00/01/05→02/03/04/06 の順。

## C. オーナー(人間)の宿題
- **FRED APIキー**を .env に記入(M0の前提・5分・急ぎでない)。
- **DM受信セッションの SELF_ROLE 開示**(最後の未開示枠・dialogue_responder.py 逸脱と関連)。
- **教育クイズ #5(分野E)以降**への回答(自動grader採点)/ **金曜の判断記録 第1号**。
- MV-001 の答え合わせ(2026-08-05頃・TOPIX/日経基準値の確定が前提)。

## D. 休眠・条件待ち(今は動かさない)
- HB-001/002/003(仮説バックログ)= DT-1b/c・fins予想活用の後、審査パネル経由で事前登録。
- 検証機会アラート = M0+予想修正検出の完了直後に仕様発行(4a3)。
- 深読みディスパッチャ = バッチ後に仕様(4a2)。
- 2台PC運用(DUAL_MACHINE)= 発動トリガー待ち(4c)。
- DT-1c = G2解禁待ち。Phase 3(fins/details・大株主・#6+#7項目)= 順番待ち。
- VERIFY playbook / レーンSKILL標準化 = バッチ後の小タスク(4b)。
- dialogue_responder.py 未コミット差分 = ROLES v2 で追認/巻き戻し裁定。

## E. 継続監視(自動・報告を待つだけ)
- MV-001(相場観較正・8/5頃判定)/ education日次(19:00・grader採点)/
  観測5レーン(launchd)/ EDINETローリング再取得(400/日・9.5日周期)。

## 引き継ぎの一言
新世代裁定者への最初の指示: 「BATCH_REVISION_QUEUE.md と本書(HANDOFF_OPEN_ITEMS)を読み、
Aの宿題(バッチ改版+Phase 2c SPEC)から着手せよ」。
