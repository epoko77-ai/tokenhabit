# Changelog

All notable changes to this project are documented here.
This project follows [Semantic Versioning](https://semver.org/).

---

## [1.3.2] — 2026-08-16

**Three factual errors in the catalog, and a hardcoded cache TTL that is wrong for
most users. Found by an independent review (codex/gpt-5.6-sol) plus a re-read of
the official prompt-caching documentation.**

### Fixed — H4-03 said three things that are not true

The v1.3.0 "what invalidates the cache" expansion was wrong on three counts.
Corrected against [Claude Code prompt caching](https://code.claude.com/docs/en/prompt-caching):

- **Editing CLAUDE.md mid-session does NOT invalidate the cache.** Project-root and
  user CLAUDE.md are read once at session start and held in memory. The edit also
  does not apply until `/clear`, `/compact`, or restart.
- **Connecting or disconnecting an MCP server only invalidates the cache when its
  tools are loaded into the prefix.** With tool search — the default on supported
  models — the tools are deferred and the cache survives.
- **Enabling or disabling a plugin only matters when the plugin provides an MCP
  server.** Skills, commands, agents, hooks, LSP servers, monitors and themes never
  invalidate the cache; their content is appended after the cached prefix.

Also added the full official list of what does and does not invalidate the cache,
including fast mode and whole-tool deny rules, and the fact that invoking a skill
appends a user message rather than changing the prefix.

### Fixed — cache TTL is not always five minutes

`CACHE_TTL_SECONDS` was hardcoded to 300. Officially the TTL depends on how you
authenticate: **one hour on a Claude subscription** (requested automatically),
five minutes on an API key, Bedrock, Vertex or Foundry, and five minutes again when
a subscription is drawing on usage credits. Subagents use five minutes even on a
subscription.

The log does not record the auth method, so the default is now 3600 — the common
case for Claude Code — and `TOKENHABIT_CACHE_TTL` overrides it. This makes H4-03
charge fewer model switches, not more: a longer window means more gaps count as
"the cache was still warm anyway".

### Fixed — a savings estimate that confused throughput with billing

H3-01 claimed "trimming 3,000 tokens from CLAUDE.md saves 300,000 tokens over a
100-turn session". CLAUDE.md sits in the cached prefix and is served at the cache
read rate from the second turn onward, so multiplying by turn count describes
context throughput, not cost. Replaced with what can honestly be said — the
per-session context reduction — plus the actual cost formula.

### Changed

- The evidence grades from 1.3.1 now appear consistently in the skill, the coaching
  checklist and both READMEs. 1.3.1 fixed the code but left four documents saying
  "measured" for character conversions.

---

## [1.3.1] — 2026-08-16

**A labelling correction. Two patterns claimed their numbers came from the log's
token counters when they came from a character conversion.**

### Fixed

- **H2-02 and H8-02 were labelled "measured".** Their waste is computed by
  `_est_tokens()` — characters converted at 4/token (English) and 2/token
  (Korean) — not by any token counter in the log. Calling that a measurement
  was exactly the failure this project criticises in others: a confident number
  whose stated basis is wrong.

### Changed

Waste is now graded in three, and the report says which one it is:

| Grade | Meaning | Patterns |
|---|---|---|
| **observed** | the log's own token counters | H4-03, H1-03 |
| **estimated** | real content, characters converted to tokens | H2-02, H8-02 |
| **heuristic** | a scenario constant x hit count | H2-01, H5-04, H8-01 |
| signal | counted, never scored | H1-01, H2-04, H4-04, H8-03 |

Totals are unchanged — only the claim about where they come from is. If you ran
1.3.0, your numbers are the same; two of them were described wrongly.

---

## [1.3.0] — 2026-08-15

**A correctness release. If you have run tokenhabit before, your score will change — see
[Why your score changed](#why-your-score-changed) below. The old numbers were wrong.**

### Fixed — detectors that never fired

Four of the eleven advertised detectors were silently broken. They are now covered by
regression tests (`tests/test_detectors.py`) that reproduce each failure.

- **H8-03 (subagent overuse) counted nothing.** Claude Code records subagent spawns as
  the `Agent` tool; the scanner only looked for `Task`. Real logs showed `Agent: 134,
  Task: 0`, so this detector was structurally incapable of firing. Both names are now
  accepted (`Task` for older logs); the `TaskCreate`/`TaskUpdate` todo tools are
  correctly excluded.
- **H8-01 (main-thread exploration) could never reach its threshold.** A turn was
  counted per JSONL line, but Claude Code writes the parallel tool calls of one
  assistant turn as *separate lines sharing a `message.id`*. Maximum observable Reads
  per "turn" was therefore 1, against a threshold of 4. Turns are now grouped by
  `message.id`.
- **H8-02 (stdout flood) never reached the report.** The pattern existed in the catalog
  but was never written into the aggregate. Large tool results are now attributed to
  their originating tool via `tool_use_id`, so Bash floods (H8-02) are separated from
  other oversized results (H2-02).
- **H1-01 / H1-03 flagged almost every session.** The 50K ceiling — a *context size*
  threshold — was compared against session-cumulative totals including `cache_read`.
  With cache hit rates above 90%, any session of moderate length exceeded it within a
  few turns. Context size is now the per-turn `input + cache_read + cache_creation`.

### Fixed — detectors that fired when they shouldn't

- **H4-03 (cache-kill switch) blamed you for things that are not habits.** It inferred
  model switches from cache hit-rate crashes, which also occur on session resume,
  auto-compact, and ordinary 5-minute cache TTL expiry. On a real 7-day window it
  reported 19 switches in sessions where the model never changed. It now reads
  `message.model` directly, ignores `<synthetic>` entries, and skips gaps longer than
  the cache TTL.
- **Subagent transcripts were billed to you.** Files marked `isSidechain` were scanned
  as if they were your own sessions, so an agent's file reads and command output landed
  in *your* habit score. They are now excluded by default (`--include-subagents` to
  opt in).
- **Chunked reads counted as re-reads.** Reading a large file in `offset`/`limit` slices
  is correct behaviour, not a re-read. Dedup now keys on `(file_path, offset, limit)`.
  The `hook_check.py` runtime warning was corrected the same way.

### Changed — how waste is calculated

Waste is now reported in three explicitly labelled kinds, because the previous single
"est. waste" number was dominated by scenario constants stacked on over-detection:

| Kind | Patterns | Source |
|---|---|---|
| **measured** | H2-02, H8-02, H4-03, H1-03 | token counts recorded in the log |
| **estimated** | H2-01, H5-04, H8-01 | scenario constant × hit count |
| **signal** (not scored) | H1-01, H2-04, H4-04, H8-03 | counted and shown, never summed |

A long session, a web search, a subagent spawn, or staying on one model tier is not
waste by itself, so none of them are charged to the score any more.

### Added

- **H2-05 · Insurance attachments** — attaching files "just in case". Every attached
  file rides along in every later turn, and Claude will read what it needs if you give
  it a path.
- **H4-04 · Top-tier-only driving** — never leaving the most expensive model tier.
  Auto-detected from `message.model` (signal only). Official list prices differ 5x
  (Opus 5 vs Haiku 4.5) to 10x (Fable 5 vs Haiku 4.5) — and lint, format and rename
  need no model at all.
- **H9 · Billing habits** (new category) — **H9-01 · Overlapping subscriptions**.
  Leaves no trace in token logs and cannot be auto-detected; the skill now asks about
  it explicitly during diagnosis.
- **H4-03 expanded** — mid-session MCP server, plugin, and CLAUDE.md changes also void
  the prompt cache, not just model switches. Invalidation cascades
  `tools → system → messages`.
- `--include-subagents` flag.
- `tests/test_detectors.py` — 26 assertions over synthetic sessions, run in CI.
- `tests/make_demo_logs.py` — regenerates the README sample output reproducibly.
- CI workflow (Python 3.9 / 3.12 / 3.13).

### Changed — project structure

- **Detection logic now has one home.** `tokenhabit/` is the single source of truth;
  the skill ships a generated copy under `skill/scripts/_vendor/` so it runs without a
  pip install, and `skill/scripts/sync_vendor.py --check` fails CI if the two drift.
  Previously the same constants and catalog lived in four places and had already
  diverged.
- `skill/scripts/habit_scan.py` is now a thin entry point (Korean output by default).

### Docs

- **README sample output was arithmetically impossible** (cache hits of 1.25 billion
  against a 9.1 million token total). Replaced with real output from generated logs.
- **"Runs fully offline" was not true of the skill script**, which invoked
  `npx ccusage` unconditionally. Network access is now opt-in (`--ccusage`) everywhere,
  and the claim is stated accurately.
- Log path corrected to `~/.claude/projects/**/*.jsonl` (it is nested).
- **New: official-figures reference** (`skill/references/measurement_and_hooks.md` §5).
  Every price, multiplier and saving rate in this project is now traceable to provider
  documentation — cache reads at 0.1x, writes at 1.25x/2x, Batch API at 50%, the real
  model tier ratios. Widely circulated figures that conflict with official numbers are
  named as such.
- **New: positioning statement.** The goal is removing waste, not spending less.
  Rationing tokens until you cannot finish the job is a more expensive mistake than the
  waste itself.

### Why your score changed

Your habits did not change; the measurement did. Expect all of these:

- **Score may go down.** H1-01 and H1-03 no longer fire on nearly every session, and
  H4-03 no longer fires on session resumes. If your previous grade was driven by those,
  it was inflated.
- **Score may go up.** H8-01, H8-02 and H8-03 were reporting zero. If you actually have
  those habits, they will now appear.
- **New patterns may appear.** H4-04 shows up if you never left the top model tier.
- **Session counts may drop.** Subagent transcripts are no longer counted as your
  sessions.

Numbers remain trend-spotting approximations, not billing. Compare runs only within the
same version and the same `--days` window.

---

## [1.2.1] — 2026-06-15

- Added `--current` (scan only the most recently modified session).
- Skill and CLI reported different scores; `habit_scan.py` gained Token Waste Score
  (A–F) output to match.

## [1.2.0] — 2026-06-15

- First PyPI release of the standalone CLI (`uvx tokenhabit`).
- Habit catalog expanded to 28 patterns across 8 categories.
- README badges, demo GIF, issue templates.

## [1.1.0] — 2026-06

- Claude Code skill: catalog, measurement adapter, runtime hook.

[1.3.2]: https://github.com/epoko77-ai/tokenhabit/releases/tag/v1.3.2
[1.3.1]: https://github.com/epoko77-ai/tokenhabit/releases/tag/v1.3.1
[1.3.0]: https://github.com/epoko77-ai/tokenhabit/releases/tag/v1.3.0
[1.2.1]: https://github.com/epoko77-ai/tokenhabit/releases/tag/v1.2.1
[1.2.0]: https://github.com/epoko77-ai/tokenhabit/releases/tag/v1.2.0
