#!/usr/bin/env python3
"""CLI for BeadTrain V3 durable orchestration."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

V3_DIR = Path(__file__).resolve().parents[1] / "v3"
sys.path.insert(0, str(V3_DIR))

from engine import (  # noqa: E402
    BeadTrainError,
    append_event,
    execution_packet,
    load_train,
    make_event,
    materialize,
    read_events,
    ready_cars,
    require_claim,
    state_path_for,
)


def _load(path: str):
    train = load_train(Path(path))
    state_path = state_path_for(train.path)
    snapshot = materialize(train, read_events(state_path))
    return train, state_path, snapshot


def _fields(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise BeadTrainError(f"expected key=value evidence, got {value!r}")
        key, item = value.split("=", 1)
        result[key.strip()] = item.strip()
    return result


def command_init(args: argparse.Namespace) -> int:
    train = load_train(Path(args.train))
    state_path = state_path_for(train.path)
    if state_path.exists() and not args.force:
        raise BeadTrainError(f"state already exists: {state_path}")
    if args.force:
        state_path.unlink(missing_ok=True)
    append_event(state_path, make_event(train, "train.initialized", actor=args.actor))
    print(state_path)
    return 0


def command_status(args: argparse.Namespace) -> int:
    train, _, snapshot = _load(args.train)
    print(f"TRAIN {train.name}")
    for car in train.cars:
        state = snapshot.states[car.id]
        lease = f" lease={state.lease_until.isoformat()}" if state.lease_until else ""
        actor = f" actor={state.actor}" if state.actor else ""
        print(f"{car.id:24} {state.state:18}{actor}{lease}")
    return 0


def command_ready(args: argparse.Namespace) -> int:
    _, _, snapshot = _load(args.train)
    for car in ready_cars(snapshot, args.capability):
        print(f"{car.id}\t{car.bead}\t{car.title}")
    return 0


def command_claim(args: argparse.Namespace) -> int:
    train, state_path, snapshot = _load(args.train)
    car = train.car_map.get(args.car)
    if car is None:
        raise BeadTrainError(f"unknown car: {args.car}")
    ready = {item.id for item in ready_cars(snapshot, args.capability)}
    if car.id not in ready:
        raise BeadTrainError(f"car is not ready or capabilities do not match: {car.id}")
    claim = args.claim or __import__("uuid").uuid4().hex
    append_event(state_path, make_event(
        train, "car.claimed", car=car.id, actor=args.actor,
        claim=claim, lease_minutes=args.lease_minutes,
        fields={"capabilities": ",".join(sorted(args.capability))},
    ))
    latest = materialize(train, read_events(state_path))
    print(execution_packet(latest, car, args.actor, claim), end="")
    return 0


def command_start(args: argparse.Namespace) -> int:
    train, state_path, snapshot = _load(args.train)
    require_claim(snapshot, args.car, args.actor, args.claim)
    append_event(state_path, make_event(
        train, "car.started", car=args.car, actor=args.actor,
        claim=args.claim, lease_minutes=args.lease_minutes,
    ))
    print("START-ACK")
    return 0


def command_transition(args: argparse.Namespace, event_type: str) -> int:
    train, state_path, snapshot = _load(args.train)
    if event_type not in {"car.released", "car.superseded"}:
        require_claim(snapshot, args.car, args.actor, args.claim)
    evidence = _fields(args.evidence)
    if args.reason:
        evidence["reason"] = args.reason
    if event_type == "car.completed":
        car = train.car_map[args.car]
        missing = [key for key in car.evidence_required if key not in evidence]
        if missing:
            raise BeadTrainError(f"missing required evidence: {', '.join(missing)}")
    append_event(state_path, make_event(
        train, event_type, car=args.car, actor=args.actor,
        claim=args.claim, fields=evidence,
    ))
    print(event_type.upper().replace(".", "-") + "-ACK")
    return 0


def command_packet(args: argparse.Namespace) -> int:
    train, _, snapshot = _load(args.train)
    car = train.car_map.get(args.car)
    if car is None:
        raise BeadTrainError(f"unknown car: {args.car}")
    state = snapshot.states[car.id]
    print(execution_packet(snapshot, car, state.actor, state.claim), end="")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="BeadTrain V3 orchestration")
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("train")
    init.add_argument("--actor", default="human")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=command_init)

    status = sub.add_parser("status")
    status.add_argument("train")
    status.set_defaults(func=command_status)

    ready = sub.add_parser("ready")
    ready.add_argument("train")
    ready.add_argument("--capability", action="append", default=[])
    ready.set_defaults(func=command_ready)

    claim = sub.add_parser("claim")
    claim.add_argument("train")
    claim.add_argument("car")
    claim.add_argument("--actor", required=True)
    claim.add_argument("--claim")
    claim.add_argument("--lease-minutes", type=int, default=45)
    claim.add_argument("--capability", action="append", default=[])
    claim.set_defaults(func=command_claim)

    start = sub.add_parser("start")
    start.add_argument("train")
    start.add_argument("car")
    start.add_argument("--actor", required=True)
    start.add_argument("--claim", required=True)
    start.add_argument("--lease-minutes", type=int, default=45)
    start.set_defaults(func=command_start)

    packet = sub.add_parser("packet")
    packet.add_argument("train")
    packet.add_argument("car")
    packet.set_defaults(func=command_packet)

    transitions = {
        "complete": "car.completed",
        "review": "car.awaiting_review",
        "validate": "car.validated",
        "fail": "car.failed",
        "block": "car.blocked",
        "release": "car.released",
        "supersede": "car.superseded",
    }
    for name, event_type in transitions.items():
        item = sub.add_parser(name)
        item.add_argument("train")
        item.add_argument("car")
        item.add_argument("--actor", required=True)
        item.add_argument("--claim", default="")
        item.add_argument("--reason")
        item.add_argument("--evidence", action="append", default=[])
        item.set_defaults(func=lambda args, event_type=event_type: command_transition(args, event_type))
    return p


def main() -> int:
    try:
        args = parser().parse_args()
        return int(args.func(args))
    except BeadTrainError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
