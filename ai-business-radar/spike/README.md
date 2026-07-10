# spike/ — 旧プロトタイプ(参照専用・運用しない)

> ⚠️ **これは“原則を発見するための試作(spike)”です。本ツールではありません。**
> `DESIGN_PRINCIPLES.md` を言語化する**前**に書かれており、いくつかの原則に違反します:
> - 「**買い候補/見送り**」等の**ラベルを出す**(規律ゲートを通さない)。
> - look-ahead 近似・ライブ≠バックテスト・自選銘柄バックテスト 等。
>
> **判断には使わないでください。** 本体は親ディレクトリの `radar/`(`python3 -m radar mirror` / `check`)。
> ここは計算式やローダの**参照・部品取り**用に残しているだけです。

含まれるもの: `opportunity_radar.py`(run/equity/trend/backtest-trend)、`ohlcv_data.py`、
`trend_indicators.py`、`trend_backtest.py`、`scripts/`、`inputs/`、`data/`、`outputs/`(旧生成物)。
