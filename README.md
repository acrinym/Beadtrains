# Beadtrains

**Beads (`bd`) is the issue tracker. Beadtrains is not.**

| | Beads | Beadtrains |
|---|---|---|
| What | Work items, deps, status (`bd create` / `bd close`) | One job: an ordered train of those items |
| File | `.beads/issues.jsonl` + SQLite | `.beads/<name>.beadtrain` (TOML) |
| Authority | The ticket | The plan agents execute without whistling each car |

A train is a TOML manifest: cars point at **real** `bd` ids, run in order (or in parallel when marked), and join other trains **only** through `[[couplers]]`. Format **v1.3** (`beadtrain/1` lineage). Optional **V3** adds an append-only `.beadstate` journal, leases, and evidence packets.

**Requires:** [Beads](https://github.com/steveyegge/beads) (`bd`) installed. This repo does **not** vendor Beads.

## Validate

Python 3.11+ (`tomllib`):

```bash
python scripts/validate_beadtrain.py examples/example_primary_demo.beadtrain
python scripts/validate_beadtrain.py examples/example_secondary_demo.beadtrain
```

Classroom examples use fictional `classroom-demo-*` bead ids so CI stays green without your tracker.

## Run a train (agents)

See [WORKFLOW.md](WORKFLOW.md) and [skills/beadtrains/SKILL.md](skills/beadtrains/SKILL.md). Copy the skill into Cursor/Codex/Claude skills dirs. Default: **the whole train is one job** — do not stop after every car to ask permission.

Optional V3 orchestration: [PROTOCOL.md](PROTOCOL.md) and `scripts/beadtrain_v3.py`.

## Layout

| Path | Role |
|---|---|
| [SPEC.md](SPEC.md) | v1.3 TOML format |
| [WORKFLOW.md](WORKFLOW.md) | Full-train execution |
| `scripts/validate_beadtrain.py` | Schema + coupler + optional V3 field checks |
| `scripts/beadtrain_v3.py` + `v3/engine.py` | Durable state CLI |
| `examples/` | Fictional coupler pair |
| `skills/beadtrains/SKILL.md` | Agent skill |

MIT. Designed by Justin (acrinym). Extracted from a private monorepo so any Beads project can run trains.
