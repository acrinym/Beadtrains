#!/usr/bin/env python3
"""Validate BeadTrain v1.3 definitions plus optional V3 protocol fields.

Single files are checked in isolation. Passing several files (or a directory)
also checks that [[couplers]] resolve against peer trains in that set.
This package does not run trains, talk to bd, or track its own development.
"""
from __future__ import annotations

import argparse
import re
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
CREATED_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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
    created = str(train.get("created") or "").strip()
    if created and not CREATED_DATE.match(created):
        errors.append("[train].created must be YYYY-MM-DD")
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


def iter_train_files(raw: Path) -> list[Path]:
    """Resolve a file or a shallow directory of .beadtrain files (dir and one child level)."""
    if raw.is_file():
        return [raw.resolve()]
    if raw.is_dir():
        found = [*sorted(raw.glob("*.beadtrain")), *sorted(raw.glob("*/*.beadtrain"))]
        unique: list[Path] = []
        seen: set[Path] = set()
        for path in found:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                unique.append(resolved)
        return unique
    return []


def _car_ids(data: dict) -> set[str]:
    cars = data.get("cars")
    if not isinstance(cars, list):
        return set()
    return {str(car.get("id")) for car in cars if isinstance(car, dict) and car.get("id")}


def _cross_file_couplers(loaded: dict[str, tuple[Path, dict]]) -> list[str]:
    """Resolve coupler endpoints across a set of trains. Missing peers are errors."""
    errors: list[str] = []
    names = set(loaded)
    for train_name, (path, data) in loaded.items():
        couplers = data.get("couplers")
        if not isinstance(couplers, list):
            continue
        for coupler in couplers:
            if not isinstance(coupler, dict):
                continue
            coupler_id = str(coupler.get("id") or "")
            from_train = str(coupler.get("from_train") or "")
            to_train = str(coupler.get("to_train") or "")
            from_car = str(coupler.get("from_car") or "")
            to_car = str(coupler.get("to_car") or "")
            if from_train not in names:
                errors.append(
                    f"{path.name}: coupler {coupler_id}: from_train '{from_train}' not in this set"
                )
                continue
            if to_train not in names:
                errors.append(
                    f"{path.name}: coupler {coupler_id}: to_train '{to_train}' not in this set "
                    "(pass the peer .beadtrain too)"
                )
                continue
            from_ids = _car_ids(loaded[from_train][1])
            to_ids = _car_ids(loaded[to_train][1])
            if from_car not in from_ids:
                errors.append(
                    f"{path.name}: coupler {coupler_id}: from_car '{from_car}' "
                    f"not in train {from_train}"
                )
            if to_car not in to_ids:
                errors.append(
                    f"{path.name}: coupler {coupler_id}: to_car '{to_car}' "
                    f"not in train {to_train}"
                )
    return errors


def validate_paths(paths: list[Path]) -> dict[Path, list[str]]:
    """Validate each path, then coupler endpoints across successfully parsed trains."""
    per_file: dict[Path, list[str]] = {}
    loaded: dict[str, tuple[Path, dict]] = {}
    name_owners: dict[str, Path] = {}

    for path in paths:
        file_errors = validate(path)
        per_file[path] = list(file_errors)
        if file_errors:
            continue
        data = _load(path)
        name = str((data.get("train") or {}).get("name") or "").strip()
        if not name:
            continue
        if name in name_owners and name_owners[name] != path:
            clash = f"[train].name '{name}' also used by {name_owners[name].name}"
            per_file[path].append(clash)
            per_file[name_owners[name]].append(f"[train].name '{name}' also used by {path.name}")
            continue
        name_owners[name] = path
        loaded[name] = (path, data)

    if len(paths) >= 2:
        for message in _cross_file_couplers(loaded):
            # Attach to the file named at the start of the message when possible.
            attached = False
            for path in per_file:
                if message.startswith(path.name + ":"):
                    per_file[path].append(message)
                    attached = True
                    break
            if not attached and per_file:
                next(iter(per_file.values())).append(message)

    return per_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate-beadtrain",
        description="Validate .beadtrain TOML. Directories include *.beadtrain in that folder and one child level.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help=".beadtrain file(s) or directory of trains",
    )
    args = parser.parse_args(argv)

    files: list[Path] = []
    for raw in args.paths:
        found = iter_train_files(raw)
        if not found:
            print(f"not found: {raw}", file=sys.stderr)
            return 2
        files.extend(found)

    unique: list[Path] = []
    seen: set[Path] = set()
    for path in files:
        if path not in seen:
            seen.add(path)
            unique.append(path)

    results = validate_paths(unique)
    failed = False
    for path, errors in results.items():
        if errors:
            failed = True
            for error in errors:
                if error.startswith(path.name + ":"):
                    print(f"ERROR: {error}", file=sys.stderr)
                else:
                    print(f"ERROR: {path.name}: {error}", file=sys.stderr)
        else:
            print(f"OK: {path.name}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
