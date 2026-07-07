# Roadmap

Status as of the initial commit: one working case study (`mock_widget`) has
been built and manually verified — imported into both a real Brightway
project and openLCA desktop, matching a hand-calculated expected value
(score = 6.7) exactly, including the full scaling vector and inventory
breakdown, in both engines. The scripts that did this are generalized into
`scripts/import_to_brightway.py` and `scripts/run_check.py`, but have only
been run manually, not wired into CI, and only cover the single linear case.

## Done since initial commit

- [x] Added three more simple linear-chain case studies —
      `mock_cotton_fiber` (2-process, two impact categories sharing a
      common emission), `mock_polyester_tshirt` (3-process, compound
      scaling), `mock_wool_yarn` (2-process, >1.0 scaling factor). Each
      mirrors the topology/teaching point of a real-data case study from
      the `life-cycle-assessment-mcp` repo, rebuilt with round numbers and
      trivial CFs. All four case studies (including `mock_widget`) verified
      manually: 0 unlinked exchanges on import, bw2calc score matches
      `expected.json` exactly. These are still single linear chains, same
      shape as `mock_widget` — none of this is the foreground-after-background
      split that Phase 2 below still needs.
- [x] `build.py` now writes an expanded, checked-in `olca_ld/` JSON-LD
      directory (via `scripts/ld_dir.py`) instead of writing a zip directly
      — this is the browsable source of truth for each case study's
      database structure. `mock_lca.zip` is a regenerate-on-demand build
      artifact (`scripts/make_release.py`), gitignored, not committed.
- [x] Added `pyproject.toml` + `uv.lock` (dependency management via `uv`)
      and a `Makefile` (`build`/`release`/`check`/`clean` targets per case
      study via `CASE=name`, plus `all`/`all-build`/`all-release`/
      `all-check`/`all-clean` looping over every case study).
- [x] Added `scripts/check_case_study.py`, which runs
      `import_to_brightway.py` + `run_check.py` in one step, reading the
      reference product / method name / impact category from metadata now
      recorded directly in each `expected.json`.
- [x] Published a GitHub Release per case study, each with that case
      study's zip attached as a downloadable asset, built from the exact
      committed `olca_ld/` directory and re-verified before publishing.
      Asset is named after the case study (`mock_widget.zip`,
      `mock_cotton_fiber.zip`, etc.), not the generic `mock_lca.zip`
      filename `make release` produces locally — rename before `gh
      release upload` if cutting a new version. Release notes bodies are
      intentionally left empty. Note: GitHub's automatic "Source code
      (zip/tar.gz)" links still appear on every tag-based release
      regardless — that's generated from the tag itself and can't be
      suppressed per-release via `gh`/the API. Current releases:
      `mock_widget-v1`, `mock_cotton_fiber-v2`, `mock_polyester_tshirt-v2`,
      `mock_wool_yarn-v2`.
- [x] `mock_cotton_fiber`, `mock_polyester_tshirt`, and `mock_wool_yarn`
      switched from invented round-number CFs (CF=1, CF=10) to the real
      TRACI v2.1 characterization factors used in each one's source recipe
      card (CH4=25.0, N2O=298.0, NH3=0.1186), so the mock database's
      numbers correspond to the real teaching material rather than an
      arbitrary substitute. `mock_widget` is unaffected — it isn't modeled
      on any real recipe card, so it keeps CF=1/CF=10.
      `expected.json` recalculated by hand (calculator, not mental
      arithmetic, since NH3's CF isn't round) and reverified for all three.
      This obsoleted their original `-v1` releases; those were deleted
      (both the GitHub Release and the underlying git tag, local and
      remote) and replaced with `-v2`, which carry the updated CFs.

Note: none of the above is the pytest/GitHub-Actions CI suite described in
Phase 1 below — checking still happens by running `make check`/`make
all-check` by hand. Phase 1 is still not started.

Everything below is prioritized; do Phase 1 before Phase 2, etc., since
later phases depend on infrastructure earlier phases build.

## Phase 1 — Turn the manual verification into a real CI regression suite

Goal: every push/PR automatically rebuilds every case study, imports it into
a fresh Brightway project, runs the LCA, and fails the build if the result
doesn't match `expected.json`.

- [ ] Write a proper test runner (`tests/test_case_studies.py`, pytest-based)
      that discovers every folder under `case_studies/`, runs its
      `build.py`, imports via `scripts/import_to_brightway.py`, and checks
      against `expected.json` via `scripts/run_check.py`'s logic (import
      the function directly rather than shelling out).
- [ ] Add a GitHub Actions workflow (`.github/workflows/test.yml`) that
      installs `olca-schema`, `bw2data`, `bw2calc`, `bw2io`, and runs the
      pytest suite on every push and PR.
- [ ] Make sure the workflow fails loudly and specifically (which case
      study, which expected value, what was actually computed) — this
      suite's entire value is precise failure localization.

## Phase 2 — Test the actual production import pattern: foreground-after-background

This is the highest-value remaining gap, because it's the one that
mirrors the real BAFU workflow (background imported once, foreground case
studies layered on top) and it's the one already known to break with
`bw2io`'s default strategies.

- [ ] Split `mock_widget` into `mock_background` (Electricity, Steel,
      Transport + their flows/unit groups) and `mock_foreground` (only
      Widget + its flow), with the foreground's technosphere exchanges
      pointing (`defaultProvider`) at the background's process UUIDs
      without redefining them.
- [ ] Import background first, then foreground, as two separate operations
      into the same Brightway project. Confirm (expect) unlinked exchanges
      on both the technosphere and biosphere side, per the gotchas in
      `CLAUDE.md`.
- [ ] Write the two custom linking strategies needed to fix this:
      one for technosphere/production edges (`link_iterable_by_fields`
      pointed at the already-written background database instead of
      `internal=True`), one for biosphere edges (pointed at the real
      target biosphere database instead of a freshly-built one — this is
      the same shape as `JSONLDLCIAImporter.match_biosphere_by_id`, but
      that method doesn't exist on the plain `JSONLDImporter` and needs to
      be added).
- [ ] Confirm the same two-stage import works cleanly and natively in
      openLCA (expected: yes, since openLCA resolves by UUID across the
      whole active database, not batch-scoped) — this is mostly a
      confirmation step, not expected to require any fix.
- [ ] Add this as a second CI-checked case study once the linking strategies
      work, with its own `expected.json`.

## Phase 3 — Allocation / co-products

- [ ] Add `mock_coproduct`: one process (e.g. "Mock Steel production")
      with two functional outputs, clean round-number mass and price bases
      for allocation (e.g. mass split 50/50, price split 30/70), following
      the design discussed in the source conversation this repo grew out
      of.
- [ ] On the Brightway side, use the `multifunctional` package
      (`pip install multifunctional`) — a `MultifunctionalDatabase`, with
      `price`/`mass` properties set on each functional exchange, calling
      `.allocate(strategy_label=...)`. Note from prior investigation: by
      default this creates collapsed "chimaera" process+product nodes;
      explicit product nodes need to be created deliberately to keep the
      process/product separation this repo's other cases rely on.
- [ ] On the openLCA side, use its native allocation method selection
      (physical/economic/causal) in the calculation setup — the schema
      already supports `AllocationFactor`/`AllocationType` natively, and
      `bw2io` already has a matching strategy
      (`bw2io/strategies/json_ld_allocation.py`) that reads this same
      vocabulary, so this may work with less custom code than the
      Brightway-native path.
- [ ] `expected.json` for this case should include the score under *each*
      allocation method tested (mass, economic), not just one — this case
      study's whole value is demonstrating the spread between methods, not
      picking one as "correct."
- [ ] Optionally also add `mock_substitution`: a co-product credited via a
      negative technosphere edge (avoided-burden/system-expansion) instead
      of allocation, since this needs zero special library support in
      either engine and is worth confirming works identically.

## Phase 4 — Supplier alternatives / scenario comparison

- [ ] Add a second background process producing the same product flow as
      an existing one (e.g. "Mock Electricity production (renewable)",
      much lower emission factor), and demonstrate re-pointing one
      `defaultProvider` reference changes the total predictably (this was
      sketched by hand in the source conversation: baseline score 6.7,
      renewable-swap score 4.0).
- [ ] Decide whether scenario handling should be modeled as: (a) multiple
      independent case study zips (baseline vs. renewable, fully separate
      files), or (b) investigate `premise`'s "superstructure database" /
      scenario-difference-file pattern, which Activity Browser has native
      UI support for. Recommend spending an hour evaluating (b) before
      committing to (a), since it may be a better-supported path for the
      real recipe-card tool's eventual scenario needs.

## Phase 5 — Other mechanism-isolating cases (lower priority, do if time)

- [ ] `mock_loop` — a process that indirectly consumes its own output
      (e.g. an energy process using a bit of its own electricity), to
      confirm both engines correctly solve a genuinely cyclic technosphere
      matrix rather than just reading off single-exchange amounts.
- [ ] `mock_units` — deliberately mixed units (kg, L, unit, tkm) with
      non-trivial conversion factors, to catch unit-conversion bugs
      specifically (the current cases avoid this on purpose, using
      conversion_factor=1.0 unit groups everywhere).

## Explicitly out of scope for this repo

- The actual `recipe_card.yaml` schema and its compiler — that lives in
  the separate `life-cycle-assessment-mcp` repo. This repo is the
  benchmark suite that compiler should eventually be checked against
  (once it exists), not the compiler itself.
- Real ecoinvent/BAFU data of any kind. Every flow and process here starts
  with "Mock " and should stay that way — the whole point is data small
  and clean enough to verify by hand.
- SimaPro compatibility. Confirmed SimaPro only imports SimaPro CSV and
  EcoSpold directly (not JSON-LD or ILCD); reachable only via openLCA as a
  conversion hub if it's ever actually needed. Not worth building toward
  unless a concrete need shows up.
