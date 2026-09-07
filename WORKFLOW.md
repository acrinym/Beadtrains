# Beadtrain execution workflow

Canonical definitions:

- [SPEC.md](SPEC.md) — v1.3
- [PROTOCOL.md](PROTOCOL.md) — V3 durable orchestration (optional)

## Triggers

Activate when the user mentions **beadtrain**, **bead train**, **`.beadtrain`**, **Car N**, **build it**, **run the train**, train status, or points at `.beadtrain` files.

## Compatibility

- Train names are human/agent-owned slugs.
- `[[cars]].bead` is a real Beads ID (except documented classroom examples).
- Local deps are car IDs in the same file.
- Cross-train joins are `[[couplers]]` only.
- Valid v1.3 files run under V3 without modification.
- Optional `[protocol]`, `capabilities`, and `evidence_required` activate V3.

## Default: run the full train

Starting any car means the train is one continuous job:

1. mark the train `in_progress`;
2. keep executing ready cars until every car is terminal;
3. do not pause between cars unless the human explicitly asks, a hard blocker requires them, or a requested live soak follows completion;
4. prefer one branch and one PR for the train;
5. honor couplers and recompute readiness after every terminal transition.

## Before coding

1. List trains (no drive-wide recursive searches):

```bash
python scripts/beadtrain.py list --dir .beads
python scripts/beadtrain.py ready --dir .beads --issues .beads/issues.jsonl
```

2. Read the train, `[meta].watch`, and couplers (`beadtrain status` / `beadtrain couplers`).
3. Run `bd show <bead>` for every car being considered.
4. Validate:

```bash
python scripts/validate_beadtrain.py path/to/<train>.beadtrain
# or
python scripts/beadtrain.py validate path/to/<train>.beadtrain
```

In a host repo that vendors these scripts under `.beads/beadtrains/`, use that path instead.

5. Read host-repo agent memory / contributing rules.
6. Resolve live git and PR state before editing.

## V3 (optional)

```bash
python scripts/beadtrain_v3.py init path/to/<train>.beadtrain --actor <actor>
python scripts/beadtrain_v3.py ready path/to/<train>.beadtrain --capability python
python scripts/beadtrain_v3.py claim path/to/<train>.beadtrain <car> --actor <id> --capability python --lease-minutes 45
```

The claim command prints a `BEADTRAIN PACKET 3.0`. Preserve the claim ID. A claim is a lease, not permanent ownership.

Never hand-edit `.beadstate` to make history prettier.

## Per-car implementation

- `bd update <id> --status in_progress`
- implement only the car summary and bead acceptance criteria
- run the **host repository's** real quality gates (build, tests, linters as that repo defines)
- close the bead when criteria are met
- append a terminal V3 transition when using V3
- continue immediately to the next ready car

## After completion

- set `[train].status = "complete"`
- preserve `.beadstate` history
- `bd export` (or the host Beads snapshot command)
- do not start a requested post-train soak or a different train before the human gate they asked for
