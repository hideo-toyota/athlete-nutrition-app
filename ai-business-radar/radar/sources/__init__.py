"""source 層(J-Quants / EDINET DB)。

A0: ネットワーク無しの骨格のみ。実APIには接続しない(既定 client は接続せず停止)。
secrets/redact・注入可能 fetch・hash・provenance schema を提供。実 client と sync は A1 以降。
"""
