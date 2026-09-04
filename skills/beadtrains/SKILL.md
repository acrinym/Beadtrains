---
name: beadtrains
description: >-
  Executes and plans bead trains (.beadtrain TOML manifests). Format v1.3:
  trains named by agent/human, beads = bd ids, cars = arbitrary labels,
  cross-train joins ONLY via [[couplers]]. Parses car order, parallel_start,
  depends_on, couplers; runs bd show/close per car; PR merge cycle and train
  status updates. Use when the user mentions beadtrain, bead train,
  .beadtrain, Car N, "may build", train status, or points at .beadtrain files.
---

# Beadtrains

Install this file as `.cursor/skills/beadtrains/SKILL.md` (or the equivalent Codex/Claude skills path) in the **host** Beads repo.

## Read first

1. [SPEC.md](https://github.com/acrinym/Beadtrains/blob/main/SPEC.md) — format **v1.3**
2. [WORKFLOW.md](https://github.com/acrinym/Beadtrains/blob/main/WORKFLOW.md)
3. Active train file(s) under the host `.beads/*.beadtrain`

Validate (adjust the script path if you copied scripts into `.beads/beadtrains/scripts/`):

```bash
validate-beadtrain .beads/<train>.beadtrain
# or, without install:
python scripts/validate_beadtrain.py .beads/<train>.beadtrain
```

## Finding train files

- **In-repo:** list `.beads/*.beadtrain` or use the path the human gave.
- Do not crawl whole drives with recursive `rg` / `Get-ChildItem`.

## Naming (v1.3)

- **Train** name + filename: agent/human slug
- **`[[cars]].bead`**: real `bd` issue id
- **Car `id`**: arbitrary local label
- **Join trains**: `[[couplers]]` only (`prior_car` is narrative, not a gate)

## Default: run the FULL train

A train is one job. When the human starts a train (or says any car "may build", "build it", "run the train"):

1. Open the matching `.beadtrain`; set `[train].status = "in_progress"` if still `planned`
2. Loop until **all cars are closed** — do not stop after one car to ask permission for the next
3. Each iteration: compute ready cars (deps + coupler gates; respect `parallel_start`) → `bd show` → implement → test → `bd close`
4. Prefer one branch + one PR for the whole train unless they ask otherwise
5. After the last car: set `[train].status = "complete"` and export Beads state

### Forbidden

- Stopping after every car to wait for "Car N+1 may build"
- Asking the human to whistle each car through
- Starting a coupler `to_car` before `from_car` satisfies `mode`

### Exceptions (only)

- They explicitly say stop / pause / only do car X
- A hard blocker needs them (secrets, policy, interactive smoke)
- Capstone needs live soak they already required — finish code cars first

## Scope discipline

Car `summary` + bead acceptance criteria = boundaries. Do not expand. Run the **host** repo's quality gates, not this package's.
