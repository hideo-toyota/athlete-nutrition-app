# data/ — データ提供元の取得物(構造のみ・A0時点では空)

> ⚠️ A0(ネットワーク無し)では**実データは取得しない**。ここは将来の構造の説明のみ。
> `raw/` `cache/` `derived/` は **`.gitignore` 済み**(ローカル限定・コミットしない)。

```
data/
  raw/<provider>/<dataset>/...   # API生データのpurgeable cache(git除外)
  cache/                         # 一時(git除外)
  derived/<feature_set>/<asof>.json  # 派生(入力field+raw_hash+版情報を内包)(git除外)
  metadata/
    fetch_log.jsonl              # 追記専用: 1 fetch = 1 行(provenance)
    dataset_manifest.json        # 索引
```

詳細は [DATA_LAYER_SPEC.md](../DATA_LAYER_SPEC.md)。取得(sync)は **LICENSE_MATRIX の ToS 確認後(A1以降)**。
