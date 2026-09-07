"""Starter .beadtrain files. Bead ids are placeholders until `bd create`."""

from __future__ import annotations

from datetime import date
from pathlib import Path

TEMPLATES = ("capability", "audit_then_build", "coupled")


def _header(name: str, title: str, description: str, created: str) -> str:
    return f'''[train]
name        = "{name}"
title       = "{title}"
description = """
{description}
"""
created     = "{created}"
status      = "planned"
'''


def render_capability(name: str, *, created: str, bead_prefix: str) -> str:
    p = bead_prefix
    return (
        _header(
            name,
            "Capability train",
            "One capability end-to-end: foundation, parallel work, capstone.",
            created,
        )
        + f'''
[[cars]]
id             = "foundation"
bead           = "{p}.1"
title          = "Foundation"
parallel_start = true
depends_on     = []
summary        = "Lock the contract and the files this train owns."

[[cars]]
id             = "build-a"
bead           = "{p}.2"
title          = "Build A"
parallel_start = true
depends_on     = ["foundation"]
summary        = "First parallel workstream after foundation."

[[cars]]
id             = "build-b"
bead           = "{p}.3"
title          = "Build B"
parallel_start = true
depends_on     = ["foundation"]
summary        = "Second parallel workstream after foundation."

[[cars]]
id             = "capstone"
bead           = "{p}.4"
title          = "Capstone"
parallel_start = false
depends_on     = ["build-a", "build-b"]
summary        = "Prove the whole capability. Host-repo quality gates."

[meta]
one_liner = "Ship one complete capability, not a slice."
'''
    )


def render_audit_then_build(name: str, *, created: str, bead_prefix: str) -> str:
    p = bead_prefix
    return (
        _header(
            name,
            "Audit then build",
            "Inventory first, then parallel drafts, then assemble.",
            created,
        )
        + f'''
[[cars]]
id             = "audit"
bead           = "{p}.1"
title          = "Audit"
parallel_start = true
depends_on     = []
summary        = "Inventory current state. Gap list. No implementation yet."

[[cars]]
id             = "map"
bead           = "{p}.2"
title          = "Map"
parallel_start = false
depends_on     = ["audit"]
summary        = "Map gaps onto cars. Fill real bd ids before running."

[[cars]]
id             = "draft-a"
bead           = "{p}.3"
title          = "Draft A"
parallel_start = true
depends_on     = ["map"]
summary        = "First draft stream."

[[cars]]
id             = "draft-b"
bead           = "{p}.4"
title          = "Draft B"
parallel_start = true
depends_on     = ["map"]
summary        = "Second draft stream."

[[cars]]
id             = "assemble"
bead           = "{p}.5"
title          = "Assemble"
parallel_start = false
depends_on     = ["draft-a", "draft-b"]
summary        = "Integrate drafts. Host-repo quality gates."

[[cars]]
id             = "capstone"
bead           = "{p}.6"
title          = "Capstone"
parallel_start = false
depends_on     = ["assemble"]
summary        = "Whole-arc proof."

[meta]
one_liner = "Audit, map, draft in parallel, assemble, prove."
'''
    )


def render_coupled_primary(name: str, secondary: str, *, created: str, bead_prefix: str) -> str:
    p = bead_prefix
    return (
        _header(
            name,
            "Coupled primary",
            f"Primary side. Unlocks `{secondary}` after capstone via coupler.",
            created,
        )
        + f'''
[[cars]]
id             = "build"
bead           = "{p}.1"
title          = "Build"
parallel_start = true
depends_on     = []
summary        = "Primary work."

[[cars]]
id             = "capstone"
bead           = "{p}.2"
title          = "Capstone"
parallel_start = false
depends_on     = ["build"]
summary        = "Primary complete. Coupler `after` this car."

[meta]
one_liner    = "Primary train; secondary starts after capstone."
couples_with = ["{secondary}"]

[[couplers]]
id         = "primary-to-secondary"
from_train = "{name}"
from_car   = "capstone"
to_train   = "{secondary}"
to_car     = "start"
mode       = "after"
note       = "Secondary may start only after primary capstone is closed in bd."
'''
    )


def render_coupled_secondary(name: str, primary: str, *, created: str, bead_prefix: str) -> str:
    p = bead_prefix
    return (
        _header(
            name,
            "Coupled secondary",
            f"Secondary side. `start` waits on `{primary}` capstone (`after`).",
            created,
        )
        + f'''
[[cars]]
id             = "start"
bead           = "{p}.1"
title          = "Start"
parallel_start = true
depends_on     = []
summary        = "First car after the coupler opens."

[[cars]]
id             = "capstone"
bead           = "{p}.2"
title          = "Capstone"
parallel_start = false
depends_on     = ["start"]
summary        = "Secondary complete."

[meta]
one_liner = "Secondary train gated by primary coupler."
'''
    )


def write_template(
    dest_dir: Path,
    name: str,
    template: str,
    *,
    bead_prefix: str,
    secondary_name: str | None = None,
) -> list[Path]:
    created = date.today().isoformat()
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    if template == "capability":
        path = dest_dir / f"{name}.beadtrain"
        path.write_text(render_capability(name, created=created, bead_prefix=bead_prefix), encoding="utf-8")
        written.append(path)
        return written
    if template == "audit_then_build":
        path = dest_dir / f"{name}.beadtrain"
        path.write_text(
            render_audit_then_build(name, created=created, bead_prefix=bead_prefix),
            encoding="utf-8",
        )
        written.append(path)
        return written
    if template == "coupled":
        peer = secondary_name or f"{name}_secondary"
        primary = dest_dir / f"{name}.beadtrain"
        secondary = dest_dir / f"{peer}.beadtrain"
        primary.write_text(
            render_coupled_primary(name, peer, created=created, bead_prefix=bead_prefix),
            encoding="utf-8",
        )
        written.append(primary)
        secondary.write_text(
            render_coupled_secondary(peer, name, created=created, bead_prefix=f"{bead_prefix}-b"),
            encoding="utf-8",
        )
        written.append(secondary)
        return written
    raise ValueError(f"unknown template {template!r}; choose one of {TEMPLATES}")
