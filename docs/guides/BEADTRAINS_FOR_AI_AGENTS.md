# Beadtrains for AI agents

Beads (`bd`) owns work items. A `.beadtrain` is the **order** those items run as **one job**.

This is not a second issue tracker. Do not invent bead ids. Do not stop after every car.

## Commands

Install from this repo (`pip install -e .`) or run the shim:

```bash
beadtrain list --dir .beads
beadtrain status <train-name>
beadtrain ready --dir .beads --issues .beads/issues.jsonl
beadtrain couplers --dir .beads
beadtrain init my_arc --template capability --dir .beads --bead-prefix PREFIX
beadtrain validate .beads/
```

Without install:

```bash
python scripts/beadtrain.py list --dir .beads
python scripts/validate_beadtrain.py examples/
```

`ready` uses a `bd export` JSONL (`issues.jsonl`). It does not call `bd` itself. If that file is missing, cars are listed as waiting — not guessed ready.

## How to run a train

1. `beadtrain list` / `beadtrain ready` to see what can start.
2. Set `[train].status = "in_progress"`.
3. For each ready car: `bd show`, implement only that car’s summary + bead acceptance, run the **host** repo’s gates, `bd close`.
4. Recompute ready. Continue until every car’s bead is closed.
5. Set `[train].status = "complete"`. Export beads if the host repo tracks `issues.jsonl`.

Do not ask the human to whistle each car. Exceptions: they said stop; a secret/policy/live soak only they can do; soak after the train, not between cars.

## Templates

`beadtrain init NAME --template …`

| Template | What you get |
|----------|----------------|
| `capability` | foundation → two parallel cars → capstone |
| `audit_then_build` | audit → map → two drafts → assemble → capstone |
| `coupled` | primary + secondary files and one `[[couplers]]` `after` join |

Placeholder `bead` fields must be replaced with real `bd create` ids before execution. Classroom examples use `classroom-demo-*` on purpose and are not live tickets.

## Couplers

Cross-train joins are `[[couplers]]` only. `depends_on` never names another file. `prior_car` is a sentence, not a gate.

- `after` — `to_car` waits until `from_car`’s bead is closed
- `with` — `to_car` may start once `from_car` is `in_progress` or closed

## Anti-patterns

- Treating the train file as a todo list you tick without `bd close`
- One PR per car when the human wanted one PR for the train
- Starting the next *train* before a soak they required
- Expanding a car past its summary

## GUI

[Beadbox](https://github.com/beadbox/beadbox) can show trains for a workspace that has `*.beadtrain` files next to beads. Same rules. It still does not replace `bd`.
