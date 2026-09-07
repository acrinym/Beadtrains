"""Ready-set: local depends_on + coupler gates + optional bd/export status."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from beadtrains.catalog import Car, Train, all_couplers, index_trains

TERMINAL_BEAD = {"closed", "tombstone"}
IN_PROGRESS_BEAD = {"in_progress", "open"}  # "with" needs claimed-or-done; see coupler_satisfied


@dataclass(frozen=True)
class CarView:
    train: str
    car: Car
    reason: str
    bead_status: str | None
    ready: bool


def load_bead_status_jsonl(path: Path) -> dict[str, str]:
    status: dict[str, str] = {}
    if not path.is_file():
        return status
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        bead_id = str(row.get("id") or "").strip()
        state = str(row.get("status") or "").strip()
        if bead_id and state:
            status[bead_id] = state
    return status


def find_issues_jsonl(train_dir: Path) -> Path | None:
    candidates = [
        train_dir / "issues.jsonl",
        train_dir.parent / ".beads" / "issues.jsonl",
    ]
    if train_dir.name == ".beads":
        candidates.insert(0, train_dir / "issues.jsonl")
    for path in candidates:
        if path.is_file():
            return path
    return None


def bead_is_terminal(status: str | None) -> bool:
    if status is None:
        return False
    return status.lower() in TERMINAL_BEAD


def coupler_from_ok(mode: str, from_status: str | None) -> bool:
    if from_status is None:
        return False
    lowered = from_status.lower()
    if mode == "after":
        return bead_is_terminal(lowered)
    if mode == "with":
        return lowered in TERMINAL_BEAD or lowered == "in_progress"
    return False


def _incoming_couplers(trains: dict[str, Train]) -> dict[tuple[str, str], list[tuple[str, str, str]]]:
    incoming: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
    for _host, coupler in all_couplers(list(trains.values())):
        key = (coupler.to_train, coupler.to_car)
        incoming.setdefault(key, []).append(
            (coupler.from_train, coupler.from_car, coupler.mode)
        )
    return incoming


def car_readiness(
    train: Train,
    car: Car,
    trains: dict[str, Train],
    bead_status: dict[str, str],
    incoming: dict[tuple[str, str], list[tuple[str, str, str]]],
    have_status: bool,
) -> CarView:
    own_status = bead_status.get(car.bead)
    if bead_is_terminal(own_status):
        return CarView(train.name, car, "bead already closed", own_status, False)

    for dep_id in car.depends_on:
        dep = train.car_by_id().get(dep_id)
        if dep is None:
            return CarView(train.name, car, f"depends_on '{dep_id}' missing", own_status, False)
        dep_status = bead_status.get(dep.bead)
        if have_status:
            if not bead_is_terminal(dep_status):
                return CarView(
                    train.name,
                    car,
                    f"waiting on local car '{dep_id}' ({dep.bead}={dep_status or 'unknown'})",
                    own_status,
                    False,
                )
        else:
            # Plan-only: local deps are treated as blocking until status is known.
            return CarView(
                train.name,
                car,
                "bead status unknown (pass --issues or put issues.jsonl in .beads/)",
                None,
                False,
            )

    gates = incoming.get((train.name, car.id), [])
    for from_train, from_car, mode in gates:
        peer = trains.get(from_train)
        if peer is None:
            return CarView(
                train.name,
                car,
                f"coupler peer train '{from_train}' not loaded",
                own_status,
                False,
            )
        source = peer.car_by_id().get(from_car)
        if source is None:
            return CarView(
                train.name,
                car,
                f"coupler from_car '{from_car}' missing on {from_train}",
                own_status,
                False,
            )
        from_status = bead_status.get(source.bead)
        if not have_status:
            return CarView(
                train.name,
                car,
                "bead status unknown (coupler gate needs bd/export)",
                None,
                False,
            )
        if not coupler_from_ok(mode, from_status):
            return CarView(
                train.name,
                car,
                f"coupler {mode} waiting on {from_train}/{from_car} ({source.bead}={from_status or 'unknown'})",
                own_status,
                False,
            )

    if not have_status:
        return CarView(
            train.name,
            car,
            "bead status unknown (pass --issues or put issues.jsonl in .beads/)",
            None,
            False,
        )
    return CarView(train.name, car, "ready", own_status, True)


def ready_views(
    train_list: list[Train],
    bead_status: dict[str, str] | None,
) -> list[CarView]:
    trains = index_trains(train_list)
    incoming = _incoming_couplers(trains)
    have_status = bead_status is not None
    status = bead_status or {}
    views: list[CarView] = []
    for train in train_list:
        for car in train.cars:
            views.append(car_readiness(train, car, trains, status, incoming, have_status))
    return views
