"""tokenhabit CLI — scan Claude Code logs for token-wasting habits.

    tokenhabit                  # last 7 days, all projects
    tokenhabit --days 14
    tokenhabit --project /path
    tokenhabit --session file.jsonl
    tokenhabit --lang ko
    tokenhabit --json           # machine-readable (CI / piping)

No LLM calls. Standard library only. Runs offline.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import json
import subprocess
import sys

from . import __version__
from .scan import CLAUDE_PROJECTS_DIR, aggregate, analyze_session, collect_jsonl_files
from .report import render, set_color, STR


def _try_ccusage() -> str | None:
    """Best-effort `ccusage daily`. Returns None if missing/failed (graceful skip)."""
    try:
        result = subprocess.run(
            ["npx", "--yes", "ccusage@latest", "daily"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0 and result.stdout.strip():
            return "\n".join(result.stdout.strip().splitlines()[:12])
    except Exception:
        pass
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="tokenhabit",
        description="Scan your Claude Code logs and find the habits burning your tokens.",
    )
    ap.add_argument("--days", type=int, default=7, metavar="N", help="analyze the last N days (default 7)")
    ap.add_argument("--project", type=Path, metavar="PATH", help="a specific project directory")
    ap.add_argument("--session", type=Path, metavar="FILE", help="a single .jsonl session file")
    ap.add_argument("--lang", choices=["en", "ko"], default="en", help="report language (default en)")
    ap.add_argument("--json", action="store_true", help="machine-readable JSON output")
    ap.add_argument("--no-color", action="store_true", help="disable ANSI color")
    ap.add_argument("--ccusage", action="store_true", help="augment with `npx ccusage daily` totals")
    ap.add_argument("--version", action="version", version=f"tokenhabit {__version__}")
    args = ap.parse_args(argv)

    if args.no_color:
        set_color(False)

    files = collect_jsonl_files(project_dir=args.project, session_file=args.session, days=args.days)
    if not files:
        msg = STR.get(args.lang, STR["en"])["no_files"].format(days=args.days, path=CLAUDE_PROJECTS_DIR)
        if args.json:
            print(json.dumps({"error": msg}))
        else:
            print(msg, file=sys.stderr)
        return 1

    results = [analyze_session(f) for f in files]
    agg = aggregate(results)

    if args.json:
        print(json.dumps({
            "meta": {
                "tool": "tokenhabit",
                "version": __version__,
                "days": args.days,
                "file_count": len(files),
                "session_count": agg["session_count"],
                "generated_at": datetime.now().isoformat(),
            },
            "totals": {
                "total_tokens": agg["total_tokens"],
                "total_input": agg["total_input"],
                "total_output": agg["total_output"],
                "total_cache_read": agg["total_cache_read"],
            },
            "pattern_counts": {
                k: v for k, v in agg["pattern_counts"].items()
                if not k.endswith("_tokens") and v > 0
            },
            "sessions": results,
        }, ensure_ascii=False, indent=2))
        return 0

    ccusage_out = _try_ccusage() if args.ccusage else None
    render(agg, args.days, len(files), args.lang, ccusage_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
