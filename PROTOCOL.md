# BeadTrain V3.0 Protocol Specification

## Purpose

BeadTrain V3 turns a static train plan into a durable orchestration protocol for stateless human and AI collaborators. It preserves Beads as the work-item authority, Git/GitHub as source and review authority, CI as validation authority, and `.beadtrain` as the human-authored plan.

V3 adds a separate append-only `.beadstate` journal, capability-aware ready sets, lease-based claims, explicit acknowledgements, evidence-backed completion, and self-contained execution packets.

## Compatibility

Every valid BeadTrain v1.3 definition remains a valid V3 definition. V3 fields are optional. A train without V3 fields behaves as a train with no declared capability or evidence constraints.

## Artifacts

### `<name>.beadtrain`

Human-authored TOML definition. Existing `[train]`, `[[cars]]`, `[meta]`, and `[[couplers]]` remain canonical.

### `<name>.beadstate`

Append-only UTF-8 runtime journal stored beside the train definition. It is not TOML or JSON. Each record uses explicit opening and closing markers:

```text
EVENT 8e965fc0-...
at=2026-07-19T15:30:00Z
type=car.claimed
train=renderer_train
car=semantic-map
actor=codex
claim=claim-123
lease_until=2026-07-19T16:15:00Z
field.capabilities=csharp,github-write
END EVENT
```

Values escape backslashes, newlines, and equals signs. Existing events are never rewritten.

### Execution packet

A generated `BEADTRAIN PACKET 3.0` text document containing the train, car, bead, objective, dependency state, repository, branch policy, capability requirements, evidence requirements, actor, and claim identity.

## Optional definition fields

### `[protocol]`

```toml
[protocol]
version = "3.0"
repository = "example-org/example-repo"
branch_policy = "one-pr-per-train"
default_lease_minutes = 45
```

### `[[cars]]`

```toml
capabilities = ["csharp", "roslyn", "github-write"]
evidence_required = ["commit", "build", "pull_request", "review_threads"]
```

`capabilities` is a required subset match. A collaborator must advertise every declared capability before claiming the car.

`evidence_required` lists evidence keys that must be present on `car.completed`.

## Car states

Materialized state is derived by replaying the journal:

```text
planned
ready
claimed
running
blocked
awaiting_review
validated
complete
failed
abandoned
superseded
```

`complete` and `superseded` satisfy dependencies. `failed` and `abandoned` may become ready again when their dependencies and capability requirements are satisfied.

## Claims and leases

A claim records:

- actor identity;
- unique claim identity;
- car identity;
- advertised capabilities;
- lease expiration.

Only the matching actor and claim may transition an actively leased car. An expired active claim materializes as `abandoned`, allowing another collaborator to claim the car without deleting history.

A claim is not a permanent assignment. It is temporary collision protection.

## Ready-set computation

A car is ready when:

1. its current state is `planned`, `ready`, `failed`, or `abandoned`;
2. every local `depends_on` car is `complete` or `superseded`;
3. all declared capabilities are present in the collaborator's offered capability set;
4. no active lease owns the car.

Cross-train coupler resolution remains governed by the v1.3 coupler model. The initial V3 engine operates on one train journal at a time; linked-train orchestration may supply satisfied coupler gates to a later repository-level resolver.

## Events and acknowledgements

Canonical event types:

```text
train.initialized
car.claimed
car.started
car.blocked
car.failed
car.released
car.awaiting_review
car.validated
car.completed
car.superseded
```

CLI success output acts as an explicit acknowledgement, including `START-ACK`, `CAR-COMPLETED-ACK`, and equivalent transition acknowledgements.

## Evidence

Evidence is attached as named text fields:

```text
field.commit=abc123
field.build=0 errors, 0 warnings
field.pull_request=702
field.review_threads=0 unresolved
```

Completion fails when any `evidence_required` key is absent. The engine does not claim that evidence is true; validators and repository integrations verify it.

## CLI

```powershell
python .beads/beadtrains/scripts/beadtrain_v3.py init .beads/example.beadtrain
python .beads/beadtrains/scripts/beadtrain_v3.py ready .beads/example.beadtrain --capability csharp
python .beads/beadtrains/scripts/beadtrain_v3.py claim .beads/example.beadtrain car-id --actor codex --capability csharp
python .beads/beadtrains/scripts/beadtrain_v3.py start .beads/example.beadtrain car-id --actor codex --claim <id>
python .beads/beadtrains/scripts/beadtrain_v3.py complete .beads/example.beadtrain car-id --actor codex --claim <id> --evidence commit=abc123
python .beads/beadtrains/scripts/beadtrain_v3.py status .beads/example.beadtrain
```

## Pipeline 2.0 relationship

Pipeline 2.0 supplies structural truth about projects, callers, descendants, and dependencies. BeadTrain V3 supplies work state, routing, claims, handoffs, and evidence. V3 execution packets may later consume `.pipeline` scope information, but neither system owns the other.

## Non-goals

BeadTrain V3 is not a replacement for Beads, Git, GitHub, CI, review bots, or human approval. It does not preserve private chain-of-thought. It records operational state and explicit evidence only.
