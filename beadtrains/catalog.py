"""Load v1.3 .beadtrain files. Does not talk to bd."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from beadtrains.validate import _load, iter_train_files


@dataclass(frozen=True)
class Coupler:
    id: str
    from_train: str
    from_car: str
    to_train: str
    to_car: str
    mode: str
    join_main_at: str | None = None
    note: str = ""


@dataclass(frozen=True)
class Car:
    id: str
    bead: str
    title: str
    parallel_start: bool
    depends_on: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Train:
    path: Path
    name: str
    title: str
    description: str
    created: str
    status: str
    cars: tuple[Car, ...]
    couplers: tuple[Coupler, ...]
    one_liner: str = ""
    watch: str = ""
    couples_with: tuple[str, ...] = ()
    prior_car: str = ""

    def car_by_id(self) -> dict[str, Car]:
        return {car.id: car for car in self.cars}


def _coupler_from(raw: dict[str, Any]) -> Coupler:
    join = raw.get("join_main_at")
    return Coupler(
        id=str(raw.get("id") or ""),
        from_train=str(raw.get("from_train") or ""),
        from_car=str(raw.get("from_car") or ""),
        to_train=str(raw.get("to_train") or ""),
        to_car=str(raw.get("to_car") or ""),
        mode=str(raw.get("mode") or ""),
        join_main_at=str(join) if join else None,
        note=str(raw.get("note") or ""),
    )


def _car_from(raw: dict[str, Any]) -> Car:
    deps = raw.get("depends_on") or []
    if not isinstance(deps, list):
        deps = []
    return Car(
        id=str(raw.get("id") or ""),
        bead=str(raw.get("bead") or ""),
        title=str(raw.get("title") or ""),
        parallel_start=bool(raw.get("parallel_start")),
        depends_on=tuple(str(item) for item in deps),
        summary=str(raw.get("summary") or ""),
    )


def train_from_data(path: Path, data: dict[str, Any]) -> Train:
    section = data.get("train") or {}
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    cars_raw = data.get("cars") or []
    couplers_raw = data.get("couplers") or []
    couples = meta.get("couples_with") or []
    if not isinstance(couples, list):
        couples = []
    cars = tuple(_car_from(item) for item in cars_raw if isinstance(item, dict))
    couplers = tuple(_coupler_from(item) for item in couplers_raw if isinstance(item, dict))
    return Train(
        path=path,
        name=str(section.get("name") or path.stem),
        title=str(section.get("title") or ""),
        description=str(section.get("description") or ""),
        created=str(section.get("created") or ""),
        status=str(section.get("status") or ""),
        cars=cars,
        couplers=couplers,
        one_liner=str(meta.get("one_liner") or ""),
        watch=str(meta.get("watch") or ""),
        couples_with=tuple(str(item) for item in couples),
        prior_car=str(meta.get("prior_car") or ""),
    )


def load_train(path: Path) -> Train:
    return train_from_data(path.resolve(), _load(path))


def default_train_dir(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit
    beads = Path.cwd() / ".beads"
    if beads.is_dir():
        return beads
    return Path.cwd()


def load_trains(root: Path) -> list[Train]:
    trains: list[Train] = []
    for path in iter_train_files(root):
        trains.append(load_train(path))
    return trains


def index_trains(trains: list[Train]) -> dict[str, Train]:
    return {train.name: train for train in trains}


def all_couplers(trains: list[Train]) -> list[tuple[Train, Coupler]]:
    rows: list[tuple[Train, Coupler]] = []
    seen: set[str] = set()
    for train in trains:
        for coupler in train.couplers:
            key = (
                f"{coupler.id}|{coupler.from_train}|{coupler.from_car}|"
                f"{coupler.to_train}|{coupler.to_car}|{coupler.mode}"
            )
            if key in seen:
                continue
            seen.add(key)
            rows.append((train, coupler))
    return rows
