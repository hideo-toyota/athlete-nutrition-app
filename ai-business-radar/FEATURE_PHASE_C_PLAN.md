# FEATURE_PHASE_C_PLAN — feature生成 Phase C 実装計画

> 正: FEATURE_PHASE_C_SPEC.md / DATA_LAYER_SPEC.md / CLAIMS.md / SYNC_PHASE_B_PLAN.md。
> 目的は **EDINET DB financials raw から data/derived を作るだけ**。
> research_item / evidence / LLM投入 / 買い候補 / 推奨 / 予測は作らない。

## 1. 実装順序

### C-0: 文書・ゲート固定
- `FEATURE_PHASE_C_SPEC.md` と本PLANを確定。
- `DATA_LAYER_SPEC.md` / README / PLAN から参照。
- DoD: Claude Code 監査で Phase C minimal のスコープが一意。

### C-1: pure feature engine
新規候補:

```text
radar/features/__init__.py
radar/features/registry.py
radar/features/compute.py
```

責務:
- raw dict を受け取り、feature dict を返す。
- I/Oなし、ネットワークなし、envなし。
- `Measured` を生成し、UNKNOWNを0/falseにしない。

DoD:
- `revenue_growth_yoy`, `operating_margin`, `net_margin`, `roe_proxy`, `equity_ratio`, `fcf_proxy`, `net_cash`, `valuation_status` を返す。
- `roic_proxy` は入力が足りなければ UNKNOWN。無理に出さない。
- 単体テストで欠損 / nan / inf / 分母0 / 前期なしを網羅。

### C-2: builder / derived writer
新規候補:

```text
radar/features/build.py
```

責務:
- explicit `raw_path` + sidecar provenance を読む。
- raw hash を再計算して sidecar と一致確認。
- `available_at <= asof` を検証。
- `data/derived/features/edinet_financials_v1/<asof>/<edinet_code>.json` に書く。

DoD:
- raw本文を stdout/stderr に出さない。
- 書込先は `data/derived/features/edinet_financials_v1` 配下のみ。
- `source_snapshot.used_fields` と各 feature の source_fields を持つ。
- 同一入力で同一出力。

### C-3: CLI 配線
`radar/__main__.py` に純加法で追加:

```bash
python3 -m radar build-features \
  --provider edinet-db \
  --dataset financials \
  --raw-path data/raw/edinet-db/financials/2026-06-18/E02144_period-annual_years-1.json \
  --asof 2026-06-18
```

出力:
- path
- feature count
- UNKNOWN count
- input hash
- 注意: research_queue/evidence/LLM投入は未実装

DoD:
- 既存コマンドのI/O不変。
- `--help` が落ちない。
- 不要引数を静かに無視しない。

### C-4: tests
新規候補:

```text
tests/test_feature_phase_c.py
```

必須ケース:
- 正常rawから derived 生成。
- `available_at > asof` で停止し、derivedを書かない。
- raw_hash mismatch で停止。
- raw_path traversal拒否。
- output path traversal拒否。
- missing previous period → growth/ROE UNKNOWN。
- denominator zero → UNKNOWN。
- nan/inf/non-numeric → UNKNOWN。
- alias conflict → UNKNOWN。
- valuation_status は価格datasetなしで常に UNKNOWN。
- stdout に raw本文 sentinel が出ない。
- `rg` で feature層に `urllib|requests|socket` import が無い。
- non-regression: existing CLI help + key commands。

### C-5: one-file manual verification
既存 live sync raw を使う場合も、出力するのはメタだけ:

```bash
python3 -m radar build-features --provider edinet-db --dataset financials \
  --raw-path data/raw/edinet-db/financials/2026-06-18/E02144_period-annual_years-1.json \
  --asof 2026-06-18
```

確認:
- derived exists
- raw hash ok
- feature count / UNKNOWN count
- raw本文・キー値は出さない

## 2. スコープ外
- J-Quants prices/listed-info sync。
- EDINET DB ratios / analysis scores。
- Daloopa。
- research_queue。
- evidence pack。
- provider raw の Claude投入。
- 銘柄ランキング。
- 「割安」判定。

## 3. 受け入れ基準
- `python3 -m py_compile radar/*.py radar/sources/*.py radar/features/*.py`
- `python3 -m unittest -q`
- `python3 -m unittest -q tests.test_feature_phase_c`
- `python3 -m radar build-features --help`
- `python3 -m radar data-check --offline`
- `python3 -m radar sync --help`
- 既存 `mirror/check/target-check/value-audit` 非回帰。
- `data/derived` は gitignore 済みで、実データは追跡されない。

## 4. レビュー観点
Claude Code には以下を重点監査させる:
- UNKNOWN が 0/false になっていないか。
- raw本文/キー/derived値の過剰表示がないか。
- feature層がネットワークやenvを読んでいないか。
- raw/provenance/hash/PIT が必須か。
- `valuation_status` を勝手に計算していないか。
- research_queue 的な語彙が混入していないか。

## 5. 次フェーズへのゲート
Phase C minimal がGOになっても、次は research_queue ではない。
先に:
1. feature結果の監査レビュー。
2. missing/UNKNOWN率の確認。
3. 必要なら field alias registry の修正。
4. 価格dataset(J-Quants or EDINET DB prices相当)のToS/同期設計。

research_item 生成は、feature が安定し、第三者LLM入力ゲートを再確認してから別PLANで扱う。
