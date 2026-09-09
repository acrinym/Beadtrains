from __future__ import annotations

from pathlib import Path

from beadtrains.validate import validate


def _write_train(path: Path, name: str) -> None:
    path.write_text(
        f'''[train]\nname = "{name}"\ntitle = "Name policy"\ndescription = "Regression fixture"\ncreated = "2026-09-08"\nstatus = "planned"\n\n[[cars]]\nid = "start"\nbead = "demo-name-policy"\ntitle = "Start"\nparallel_start = true\ndepends_on = []\nsummary = "fixture"\n''',
        encoding="utf-8",
    )


def test_hyphenated_train_name_is_rejected_even_when_filename_matches(tmp_path: Path) -> None:
    path = tmp_path / "bad-name.beadtrain"
    _write_train(path, "bad-name")
    errors = validate(path)
    assert "[train].name must be a snake_case slug" in errors
    assert not any("filename stem" in error for error in errors)


def test_snake_case_train_name_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "good_name_2.beadtrain"
    _write_train(path, "good_name_2")
    assert validate(path) == []
