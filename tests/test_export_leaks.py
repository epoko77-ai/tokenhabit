#!/usr/bin/env python3
"""Export leak tests — nothing identifying may leave the machine.

These run against a synthetic snapshot seeded with markers that must never
appear in an export: a username, absolute paths, internal project names, a
vendor name, a session id. If a future field carries one through, this fails.

The allowlist construction in export_team.py is what makes that guarantee
possible; this file is what proves it still holds.

Run: python3 tests/test_export_leaks.py
"""

from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.export_team import build_export  # noqa: E402

FAILURES: list[str] = []

# Markers planted in the input. None may survive into the export.
MARKERS = {
    "username": "jdoe",
    "abs path": "/Users/jdoe/work/secret-repo",
    "project name": "projectatlas",
    "vendor name": "acmecorp",
    "session id": "b3f1c9de-0000-4444-8888-aaaabbbbcccc",
    "repo name": "secret-repo",
}

SALT = b"test-salt-not-a-real-one"


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}{(' — ' + detail) if detail else ''}")
        FAILURES.append(name)


def synthetic_snapshot() -> dict:
    return {
        "snapshot_version": 1,
        "taken_at": "2026-08-16T00:00:00+00:00",
        "cwd": MARKERS["abs path"],
        "context": {
            "evidence": "runtime_observed",
            "model": "claude-haiku-4-5",
            "total_tokens": 48_200,
            "window_tokens": 200_000,
            "categories": {"Custom agents": 20_800, "Skills": 2_000, "Free space": 151_800},
            "items": {
                "custom_agents": [
                    {"name": f"{MARKERS['project name']}-architect", "source": "User", "tokens": 305},
                    {"name": "generic-writer", "source": f"Plugin ({MARKERS['vendor name']})", "tokens": 120},
                ],
                "skills": [
                    {"name": f"{MARKERS['repo name']}-deploy", "source": "User", "tokens": 20},
                ],
                "mcp_tools": [
                    {"name": f"mcp__{MARKERS['vendor name']}__buy", "source": f"plugin_{MARKERS['vendor name']}", "tokens": 531},
                ],
                "memory_files": [
                    {"name": f"{MARKERS['abs path']}/CLAUDE.md", "source": "Project", "tokens": 3_200},
                ],
            },
            "unparsed_sections": [],
        },
        "instructions_loaded": [
            {"file_path": f"{MARKERS['abs path']}/CLAUDE.md",
             "memory_type": "Project", "load_reason": "session_start"},
        ],
    }


def synthetic_scan() -> dict:
    return {
        "meta": {"session_count": 12},
        "totals": {"total_tokens": 1_000},
        "models": {"claude-opus-5": 40},
        "pattern_counts": {"H2-01": 7, "H1-03": 2},
        "pattern_waste_tokens": {"H1-03_tokens": 40_000},
        # A future version could add this. It must not survive.
        "sessions": [{"file": f"{MARKERS['abs path']}/session.jsonl",
                      "session_id": MARKERS["session id"]}],
    }


def test_no_markers_survive():
    print("모든 name_mode 에서 식별자가 살아남지 않는다")
    for mode in ("hash", "drop"):
        export = build_export([synthetic_snapshot()], [synthetic_scan()],
                              salt=SALT, name_mode=mode, min_cohort=5)
        blob = json.dumps(export, ensure_ascii=False).lower()
        for label, marker in MARKERS.items():
            check(f"[{mode}] {label} 미포함", marker.lower() not in blob,
                  f"'{marker}' 가 export 에 남았다")


def test_raw_mode_is_opt_in_only():
    print("raw 모드는 이름을 그대로 싣는다 — 조직 합의가 있을 때만 써야 한다")
    export = build_export([synthetic_snapshot()], [], salt=SALT,
                          name_mode="raw", min_cohort=5)
    blob = json.dumps(export, ensure_ascii=False).lower()
    check("raw 는 항목 이름을 노출한다(설계된 동작)",
          MARKERS["project name"] in blob)
    check("raw 여도 cwd·경로는 여전히 안 나간다",
          MARKERS["abs path"].lower() not in blob)


def test_unknown_source_fails_closed():
    print("모르는 source 값은 통과시키지 않고 'other' 로 닫는다")
    snap = synthetic_snapshot()
    snap["context"]["items"]["custom_agents"][0]["source"] = "SomethingBrandNew(secret)"
    export = build_export([snap], [], salt=SALT, name_mode="hash", min_cohort=5)
    sources = {e["source"] for e in export["baseline"]["items"]["custom_agents"]}
    check("미지의 source 는 'other'", "other" in sources)
    check("원본 문자열 미포함",
          "somethingbrandnew" not in json.dumps(export).lower())


def test_cohort_floor():
    print("k-익명성 하한")
    small = build_export([synthetic_snapshot()], [], salt=SALT, name_mode="hash", min_cohort=5)
    check("코호트 1명이면 insufficient", small["cohort"]["sufficient"] is False)
    check("사유 문구 포함", "note" in small["cohort"])

    big = build_export([synthetic_snapshot()] * 6, [], salt=SALT, name_mode="hash", min_cohort=5)
    check("코호트 6명이면 sufficient", big["cohort"]["sufficient"] is True)


def test_salt_is_never_exported():
    print("salt 자체는 절대 나가지 않는다 (지문만)")
    export = build_export([synthetic_snapshot()], [], salt=SALT, name_mode="hash", min_cohort=5)
    blob = json.dumps(export)
    check("salt 원문 미포함", SALT.decode() not in blob)
    check("지문은 포함", len(export["meta"]["salt_fingerprint"]) == 16)


def test_pseudonyms_are_stable_and_salt_dependent():
    print("가명은 같은 salt 에서 안정적이고, 다른 salt 에서는 달라진다")
    a = build_export([synthetic_snapshot()], [], salt=SALT, name_mode="hash", min_cohort=5)
    b = build_export([synthetic_snapshot()], [], salt=SALT, name_mode="hash", min_cohort=5)
    c = build_export([synthetic_snapshot()], [], salt=b"a-different-salt", name_mode="hash", min_cohort=5)
    ids = lambda e: [i["id"] for i in e["baseline"]["items"]["custom_agents"]]  # noqa: E731
    check("같은 salt -> 같은 가명 (시점 비교 가능)", ids(a) == ids(b))
    check("다른 salt -> 다른 가명 (조직 간 대조 불가)", ids(a) != ids(c))


def main() -> int:
    for fn in (test_no_markers_survive, test_raw_mode_is_opt_in_only,
               test_unknown_source_fails_closed, test_cohort_floor,
               test_salt_is_never_exported, test_pseudonyms_are_stable_and_salt_dependent):
        fn()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("all export leak tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
