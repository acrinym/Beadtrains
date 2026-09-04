#!/usr/bin/env python3
"""Validate BeadTrain v1.3 definitions plus optional V3 protocol fields."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover
    print("Python 3.11+ required (tomllib)", file=sys.stderr)
    raise SystemExit(2)

REQUIRED_TRAIN = ("name", "title", "description", "created", "status")
REQUIRED_CAR = ("id", "bead", "title", "parallel_start", "depends_on", "summary")
REQUIRED_COUPLER = ("id", "from_train", "from_car", "to_train", "to_car", "mode")
VALID_STATUS = {"planned", "in_progress", "complete"}
VALID_COUPLER_MODE = {"after", "with"}
VALID_PROTOCOL_VERSIONS = {"3", "3.0"}


def _load(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _string_list(value: object, label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return [f"{label} must be a list of strings"]
    if any(not isinstance(item, str) or not item.strip() for item in value):
        errors.append(f"{label} must contain only non-empty strings")
    if len(value) != len(set(value)):
        errors.append(f"{label} contains duplicate entries")
    return errors


def _toposort_ok(cars: list[dict]) -> list[str]:
    errors: list[str] = []
    ids = {car.get("id") for car in cars if car.get("id") is not None}
    indegree = {car_id: 0 for car_id in ids}
    adjacency = {car_id: [] for car_id in ids}
    for car in cars:
        car_id = car.get("id")
        for dependency in car.get("depends_on") or []:
            if dependency not in ids:
                errors.append(f"car {car_id}: depends_on '{dependency}' not found in file")
            elif car_id in indegree:
                adjacency[dependency].append(car_id)
                indegree[car_id] += 1
    queue = [car_id for car_id, degree in indegree.items() if degree == 0]
    seen = 0
    while queue:
        current = queue.pop(0)
        seen += 1
        for following in adjacency[current]:
            indegree[following] -= 1
            if indegree[following] == 0:
                queue.append(following)
    if seen != len(indegree):
        errors.append("dependency cycle detected in depends_on graph")
    return errors


def _couplers_ok(data: dict, car_ids: set[str]) -> list[str]:
    errors: list[str] = []
    couplers = data.get("couplers")
    meta = data.get("meta") or {}
    couples_with = meta.get("couples_with") if isinstance(meta, dict) else None
    if couplers is None:
        if couples_with:
            errors.append("[meta].couples_with is set but [[couplers]] is missing")
        return errors
    if not isinstance(couplers, list):
        return ["couplers must be a list of tables"]

    train_name = (data.get("train") or {}).get("name")
    peer_names: set[str] = set()
    seen_ids: set[str] = set()
    for index, coupler in enumerate(couplers):
        if not isinstance(coupler, dict):
            errors.append(f"couplers[{index}] is not a table")
            continue
        for key in REQUIRED_COUPLER:
            if not str(coupler.get(key) or "").strip():
                errors.append(f"coupler {coupler.get('id', index)}: missing '{key}'")
        coupler_id = str(coupler.get("id") or "")
        if coupler_id in seen_ids:
            errors.append(f"duplicate coupler id '{coupler_id}'")
        seen_ids.add(coupler_id)
        if coupler.get("mode") not in VALID_COUPLER_MODE:
            errors.append(f"coupler {coupler_id}: mode must be one of {sorted(VALID_COUPLER_MODE)}")
        if coupler.get("from_train") == train_name:
            peer_names.add(str(coupler.get("to_train") or ""))
            if coupler.get("from_car") not in car_ids:
                errors.append(f"coupler {coupler_id}: from_car not in this train")
            if coupler.get("join_main_at") and coupler.get("join_main_at") not in car_ids:
                errors.append(f"coupler {coupler_id}: join_main_at not in this train")
        if coupler.get("to_train") == train_name:
            peer_names.add(str(coupler.get("from_train") or ""))
            if coupler.get("to_car") not in car_ids:
                errors.append(f"coupler {coupler_id}: to_car not in this train")

    if couples_with is not None:
        errors.extend(_string_list(couples_with, "[meta].couples_with"))
        if isinstance(couples_with, list):
            for peer in couples_with:
                if peer not in peer_names:
                    errors.append(f"[meta].couples_with lists '{peer}' without a matching coupler")
    return errors


def _protocol_ok(data: dict, cars: list[dict]) -> list[str]:
    errors: list[str] = []
    protocol = data.get("protocol")
    if protocol is not None:
        if not isinstance(protocol, dict):
            errors.append("[protocol] must be a table")
        else:
            version = str(protocol.get("version") or "").strip()
            if version and version not in VALID_PROTOCOL_VERSIONS:
                errors.append(f"[protocol].version must be one of {sorted(VALID_PROTOCOL_VERSIONS)}")
            lease = protocol.get("default_lease_minutes")
            if lease is not None and (not isinstance(lease, int) or lease <= 0):
                errors.append("[protocol].default_lease_minutes must be a positive integer")
            for key in ("repository", "branch_policy"):
                if key in protocol and not str(protocol[key]).strip():
                    errors.append(f"[protocol].{key} must be non-empty when supplied")

    for car in cars:
        car_id = car.get("id")
        for key in ("capabilities", "evidence_required"):
            if key in car:
                errors.extend(_string_list(car[key], f"car {car_id}: {key}"))
    return errors


def validate(path: Path) -> list[str]:
    try:
        data = _load(path)
    except Exception as exc:
        return [f"parse error: {exc}"]

    errors: list[str] = []
    train = data.get("train")
    if not isinstance(train, dict):
        return ["missing [train] section"]
    for key in REQUIRED_TRAIN:
        if not str(train.get(key) or "").strip():
            errors.append(f"[train] missing or empty '{key}'")
    if train.get("status") not in VALID_STATUS:
        errors.append(f"[train].status must be one of {sorted(VALID_STATUS)}")
    if str(train.get("name") or "").strip() and path.stem != str(train["name"]).strip():
        errors.append(f"filename stem '{path.stem}' must match [train].name '{train['name']}'")

    cars = data.get("cars")
    if not isinstance(cars, list) or not cars:
        return errors + ["at least one [[cars]] entry required"]
    seen_ids: set[str] = set()
    for index, car in enumerate(cars):
        if not isinstance(car, dict):
            errors.append(f"cars[{index}] is not a table")
            continue
        for key in REQUIRED_CAR:
            if key not in car:
                errors.append(f"car {car.get('id', index)}: missing '{key}'")
        car_id = car.get("id")
        if car_id in seen_ids:
            errors.append(f"duplicate car id '{car_id}'")
        if car_id is not None:
            seen_ids.add(str(car_id))
        if "depends_on" in car:
            errors.extend(_string_list(car["depends_on"], f"car {car_id}: depends_on"))
        if not str(car.get("bead") or "").strip():
            errors.append(f"car {car_id}: empty bead")

    errors.extend(_toposort_ok(cars))
    errors.extend(_couplers_ok(data, seen_ids))
    errors.extend(_protocol_ok(data, cars))
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} <path.beadtrain>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"not found: {path}", file=sys.stderr)
        return 2
    errors = validate(path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
