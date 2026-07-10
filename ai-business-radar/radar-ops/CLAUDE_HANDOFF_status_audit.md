# CLAUDE_HANDOFF — システム棚卸し(STATUS)作成指示(司令塔用)

あなたは equity-radar-live の司令塔として、システム現状の棚卸しレポートを作成する。
実装変更はしない。読み取りと実行確認のみ。根拠は file:line / コミットハッシュ / 実行結果。
.env・APIキー・raw本文は読まない・表示しない。

## A. 体制の現状
1. 司令塔/実行役の分担構成(どのセッション/agentがどの役割か、規定ドキュメントのpath)
2. クラウド側ハンドオフ(radar-ops/CLAUDE_HANDOFF_*)の取り込み方法と最終取込日

## B. ハンドオフ別の実装状況(各項目: 完了/一部/未着手 + 根拠)
1. daily_education: 稼働状況。outputs/obsidian/education/ の最新日付、
   journal/education_ledger.jsonl の行数、LaunchAgent化の有無
2. swing_paper_trial: 状態確認(BT-1評決により「3setupでは開始しない」が最新裁定。
   誤って開始していないか。journal/swing_paper_log.jsonl の有無)
3. swing_analytics_roadmap v2: BT-1=完了済み。DT-1(決算カレンダー将来分/信用残/空売り)、
   RG-1(regime共通化)、SG-1(合流)の各状態
4. BT-1収穫物の接続: 「過熱を追わない」「決算跨がない」警告が
   investor-brief / daily-update に組み込まれているか
5. auto_pull: launchctl list | grep radar の結果と最終pull時刻

## C. 日次運用の健康状態
1. python3 -m radar doctor の出力(canonical/latest_price_date/データ鮮度)
2. 直近3日の自動生成物の有無: news/JP・kabutan_observer・investor_brief・discord prompt
3. LaunchAgent 8本の稼働状況(エラーログの有無)

## D. Git衛生
1. git log --oneline -10 / git status --short(未コミット差分の内訳)
2. BT-1関連(precompute含む)は全てコミット済みか

## E. 乖離の正直な申告
クラウド側ハンドオフの指示と実装が意図的に違う箇所、独自判断で追加した機能、
未報告の変更を列挙(無ければ「無し」と明記)

## 出力
A〜Eを radar-ops/STATUS_YYYY-MM-DD.md にまとめ、**全文を提示して停止**
(クラウド側はMacのファイルを見られないため、要約でなく全文)。
売買推奨・銘柄評価は含めない。
