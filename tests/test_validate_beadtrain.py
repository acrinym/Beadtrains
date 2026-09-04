from __future__ import annotations

from pathlib import Path

from beadtrains.validate import iter_train_files, main, validate, validate_paths

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_classroom_pair_is_ok_as_a_set() -> None:
    files = iter_train_files(EXAMPLES)
    assert len(files) == 2
    results = validate_paths(files)
    assert all(not errs for errs in results.values())


def test_single_primary_does_not_require_peer() -> None:
    path = EXAMPLES / "example_primary_demo.beadtrain"
    assert validate(path) == []
    results = validate_paths([path])
    assert results[path] == []


def test_cross_file_rejects_missing_to_car(tmp_path: Path) -> None:
    primary = tmp_path / "alpha.beadtrain"
    secondary = tmp_path / "beta.beadtrain"
    primary.write_text(
        """
[train]
name = "alpha"
title = "A"
description = "A"
created = "2026-09-04"
status = "planned"

[[cars]]
id = "done"
bead = "demo-1"
title = "Done"
parallel_start = true
depends_on = []
summary = "x"

[meta]
couples_with = ["beta"]

[[couplers]]
id = "join"
from_train = "alpha"
from_car = "done"
to_train = "beta"
to_car = "missing"
mode = "after"
""",
        encoding="utf-8",
    )
    secondary.write_text(
        """
[train]
name = "beta"
title = "B"
description = "B"
created = "2026-09-04"
status = "planned"

[[cars]]
id = "start"
bead = "demo-2"
title = "Start"
parallel_start = true
depends_on = []
summary = "x"
""",
        encoding="utf-8",
    )
    results = validate_paths([primary, secondary])
    joined = " ".join(results[primary])
    assert "to_car 'missing' not in train beta" in joined


def test_cli_directory_exit_zero() -> None:
    assert main([str(EXAMPLES)]) == 0


def test_cli_missing_path() -> None:
    assert main(["no-such-train.beadtrain"]) == 2
