# 2026-06-26 canonicalガード追加

## 背景
- 日本市場分析を試走した際、正本ではない `Documents/Playground/.../ai-business-radar` 側を参照してしまい、最新株価日 `2026-06-25` ではなく `2026-06-22` の分析を返した。
- 原因は、複数checkoutが同時に存在し、分析系コマンドがどちらでも通常通り実行できていたこと。

## 対応
- `config.json` に `runtime.canonical_root` を追加。
  - 正本: `/Users/toyodahideo/equity-radar-live`
- `radar/runtime_guard.py` を追加。
  - データ取得、feature生成、research/evidence/brief系コマンドは canonical 以外では停止。
  - `doctor` や `data-check` など診断系は停止しない。
  - 検証目的のみ `RADAR_ALLOW_NON_CANONICAL=1` で明示迂回できる。
- `radar doctor` に `canonical_root` と `canonical_match` を表示。
- README に「分析前は doctor で root / canonical_match / latest_price_date を確認する」運用メモを追加。

## 効果
- 古いcheckoutで `investor-brief` などを実行すると停止する。
- 分析前に `doctor` を見れば、正本かどうかとデータ鮮度が同時に確認できる。
- 今後、同じ原因で旧データを拾う事故を機械的に防げる。

## 検証
- `python3 -m py_compile radar/*.py radar/sources/*.py radar/features/*.py radar/research/*.py`
- `python3 -m unittest -q` → 272件 OK
- 非canonical checkout で `python3 -m radar investor-brief --asof 2026-06-25` が `canonical root mismatch` で停止することを確認。
- 非canonical checkout で `python3 -m radar doctor` が停止せず、`canonical_match: False` と警告を表示することを確認。

## 注意
- 正本 `/Users/toyodahideo/equity-radar-live` へは、このコミットを pull して反映する必要がある。
- `outputs/honest_mirror.md` の既存差分は今回の修正対象外。
