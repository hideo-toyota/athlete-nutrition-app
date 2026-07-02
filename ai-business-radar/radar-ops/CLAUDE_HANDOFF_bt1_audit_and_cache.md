# CLAUDE_HANDOFF — BT-1 実装監査 + 正規化キャッシュ設計(2026-07-02)

前提: BT-1 実装済み・train実行済み(全6本 sample_too_small)・実装差分は未コミット。
本ハンドオフは (A) 実装の逆監査 (B) 全期間実行を可能にするキャッシュ設計 (C) コミット衛生、の3点。

## A. BT-1 実装逆監査(実装者と別セッション/別AIで実施)

### A-0. 最重要: sample_too_small の原因特定(ファネル計数)
全6本 <50イベントは 2.5年×約4,000銘柄に対して**不自然に少ない**。バグと仕様効果を区別するため、
engine に**ファネル計数**を追加して1回再実行し、attempts_log と結果jsonに含めること:
```
universe_total → 流動性通過 → 参加率通過 → 地合いフィルター通過
→ 決算窓通過 → シグナル条件成立(=イベント) → 損失制御で執行見送り
```
各段の件数が出れば「どこで消えたか」が一目になる。**シグナル成立が数十件なら仕様、
最初の段で激減ならフィルタ設定、途中で不連続にゼロならバグ**を疑う。

### A-1. 先読み(lookahead)
- シグナル判定に使う最終データ日 < エントリー約定日(翌営業日寄付)を、実データ数件で手検証
- 60日高値・20日平均出来高などのローリング窓が**当日を含まない**(シグナル日を含めてよいのは
  シグナル判定のみ。約定価格側に混入していないか)
- 地合いフィルターの positive_rate 計算日がシグナル日以前か

### A-2. 決算窓の境界
- DiscDate ちょうど3営業日前・翌1営業日・その境界の**両端**でエントリー可否をテスト
- 保有中に DiscDate が来るケースの event exit が**前営業日終値**か(当日終値になっていないか)
- DiscDate が休日/非営業日の場合の営業日繰り

### A-3. R計算・コスト
- R = (exit-entry)/(entry-stop)。ショート(overheat_fade)で符号が正しいか
- コスト片道15bpsが entry/exit **両側**に適用され、R計算前の価格に反映されているか
- stop ギャップ(寄付が stop を飛び越えた場合)の約定価格 = 寄付価格(stop価格ではない)か

### A-4. 多重比較・記録
- attempts_log 6件 = 3 setup × フィルター有無2系統 で全部揃っているか
- human_approved_test=false 固定 / 実銘柄コードが公開出力に無い(grep で確認)
- FORBIDDEN_OUTPUT_TOKENS ガードが結果 .md に適用されているか

### A-5. train窓
- 2023-01〜2025-06 への短縮は fccde39 で固定済み=手続きOK。
- ただし**強い上昇相場に偏った窓**である旨を結果 .md のヘッダに明記すること
  (モメンタム系の期待値は楽観側に歪む。レジーム別分解が唯一の防御)。
- キャッシュ完成後の全期間拡張は**別 backtest_id**。

## B. 正規化キャッシュ設計(全期間を現実的に回すため)

### 方針
- 場所: `data/cache/backtest_daily_v1/`(**data/cache/ は既に gitignore 済み**)
- 内容: raw bulk日足を1回だけパースし、銘柄コード別のコンパクト形式に変換
  - 推奨: 標準ライブラリのみなら code別 `.npy`風の struct/array か pickle(list of tuples)。
    依存追加を許すなら pyarrow/parquet が最良(人間に確認してから追加)
  - 列: date(ordinal), open, high, low, close(調整後), volume, turnover
- manifest: `data/cache/backtest_daily_v1/manifest.json` に
  **入力rawファイルの digest 一覧**と normalization_version を記録。
  digest 不一致(raw更新)を検知したら該当銘柄のみ再構築
- DiscDate も同様にキャッシュ(`earnings_dates_v1/`: code → sorted DiscDate list)

### 規律
- キャッシュは**rawの再エンコードのみ**。補間・補正・除外をキャッシュ層でしない
  (フィルタは engine 層の責務。層をまたぐと監査不能になる)
- PIT はキャッシュで変化しない(日付列がそのまま残るため)。テストで再確認
- キャッシュ破損/未構築時は明示エラー(黙って raw に fallback して激遅にならない)

### 期待効果と受け入れ基準
- 1実験の実行時間: 現状比 **10倍以上**短縮(実測を Obsidian ログに記録)
- キャッシュ構築: `python3 -m radar backtest-cache build [--rebuild]` として分離
- テスト: raw→cache→raw復元一致(数銘柄) / digest差分検知 / 破損時エラー

## C. コミット衛生(今すぐ・監査の前に)
未コミットのまま監査すると「監査した版」が固定できない。以下の順で:
1. **BT-1実装のみ**をコミット(radar/backtest/ + tests/test_backtest_bt1.py + CLI配線の
   __main__.py 差分だけを選択的に stage。`git add -p` を使う)
2. 過去作業の混在差分は**別コミット**(内容を確認し、意図不明なものは人間に提示)
3. outputs/backtests/ の生成物は gitignore 対象か確認(attempts_log は残す設計なら例外を明記)
4. コミット後、そのハッシュを監査対象として A を実施

## 完了条件
- A-0 のファネル計数で sample_too_small の原因が「仕様/フィルタ/バグ」のどれか特定・記録される
- A-1〜A-5 の指摘が0件になる(または修正コミット済み)
- B のキャッシュで全期間 train が現実時間で回る(実測記録)
- 全テスト通過・Obsidian 記録
