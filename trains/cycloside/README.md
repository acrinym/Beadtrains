# Cycloside generation trains

Canonical Cycloside train manifests live here. The actual Beads work items live in:

`D:\GitHub\NewIdeas\Cycloside\.beads`

Do not create Cycloside issues in `NewIdeas\.beads`.

Cycloside's Beads database was migrated from schema v26 to v53 on 2026-09-16 using this clone as the designated migrator, then pushed successfully to the Git-backed Dolt remote.

Live generation epics:

- Windows 3.1: `Cycloside-0j7`
- Windows 98: `Cycloside-wnk`

The manifests in this directory contain only real Cycloside bead IDs and must be validated together so the cross-generation couplers resolve. Windows 3.1 is the shared older-generation foundation; Windows 98 inherits that foundation and adds its own native personalization formats and surfaces.

Current Classic 9x implementation frontier is draft NewIdeas PR #407 at `8b1e884533fcd051de84de741d14c9d872164b20`.