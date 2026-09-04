from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import sys

import pytest

V3 = Path(__file__).resolve().parents[1] / "v3"
sys.path.insert(0, str(V3))

from engine import (  # noqa: E402
    BeadTrainError,
    append_event,
    execution_packet,
    load_train,
    make_event,
    materialize,
    read_events,
    ready_cars,
    state_path_for,
    utc_now,
)

TRAIN = '''
[train]
name = "v3_test"
title = "V3 test"
description = "State engine test"
created = "2026-07-19"
status = "planned"

[protocol]
version = "3.0"
repository = "acrinym/Beadtrains"
branch_policy = "one-pr-per-train"

[[cars]]
id = "foundation"
bead = "PV-foundation"
title = "Foundation"
parallel_start = true
depends_on = []
summary = "Build foundation."
capabilities = ["python"]
evidence_required = ["commit", "tests"]

[[cars]]
id = "capstone"
bead = "PV-capstone"
title = "Capstone"
parallel_start = false
depends_on = ["foundation"]
summary = "Validate everything."
'''


def write_train(tmp_path: Path) -> Path:
    path = tmp_path / "v3_test.beadtrain"
    path.write_text(TRAIN, encoding="utf-8")
    return path


def test_v13_compatible_definition_loads(tmp_path: Path) -> None:
    path = write_train(tmp_path)
    train = load_train(path)
    assert train.name == "v3_test"
    assert train.cars[0].capabilities == ("python",)


def test_ready_set_honors_capabilities_and_dependencies(tmp_path: Path) -> None:
    train = load_train(write_train(tmp_path))
    snapshot = materialize(train, [])
    assert ready_cars(snapshot) == []
    assert [car.id for car in ready_cars(snapshot, ["python"])] == ["foundation"]


def test_claim_completion_unlocks_capstone(tmp_path: Path) -> None:
    train = load_train(write_train(tmp_path))
    state_path = state_path_for(train.path)
    claim = make_event(train, "car.claimed", car="foundation", actor="codex", claim="c1", lease_minutes=45)
    append_event(state_path, claim)
    append_event(state_path, make_event(
        train, "car.completed", car="foundation", actor="codex", claim="c1",
        fields={"commit": "abc", "tests": "passed"},
    ))
    snapshot = materialize(train, read_events(state_path))
    assert snapshot.states["foundation"].state == "complete"
    assert [car.id for car in ready_cars(snapshot)] == ["capstone"]


def test_expired_claim_becomes_abandoned_and_retryable(tmp_path: Path) -> None:
    train = load_train(write_train(tmp_path))
    event = make_event(train, "car.claimed", car="foundation", actor="cursor", claim="old", lease_minutes=1)
    snapshot = materialize(train, [event], now=utc_now() + timedelta(minutes=2))
    assert snapshot.states["foundation"].state == "abandoned"
    assert [car.id for car in ready_cars(snapshot, ["python"])] == ["foundation"]


def test_packet_is_self_contained(tmp_path: Path) -> None:
    train = load_train(write_train(tmp_path))
    packet = execution_packet(materialize(train, []), train.cars[0], "agent", "claim-1")
    assert "BEADTRAIN PACKET 3.0" in packet
    assert "acrinym/Beadtrains" in packet
    assert "commit" in packet
    assert "tests" in packet


def test_corrupt_state_is_rejected(tmp_path: Path) -> None:
    state = tmp_path / "bad.beadstate"
    state.write_text("EVENT x\ntype=car.claimed\n", encoding="utf-8")
    with pytest.raises(BeadTrainError):
        read_events(state)
