"""日足 OHLCV の読み込み層(標準ライブラリのみ)。

データ源は2つ:
  1. ローカル CSV(既定・オフラインで動く)
  2. J-Quants API(任意。`.env` か環境変数 JQUANTS_API_KEY / JQUANTS_REFRESH_TOKEN)

J-Quants が使えない・失敗する場合は自動的に CSV へフォールバックします。
APIキーはコードに直書きせず、必ず環境変数から読みます。
"""
from __future__ import annotations

import csv
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JQUANTS_BASE = "https://api.jquants.com/v1"


class Bar(dict):
    """date/open/high/low/close/volume を持つ1日分のバー(dict 互換)。"""


def _load_dotenv() -> None:
    """.env があれば os.environ に読み込む(既存の環境変数は上書きしない)。"""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


# ----------------------------------------------------------------------------
# CSV
# ----------------------------------------------------------------------------
def load_csv(path: Path) -> list[Bar]:
    rows: list[Bar] = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                rows.append(Bar(
                    date=r["date"].strip(),
                    open=float(r["open"]),
                    high=float(r["high"]),
                    low=float(r["low"]),
                    close=float(r["close"]),
                    volume=float(r.get("volume") or 0),
                ))
            except (KeyError, ValueError):
                continue
    rows.sort(key=lambda b: b["date"])
    return rows


# ----------------------------------------------------------------------------
# J-Quants(任意)
# ----------------------------------------------------------------------------
def _http_get(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_post(url: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _jquants_id_token() -> str | None:
    """環境変数から idToken を得る。優先順:
    JQUANTS_ID_TOKEN > JQUANTS_REFRESH_TOKEN > JQUANTS_API_KEY(refresh扱い) > mail/pass。
    取得不能なら None を返す(=CSVフォールバック)。
    """
    _load_dotenv()
    if os.environ.get("JQUANTS_ID_TOKEN"):
        return os.environ["JQUANTS_ID_TOKEN"]
    refresh = (os.environ.get("JQUANTS_REFRESH_TOKEN")
               or os.environ.get("JQUANTS_API_KEY"))
    try:
        if not refresh:
            mail = os.environ.get("JQUANTS_MAILADDRESS")
            pw = os.environ.get("JQUANTS_PASSWORD")
            if not (mail and pw):
                return None
            refresh = _http_post(f"{JQUANTS_BASE}/token/auth_user",
                                 {"mailaddress": mail, "password": pw})["refreshToken"]
        q = urllib.parse.urlencode({"refreshtoken": refresh})
        return _http_post(f"{JQUANTS_BASE}/token/auth_refresh?{q}", {})["idToken"]
    except Exception:
        return None


def load_jquants(code: str, date_from: str | None = None,
                 date_to: str | None = None) -> list[Bar]:
    """J-Quants の日足を取得。失敗時は例外を投げる(呼び出し側でフォールバック)。"""
    token = _jquants_id_token()
    if not token:
        raise RuntimeError("J-Quants 認証情報が無いか取得に失敗しました")
    params = {"code": code}
    if date_from:
        params["from"] = date_from
    if date_to:
        params["to"] = date_to
    url = f"{JQUANTS_BASE}/prices/daily_quotes?{urllib.parse.urlencode(params)}"
    payload = _http_get(url, headers={"Authorization": f"Bearer {token}"})
    bars: list[Bar] = []
    for q in payload.get("daily_quotes", []):
        c = q.get("AdjustmentClose") or q.get("Close")
        if c is None:
            continue
        bars.append(Bar(
            date=q.get("Date", ""),
            open=float(q.get("AdjustmentOpen") or q.get("Open") or c),
            high=float(q.get("AdjustmentHigh") or q.get("High") or c),
            low=float(q.get("AdjustmentLow") or q.get("Low") or c),
            close=float(c),
            volume=float(q.get("AdjustmentVolume") or q.get("Volume") or 0),
        ))
    bars.sort(key=lambda b: b["date"])
    return bars


# ----------------------------------------------------------------------------
# 統合ローダ
# ----------------------------------------------------------------------------
def resolve_price_path(entry: dict, cfg: dict) -> Path | None:
    csv_file = entry.get("csv_file")
    if csv_file:
        p = Path(csv_file)
        return p if p.is_absolute() else ROOT / p
    price_dir = cfg.get("price_dir", "data/prices")
    ticker = entry.get("ticker")
    if ticker:
        return ROOT / price_dir / f"{ticker}.csv"
    return None


def load_prices(entry: dict, cfg: dict) -> tuple[list[Bar], str]:
    """銘柄の日足を読み込む。(bars, source_label) を返す。

    cfg['type'] が 'jquants' なら API を試し、失敗時は CSV にフォールバック。
    """
    source_pref = (cfg.get("type") or "csv").lower()
    code = entry.get("jquants_code")

    if source_pref == "jquants" and code:
        try:
            bars = load_jquants(code)
            if bars:
                return bars, "j-quants"
        except Exception:
            pass  # フォールバックへ

    path = resolve_price_path(entry, cfg)
    if path and path.exists():
        return load_csv(path), f"csv:{path.name}"
    return [], "none"


def load_benchmark(cfg: dict) -> list[Bar]:
    bench_file = cfg.get("benchmark_file")
    if not bench_file:
        return []
    p = Path(bench_file)
    if not p.is_absolute():
        p = ROOT / p
    return load_csv(p) if p.exists() else []
