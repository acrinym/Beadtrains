#!/usr/bin/env python3
"""BeadTrain V3 durable orchestration engine.

Definition remains in .beadtrain TOML. Runtime state is append-only .beadstate text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4
import tomllib

TERMINAL = {"complete", "superseded"}
ACTIVE = {"claimed", "running", "awaiting_review"}
VALID_STATES = {
    "planned", "ready", "claimed", "running", "blocked", "awaiting_review",
    "validated", "complete", "failed", "abandoned", "superseded",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def esc(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace("=", "\\=")


def unesc(value: str) -> str:
    out: list[str] = []
    escaped = False
    for ch in value:
        if escaped:
            out.append("\n" if ch == "n" else ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        else:
            out.append(ch)
    if escaped:
        out.append("\\")
    return "".join(out)


@dataclass(frozen=True)
class Car:
    id: str
    bead: str
    title: str
    summary: str
    depends_on: tuple[str, ...] = ()
    parallel_start: bool = False
    capabilities: tuple[str, ...] = ()
    evidence_required: tuple[str, ...] = ()


@dataclass(frozen=True)
class Train:
    path: Path
    name: str
    title: str
    description: str
    repository: str | None
    branch_policy: str | None
    cars: tuple[Car, ...]

    @property
    def car_map(self) -> dict[str, Car]:
        return {car.id: car for car in self.cars}


@dataclass(frozen=True)
class Event:
    id: str
    at: datetime
    type: str
    train: str
    car: str | None = None
    actor: str | None = None
    claim: str | None = None
    lease_until: datetime | None = None
    fields: dict[str, str] = field(default_factory=dict)


@dataclass
class CarState:
    state: str = "planned"
    actor: str | None = None
    claim: str | None = None
    lease_until: datetime | None = None
    attempt: int = 0
    evidence: dict[str, str] = field(default_factory=dict)
    reason: str | None = None

    def lease_active(self, now: datetime) -> bool:
        return self.lease_until is not None and self.lease_until > now


@dataclass(frozen=True)
class Snapshot:
    train: Train
    states: dict[str, CarState]
    events: tuple[Event, ...]


class BeadTrainError(RuntimeError):
    pass


def load_train(path: Path) -> Train:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    train = data["train"]
    protocol = data.get("protocol") or {}
    cars = tuple(
        Car(
            id=str(raw["id"]),
            bead=str(raw["bead"]),
            title=str(raw["title"]),
            summary=str(raw["summary"]),
            depends_on=tuple(str(x) for x in raw.get("depends_on", [])),
            parallel_start=bool(raw.get("parallel_start", False)),
            capabilities=tuple(str(x) for x in raw.get("capabilities", [])),
            evidence_required=tuple(str(x) for x in raw.get("evidence_required", [])),
        )
        for raw in data.get("cars", [])
    )
    return Train(
        path=path,
        name=str(train["name"]),
        title=str(train["title"]),
        description=str(train["description"]),
        repository=protocol.get("repository"),
        branch_policy=protocol.get("branch_policy"),
        cars=cars,
    )


def state_path_for(train_path: Path) -> Path:
    return train_path.with_suffix(".beadstate")


def append_event(path: Path, event: Event) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"EVENT {event.id}",
        f"at={iso(event.at)}",
        f"type={esc(event.type)}",
        f"train={esc(event.train)}",
    ]
    if event.car is not None:
        lines.append(f"car={esc(event.car)}")
    if event.actor is not None:
        lines.append(f"actor={esc(event.actor)}")
    if event.claim is not None:
        lines.append(f"claim={esc(event.claim)}")
    if event.lease_until is not None:
        lines.append(f"lease_until={iso(event.lease_until)}")
    for key, value in sorted(event.fields.items()):
        lines.append(f"field.{esc(key)}={esc(value)}")
    lines.extend(["END EVENT", ""])
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))


def read_events(path: Path) -> list[Event]:
    if not path.exists():
        return []
    events: list[Event] = []
    current_id: str | None = None
    values: dict[str, str] = {}
    fields: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("EVENT "):
            if current_id is not None:
                raise BeadTrainError("nested EVENT in beadstate")
            current_id = line[6:].strip()
            values = {}
            fields = {}
            continue
        if line == "END EVENT":
            if current_id is None:
                raise BeadTrainError("END EVENT without EVENT")
            events.append(Event(
                id=current_id,
                at=parse_time(values.get("at")) or utc_now(),
                type=values["type"],
                train=values["train"],
                car=values.get("car"),
                actor=values.get("actor"),
                claim=values.get("claim"),
                lease_until=parse_time(values.get("lease_until")),
                fields=dict(fields),
            ))
            current_id = None
            continue
        if current_id is None or "=" not in line:
            raise BeadTrainError(f"invalid beadstate line: {raw_line}")
        key, value = line.split("=", 1)
        if key.startswith("field."):
            fields[unesc(key[6:])] = unesc(value)
        else:
            values[key] = unesc(value)
    if current_id is not None:
        raise BeadTrainError("unterminated EVENT")
    return events


def materialize(train: Train, events: Iterable[Event], now: datetime | None = None) -> Snapshot:
    now = now or utc_now()
    states = {car.id: CarState() for car in train.cars}
    event_list = tuple(events)
    for event in event_list:
        if event.train != train.name or event.car is None or event.car not in states:
            continue
        state = states[event.car]
        if event.type == "car.claimed":
            state.state = "claimed"
            state.actor = event.actor
            state.claim = event.claim
            state.lease_until = event.lease_until
            state.attempt += 1
        elif event.type == "car.started":
            state.state = "running"
            state.actor = event.actor or state.actor
            state.claim = event.claim or state.claim
            state.lease_until = event.lease_until or state.lease_until
        elif event.type == "car.blocked":
            state.state = "blocked"
            state.reason = event.fields.get("reason")
            state.lease_until = None
        elif event.type == "car.failed":
            state.state = "failed"
            state.reason = event.fields.get("reason")
            state.lease_until = None
        elif event.type == "car.released":
            state.state = "planned"
            state.actor = state.claim = None
            state.lease_until = None
        elif event.type == "car.awaiting_review":
            state.state = "awaiting_review"
            state.evidence.update(event.fields)
        elif event.type == "car.validated":
            state.state = "validated"
            state.evidence.update(event.fields)
        elif event.type == "car.completed":
            state.state = "complete"
            state.evidence.update(event.fields)
            state.lease_until = None
        elif event.type == "car.superseded":
            state.state = "superseded"
            state.reason = event.fields.get("reason")
            state.lease_until = None

    for state in states.values():
        if state.state in ACTIVE and not state.lease_active(now):
            state.state = "abandoned"
            state.lease_until = None
    return Snapshot(train, states, event_list)


def ready_cars(snapshot: Snapshot, capabilities: Iterable[str] = ()) -> list[Car]:
    offered = set(capabilities)
    ready: list[Car] = []
    for car in snapshot.train.cars:
        state = snapshot.states[car.id]
        if state.state not in {"planned", "ready", "failed", "abandoned"}:
            continue
        if any(snapshot.states[dep].state not in TERMINAL for dep in car.depends_on):
            continue
        if car.capabilities and not set(car.capabilities).issubset(offered):
            continue
        ready.append(car)
    return ready


def require_claim(snapshot: Snapshot, car_id: str, actor: str, claim: str) -> CarState:
    state = snapshot.states[car_id]
    if state.actor != actor or state.claim != claim or not state.lease_active(utc_now()):
        raise BeadTrainError(f"active claim for {car_id} does not belong to {actor}/{claim}")
    return state


def make_event(train: Train, event_type: str, *, car: str | None = None,
               actor: str | None = None, claim: str | None = None,
               lease_minutes: int | None = None, fields: dict[str, str] | None = None) -> Event:
    now = utc_now()
    return Event(
        id=str(uuid4()), at=now, type=event_type, train=train.name, car=car,
        actor=actor, claim=claim,
        lease_until=now + timedelta(minutes=lease_minutes) if lease_minutes else None,
        fields=fields or {},
    )


def execution_packet(snapshot: Snapshot, car: Car, actor: str | None = None,
                     claim: str | None = None) -> str:
    state = snapshot.states[car.id]
    lines = [
        "BEADTRAIN PACKET 3.0",
        "",
        f"TRAIN {snapshot.train.name}",
        f"TITLE {snapshot.train.title}",
        f"CAR {car.id}",
        f"BEAD {car.bead}",
        f"STATE {state.state}",
    ]
    if snapshot.train.repository:
        lines.append(f"REPOSITORY {snapshot.train.repository}")
    if snapshot.train.branch_policy:
        lines.append(f"BRANCH POLICY {snapshot.train.branch_policy}")
    if actor:
        lines.append(f"ACTOR {actor}")
    if claim:
        lines.append(f"CLAIM {claim}")
    lines += ["", "OBJECTIVE", car.summary.strip(), "", "DEPENDENCIES"]
    lines += [f"  - {dep}: {snapshot.states[dep].state}" for dep in car.depends_on] or ["  - none"]
    lines += ["", "CAPABILITIES"]
    lines += [f"  - {item}" for item in car.capabilities] or ["  - none declared"]
    lines += ["", "EVIDENCE REQUIRED"]
    lines += [f"  - {item}" for item in car.evidence_required] or ["  - acceptance criteria from bead"]
    lines += ["", "HANDOFF CONTRACT", "  Return explicit result, evidence, repository state, and unresolved blockers."]
    return "\n".join(lines) + "\n"
