"""Runtime workspace guardrails.

The radar can exist in multiple local checkouts. Data-bearing commands must run
from the configured canonical checkout so analysis cannot silently use stale
derived files from a scratch tree.
"""
from __future__ import annotations

import os
from pathlib import Path


ALLOW_NON_CANONICAL_ENV = "RADAR_ALLOW_NON_CANONICAL"

DEFAULT_ENFORCED_COMMANDS = frozenset({
    "sync",
    "build-features",
    "build-jquants-features",
    "build-company-map",
    "research-queue",
    "evidence",
    "jquants-evidence",
    "llm-brief",
    "audit-report",
    "investor-brief",
    "fetch-jquants",
    "fetch-jquants-bulk",
    "daily-update",
})


def _resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def canonical_status(root: Path, cfg: dict) -> dict:
    runtime = cfg.get("runtime") if isinstance(cfg.get("runtime"), dict) else {}
    configured = runtime.get("canonical_root")
    if not configured:
        return {
            "configured": False,
            "canonical_root": None,
            "current_root": str(_resolve(root)),
            "is_canonical": None,
        }
    canonical = _resolve(str(configured))
    current = _resolve(root)
    return {
        "configured": True,
        "canonical_root": str(canonical),
        "current_root": str(current),
        "is_canonical": current == canonical,
    }


def enforced_commands(cfg: dict) -> set[str]:
    runtime = cfg.get("runtime") if isinstance(cfg.get("runtime"), dict) else {}
    raw = runtime.get("canonical_enforced_commands")
    if raw is None:
        return set(DEFAULT_ENFORCED_COMMANDS)
    if not isinstance(raw, list) or not all(isinstance(x, str) and x for x in raw):
        raise SystemExit("config: runtime.canonical_enforced_commands は非空文字列の配列")
    return set(raw)


def enforce_canonical_root(root: Path, cfg: dict, command: str | None, *, dry_run: bool = False) -> None:
    """Stop data/analysis commands when executed from a non-canonical checkout.

    `dry_run` is allowed because it does not read/write production data. Tests
    and one-off scratch inspection can opt out explicitly with
    RADAR_ALLOW_NON_CANONICAL=1.
    """
    if not command or dry_run:
        return
    if command not in enforced_commands(cfg):
        return
    status = canonical_status(root, cfg)
    if not status["configured"] or status["is_canonical"]:
        return
    if os.environ.get(ALLOW_NON_CANONICAL_ENV) == "1":
        return
    raise SystemExit(
        "canonical root mismatch: このコマンドは正本checkoutでだけ実行できます。\n"
        f"  current: {status['current_root']}\n"
        f"  expected: {status['canonical_root']}\n"
        "  先に `python3 -m radar doctor` で root/data freshness を確認してください。\n"
        f"  検証目的でのみ {ALLOW_NON_CANONICAL_ENV}=1 を明示して迂回できます。"
    )
