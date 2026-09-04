# Beadtrain format specification v1.3

A `.beadtrain` file describes an ordered sequence of Beads work items — a "train" of cars — planned as one execution arc. Format is TOML. Format family: **`beadtrain/1`**.

## File placement

```
.beads/<name>.beadtrain
```

`<name>` must match `[train].name` (filename stem = train name).

## Naming model (required)

| Thing | Who names it | Rule |
|-------|--------------|------|
| **Train** (`[train].name` + filename stem) | Agent or human | Stable snake_case slug — e.g. `alex_renderer_rewrite`. Legacy `car<N>_…` is optional, not required. |
| **Bead** (`[[cars]].bead`) | Beads CLI (`bd`) | Real issue id `bd` knows. Never invent a fake bead id in a live train. Classroom examples may use placeholders. |
| **Car** (`[[cars]].id`, `title`) | Agent or human | Arbitrary local labels. Unique within that train file only. |

## `[train]` — required

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Snake_case identifier, matches filename stem |
| `title` | string | yes | Human display title |
| `description` | string | yes | Multi-line arc (`"""..."""`) |
| `created` | string | yes | ISO date `"YYYY-MM-DD"` |
| `status` | string | yes | `"planned"` \| `"in_progress"` \| `"complete"` |

## `[[cars]]` — one entry per bead, in execution order

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Local car id |
| `bead` | string | yes | Real `bd` issue id |
| `title` | string | yes | One-line label |
| `parallel_start` | bool | yes | If true, can start with other ready cars |
| `depends_on` | [string] | yes | Car `id`s **in this file**. Never reference another train here — use `[[couplers]]`. |
| `summary` | string | yes | What gets built. Use `"""..."""` for wrapped multiline. |

## `[meta]` — optional but encouraged

| Field | Type | Description |
|-------|------|-------------|
| `one_liner` | string | Whole-train payoff |
| `prior_car` | string | **Narrative only** — does not unlock cars |
| `unblocks` | [string] | Bead IDs unblocked after this train |
| `watch` | string | Risks to watch |
| `couples_with` | [string] | Peer train `name`s. Every entry **must** have a matching coupler row. |

## `[[couplers]]` — required for joining trains (v1.3)

**Joining two trains uses `[[couplers]]` only.** `prior_car` is not a gate.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Short id |
| `from_train` | string | yes | Primary train `name` |
| `from_car` | string | yes | Car on primary that unlocks the join |
| `to_train` | string | yes | Secondary train `name` |
| `to_car` | string | yes | First car on secondary after the join |
| `mode` | string | yes | `"after"` = wait until `from_car` complete; `"with"` = may run once `from_car` is in progress |
| `join_main_at` | string | | Optional later primary car for rejoin |
| `note` | string | | Rationale |

Couplers may live in either file (prefer primary). Honor them when computing ready cars across files.

## Execution semantics

- `parallel_start = true` and empty `depends_on` may start together (after coupler gates allow).
- A car starts only when all in-file `depends_on` cars are complete.
- A coupler `to_car` is not ready until `from_car` satisfies `mode`.
- Prefer a validation/capstone as the last car.
- `[train].status` is updated as the train runs.
- `prior_car` never changes the ready set.

## Example (single train)

```toml
[train]
name        = "alex_example_arc"
title       = "Example arc"
description = """
One paragraph describing the arc.
"""
created     = "2026-07-15"
status      = "planned"

[[cars]]
id             = "foundation"
bead           = "demo-xxxx"
title          = "Foundation work"
parallel_start = true
depends_on     = []
summary        = "What gets built."

[[cars]]
id             = "capstone"
bead           = "demo-yyyy"
title          = "Capstone validation"
parallel_start = false
depends_on     = ["foundation"]
summary        = "Validation capstone."

[meta]
one_liner  = "One sentence payoff."
prior_car  = "alex_previous_arc"
watch      = "Known risks."
```

Live trains must use real `bd` ids, not `demo-xxxx`.

## Coupler example

```toml
[meta]
couples_with = ["alex_follow_on"]

[[couplers]]
id         = "primary-to-follow"
from_train = "alex_example_arc"
from_car   = "capstone"
to_train   = "alex_follow_on"
to_car     = "audit"
mode       = "after"
note       = "Follow-on starts only after the primary capstone."
```

## History

| Date | Version | Note |
|------|---------|------|
| 2026-06-10 | v1 | Format canonized |
| 2026-06-10 | v1.1 | Agent skill + validator |
| 2026-07-11 | v1.2 | Optional `[[couplers]]` + `meta.couples_with` |
| 2026-07-15 | v1.3 | Naming model; cross-train joins **only** via `[[couplers]]`; `prior_car` narrative-only |

See [PROTOCOL.md](PROTOCOL.md) for optional V3 `.beadstate` fields.
