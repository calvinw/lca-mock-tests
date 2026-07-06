# Roadmap

Status as of the initial commit: one working case study (`mock_widget`) has
been built and manually verified — imported into both a real Brightway
project and openLCA desktop, matching a hand-calculated expected value
(score = 6.7) exactly, including the full scaling vector and inventory
breakdown, in both engines. The scripts that did this are generalized into
`scripts/import_to_brightway.py` and `scripts/run_check.py`, but have only
been run manually, not wired into CI, and only cover the single linear case.

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
