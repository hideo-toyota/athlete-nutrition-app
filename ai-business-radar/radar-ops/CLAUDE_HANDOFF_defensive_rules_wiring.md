# CLAUDE_HANDOFF — BT-1 防御ルールの日次運用への接続(実行役用)

あなたは equity-radar-live の実行役(implementer)です。司令塔の棚卸し(STATUS)で
本タスクが未着手であることを確認済みの前提で実装する。SPEC逸脱時は停止して司令塔に確認。

## 背景
BT-1 全期間トレイン(2008-2025)の最終評決で、3つの防御ルールがデータで裏付けられた:
1. 過熱(20日リターン+40%超)銘柄をロングで追わない(2020年急落局面で最も有効)
2. リスク1%/トレード(決算外でも-11R級ギャップが実在。サイズだけが防御)
3. 決算を跨がない
これらを「知識」から「日次運用の機械的な警告」に変える。

## 絶対制約
- 売買推奨・ランキング・価格目標を出さない。警告は「検証入口の注意」であり売り指示ではない
  (保有銘柄が過熱フラグに該当しても「売れ」とは書かない)。
- FORBIDDEN_OUTPUT_TOKENS ガード維持 / PIT維持 / raw本文・APIキー非表示。
- 既存コマンドのI/Oを壊さない。テスト無し実装はマージ禁止。canonical root guard 対象。

## 実装内容
### W1. investor-brief への過熱警告
- Human Review List / Watch Changes の各銘柄に overheat_flag を付与:
  return_20d >= +0.40(閾値は config.json の bt1_defensive.overheat_20d_threshold、
  デフォルト0.40。ハードコード禁止)
- 該当銘柄に固定文言:
  「⚠️ 過熱: 20日+40%超。BT-1全期間検証(2008-25)により追随エントリーは期待値マイナス。
   検証入口としてのみ扱い、ロングで追わない」
- 過熱銘柄をリストから除外はしない(警告付きで表示。見えなくすると学習機会が消える)

### W2. daily-update サマリへの防御ルール行
- サマリに1行追加: 「防御ルール: 過熱該当 N件 / 決算接近 M件(次の5営業日)」
- M件は jquants_earnings_calendar_v1(DT-1)が存在する場合のみ。無ければ
  「決算接近: UNKNOWN(earnings calendar未取得)」と正直に表示

### W3. 紙上トライアル事前登録ガードの拡張
- swing_paper_log への事前登録時(将来、新setupで再開した場合):
  対象銘柄が overheat_flag 該当なら警告表示+
  overheat_acknowledged: true が無ければ登録拒否(earnings_acknowledged と同方式)

### W4. education 連携(軽微)
- daily-education の題材候補に「本日の過熱該当銘柄数」を使えるようハンドオフに追記

## テスト要件(合成データ)
- return_20d=+0.45 で overheat_flag が立ち警告文言が render される / +0.39 では立たない
- 閾値が config から読まれる / 過熱銘柄がリストから除外されていない
- earnings calendar 不在時に M=UNKNOWN 表示
- FORBIDDEN_OUTPUT_TOKENS 全出力維持 / 既存 investor-brief・daily-update テスト全通過

## DoD
- 全テスト通過 / 実データで investor-brief を1回生成し警告表示を目視確認
- 本タスク単独でコミット(他の差分と混ぜない)
- Obsidian記録: outputs/obsidian/YYYY-MM-DD-防御ルール日次接続.md
- 報告: 変更ファイル一覧 / テスト結果 / 警告部分の抜粋 → radar-ops/reports/ へ

## やらないこと
- 過熱銘柄の自動除外・売りシグナル化 / 閾値の最適化(BT-1の+40%定義を維持)
- DT-1本体(決算カレンダー取得)の実装(別タスク)
