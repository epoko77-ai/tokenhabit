#!/usr/bin/env python3
"""Content-free team export — build what leaves the machine, never strip it.

The structural guarantee here is the direction of construction. This tool does
NOT take a snapshot and delete the sensitive fields; it starts from an empty
document and copies in only what an explicit allowlist permits. Stripping can
miss a field that a future version adds. An allowlist cannot.

What a baseline snapshot actually contains, and why none of it can be shipped
as-is:

    cwd                 /Users/<name>/<repo>        username + repo identity
    memory file paths   /Users/<name>/CLAUDE.md     username + directory layout
    agent/skill names   policyblind-legal-…         internal project names
    session_id          …                           links a record to a person
    transcript_path     ~/.claude/projects/…        username + repo identity

Usage:

    python3 tools/export_team.py --snapshot before.json --out export.json
    python3 tools/export_team.py --snapshot s.json --scan-json scan.json --out e.json
    python3 tools/export_team.py --audit --snapshot before.json    # what leaves, field by field

Names are hashed with an org-local salt by default, so the same agent can be
tracked across two snapshots without ever revealing what it is called. Use
--name-mode drop to omit them entirely, or --name-mode raw only inside an
organisation that has agreed to it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import hmac
import json
import secrets
import statistics
import sys

SCHEMA = "tokenhabit-org-export/1"

# Everything the export may ever contain. Nothing outside this list is written.
ALLOWLIST = {
    "baseline.model": "which model the baseline was taken with (token accounting differs)",
    "baseline.window_tokens": "context window size",
    "baseline.total_tokens": "tokens loaded before the first user message",
    "baseline.categories.*": "per-category token totals from /context",
    "baseline.item_stats.*": "count / total / median / p90 per item group — no names",
    "baseline.items.*.id": "salted hash of the item name (stable, not reversible)",
    "baseline.items.*.tokens": "token cost of that item",
    "baseline.items.*.source": "User / Built-in / Plugin — no plugin name",
    "baseline.items.memory_files.*.extension": "file extension only — never the path",
    "baseline.instruction_files.*": "memory_type + load_reason + extension. No path.",
    "habits.pattern_counts.*": "habit pattern id -> count",
    "habits.pattern_waste_tokens.*": "habit pattern id -> tokens",
    "habits.session_count": "how many sessions were scanned",
    "habits.models.*": "model id -> assistant message count",
    "cohort.*": "member count and k-anonymity verdict",
    "meta.*": "schema, generation time, tool version, salt fingerprint",
}

DROPPED = {
    "cwd": "reveals username and repository identity",
    "session_id / transcript_path": "links a record to an individual",
    "file paths (memory files, logs)": "reveals username and directory layout",
    "item names (unless --name-mode raw)": "reveals internal project names",
    "memory file names (in every mode)": "they are paths — raw mode never exposes them",
    "plugin names inside source": "reveals vendor relationships",
    "prompts, outputs, tool arguments": "never read by this tool in the first place",
}


# ─── salt ─────────────────────────────────────────────────────────────────────

def load_salt(path: Path) -> bytes:
    """Org-local salt. Generated once, never committed, never exported."""
    if path.exists():
        return path.read_bytes().strip()
    salt = secrets.token_hex(32).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(salt + b"\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    print(f"새 salt 생성: {path}  (커밋하지 마세요. 잃으면 과거 export와 대조 불가)",
          file=sys.stderr)
    return salt


def pseudonym(salt: bytes, value: str, length: int = 12) -> str:
    return hmac.new(salt, value.encode("utf-8"), hashlib.sha256).hexdigest()[:length]


def salt_fingerprint(salt: bytes) -> str:
    """Lets two exports be checked for 'same salt' without revealing the salt."""
    return hashlib.sha256(b"fingerprint" + salt).hexdigest()[:16]


# ─── build ────────────────────────────────────────────────────────────────────

def _stats(tokens: list[int]) -> dict:
    known = [t for t in tokens if t]
    if not known:
        return {"count": len(tokens), "total": 0}
    return {
        "count": len(tokens),
        "total": sum(known),
        "median": int(statistics.median(known)),
        "p90": int(sorted(known)[max(0, int(len(known) * 0.9) - 1)]),
        "max": max(known),
    }


# Item groups whose `source` column is a free-form identifier (an MCP server name)
# rather than a fixed category word. Those name the vendor, so they get hashed.
_FREEFORM_SOURCE_GROUPS = {"mcp_tools"}

# Groups whose "name" is a filesystem path, not a label. `--name-mode raw` means
# "our org agreed to see item names", never "export our directory layout", so
# these stay pseudonymised in every mode.
_PATH_NAMED_GROUPS = {"memory_files"}
_KNOWN_SOURCE_WORDS = {"User", "Built-in", "Plugin", "Project", "Local", "AutoMem"}


def _clean_source(source: str | None, group: str, salt: bytes) -> str | None:
    """Normalise a source cell so it never names a vendor or a project.

    'Plugin (vercel)'            -> 'Plugin'
    'plugin_vercel-…_vercel'     -> 'server:<hash>'   (MCP server names)
    anything unrecognised        -> 'other'           (fail closed, never pass through)
    """
    if not source:
        return None
    if group in _FREEFORM_SOURCE_GROUPS:
        return "server:" + pseudonym(salt, f"mcp_server:{source}", 8)
    head = source.split("(")[0].strip()
    return head if head in _KNOWN_SOURCE_WORDS else "other"


def build_export(snapshots: list[dict], scans: list[dict], *,
                 salt: bytes, name_mode: str, min_cohort: int) -> dict:
    out: dict = {
        "meta": {
            "schema": SCHEMA,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "name_mode": name_mode,
            "salt_fingerprint": salt_fingerprint(salt),
        },
        "cohort": {
            "members": max(len(snapshots), len(scans)),
            "min_cohort": min_cohort,
        },
    }
    members = out["cohort"]["members"]
    out["cohort"]["sufficient"] = members >= min_cohort
    if not out["cohort"]["sufficient"]:
        out["cohort"]["note"] = (
            f"코호트 {members}명 < 하한 {min_cohort}명. 개인 특정 위험이 있으므로 "
            "상위 조직에 합산하거나 insufficient data 로 보고할 것.")

    # ── baseline ──────────────────────────────────────────────────────────────
    if snapshots:
        first = snapshots[0].get("context", {})
        base: dict = {
            "model": first.get("model"),
            "window_tokens": first.get("window_tokens"),
            "total_tokens": first.get("total_tokens"),
            "categories": dict(first.get("categories", {})),
            "item_stats": {},
            "items": {},
            "instruction_files": [],
        }
        for group, entries in (first.get("items") or {}).items():
            base["item_stats"][group] = _stats([e.get("tokens") or 0 for e in entries])
            if name_mode == "drop":
                continue
            expose_names = name_mode == "raw" and group not in _PATH_NAMED_GROUPS
            items = []
            for e in entries:
                entry = {
                    "id": e["name"] if expose_names else pseudonym(salt, f"{group}:{e['name']}"),
                    "tokens": e.get("tokens"),
                    "source": _clean_source(e.get("source"), group, salt),
                }
                if group in _PATH_NAMED_GROUPS:
                    # A path tells us the file type; the path itself tells us who you are.
                    entry["extension"] = Path(e["name"]).suffix or None
                items.append(entry)
            base["items"][group] = items
        for rec in snapshots[0].get("instructions_loaded", []):
            path = rec.get("file_path") or ""
            base["instruction_files"].append({
                "memory_type": rec.get("memory_type"),
                "load_reason": rec.get("load_reason"),
                "extension": Path(path).suffix or None,   # path itself never leaves
            })
        out["baseline"] = base

    # ── habits ────────────────────────────────────────────────────────────────
    if scans:
        counts: dict[str, int] = {}
        waste: dict[str, int] = {}
        models: dict[str, int] = {}
        sessions = 0
        for s in scans:
            sessions += int(s.get("meta", {}).get("session_count") or 0)
            for k, v in (s.get("pattern_counts") or {}).items():
                counts[k] = counts.get(k, 0) + int(v)
            for k, v in (s.get("pattern_waste_tokens") or {}).items():
                waste[k] = waste.get(k, 0) + int(v)
            for k, v in (s.get("models") or {}).items():
                models[k] = models.get(k, 0) + int(v)
        out["habits"] = {
            "session_count": sessions,
            "pattern_counts": counts,
            "pattern_waste_tokens": waste,
            "models": models,
        }
    return out


# ─── audit ────────────────────────────────────────────────────────────────────

def print_audit(export: dict) -> None:
    print()
    print("═" * 70)
    print("EXPORT 감사 — 이 머신을 떠나는 것 / 떠나지 않는 것")
    print("═" * 70)
    print()
    print("[나가는 것]  허용목록으로 새로 지은 문서만 나갑니다")
    for field, why in ALLOWLIST.items():
        print(f"  {field:34} {why}")
    print()
    print("[나가지 않는 것]")
    for field, why in DROPPED.items():
        print(f"  {field:34} {why}")
    print()
    print("[실제 산출물에 담긴 최상위 키]")

    def walk(node, prefix="", depth=0):
        if depth > 2 or not isinstance(node, dict):
            return
        for k, v in node.items():
            path = f"{prefix}.{k}" if prefix else k
            kind = type(v).__name__
            size = f" ({len(v)})" if isinstance(v, (dict, list)) else ""
            print(f"  {path:40} {kind}{size}")
            if isinstance(v, dict) and depth < 1:
                walk(v, path, depth + 1)

    walk(export)
    print()
    print("─" * 70)
    print("  구조적 보장: 이 도구는 스냅샷에서 민감 필드를 '지우지' 않습니다.")
    print("  빈 문서에서 시작해 허용목록에 있는 것만 '복사'합니다. 지우는 방식은")
    print("  새 버전이 추가한 필드를 빠뜨릴 수 있지만, 허용목록은 그럴 수 없습니다.")
    print("═" * 70)
    print()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="조직에 올릴 content-free export를 만든다.")
    ap.add_argument("--snapshot", type=Path, nargs="*", default=[],
                    help="baseline_context.py --snapshot 산출물")
    ap.add_argument("--scan-json", type=Path, nargs="*", default=[],
                    help="tokenhabit --json 산출물")
    ap.add_argument("--salt-file", type=Path, default=Path.home() / ".tokenhabit-org-salt",
                    help="조직 salt 파일 (없으면 생성)")
    ap.add_argument("--name-mode", choices=["hash", "drop", "raw"], default="hash",
                    help="항목 이름 처리: hash(기본) / drop(생략) / raw(조직 합의 시에만)")
    ap.add_argument("--min-cohort", type=int, default=5, help="k-익명성 하한 (기본 5)")
    ap.add_argument("--out", type=Path, help="산출 경로 (없으면 표준출력)")
    ap.add_argument("--audit", action="store_true", help="무엇이 나가고 안 나가는지 출력")
    args = ap.parse_args(argv)

    if not args.snapshot and not args.scan_json:
        ap.error("--snapshot 또는 --scan-json 중 하나는 필요합니다")

    snapshots = [json.loads(p.read_text(encoding="utf-8")) for p in args.snapshot]
    scans = [json.loads(p.read_text(encoding="utf-8")) for p in args.scan_json]
    salt = load_salt(args.salt_file)

    export = build_export(snapshots, scans, salt=salt,
                          name_mode=args.name_mode, min_cohort=args.min_cohort)

    if args.audit:
        print_audit(export)

    text = json.dumps(export, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"export 저장: {args.out}  ({len(text):,} bytes)", file=sys.stderr)
        if not export["cohort"]["sufficient"]:
            print("⚠ " + export["cohort"]["note"], file=sys.stderr)
    elif not args.audit:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
