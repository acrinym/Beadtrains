from __future__ import annotations

import json
from pathlib import Path

from beadtrains.catalog import load_trains
from beadtrains.cli import main
from beadtrains.ready import load_bead_status_jsonl, ready_views
from beadtrains.templates import write_template
from beadtrains.validate import validate, validate_paths

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_ready_classroom_without_issues_is_not_ready() -> None:
    trains = load_trains(EXAMPLES)
    views = ready_views(trains, None)
    assert views
    assert not any(view.ready for view in views)


def test_ready_after_primary_capstone_unlocks_secondary(tmp_path: Path) -> None:
    trains = load_trains(EXAMPLES)
    issues = tmp_path / "issues.jsonl"
    rows = [
        {"id": "classroom-demo-1", "status": "closed"},
        {"id": "classroom-demo-2", "status": "closed"},
        {"id": "classroom-demo-3", "status": "open"},
    ]
    issues.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    status = load_bead_status_jsonl(issues)
    views = ready_views(trains, status)
    ready = {(view.train, view.car.id) for view in views if view.ready}
    assert ("example_secondary_demo", "start") in ready
    assert ("example_primary_demo", "build") not in ready
    assert ("example_primary_demo", "capstone") not in ready


def test_init_capability_validates(tmp_path: Path) -> None:
    written = write_template(tmp_path, "demo_cap", "capability", bead_prefix="demo-x")
    assert len(written) == 1
    assert validate(written[0]) == []


def test_init_coupled_pair_validates(tmp_path: Path) -> None:
    written = write_template(
        tmp_path,
        "demo_pri",
        "coupled",
        bead_prefix="demo-p",
        secondary_name="demo_sec",
    )
    assert len(written) == 2
    results = validate_paths(written)
    assert all(not errs for errs in results.values())


def test_cli_list_examples() -> None:
    assert main(["list", "--dir", str(EXAMPLES)]) == 0


def test_cli_couplers_examples() -> None:
    assert main(["couplers", "--dir", str(EXAMPLES)]) == 0


def test_cli_init_then_validate(tmp_path: Path) -> None:
    assert (
        main(
            [
                "init",
                "cli_cap",
                "--template",
                "capability",
                "--dir",
                str(tmp_path),
                "--bead-prefix",
                "cli-x",
            ]
        )
        == 0
    )
    assert main(["validate", str(tmp_path / "cli_cap.beadtrain")]) == 0
