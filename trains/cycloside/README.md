# Cycloside generation trains

Canonical train plans for Cycloside live here. The actual work items live in:

`D:\GitHub\NewIdeas\Cycloside\.beads`

Do not create Cycloside issues in `NewIdeas\.beads`.

The two `.beadtrain.template` files in this directory are intentionally not live manifests yet. Cycloside's current `.beads` database is schema v26 while the installed `bd` expects v53, and Beads is correctly blocking writes until the shared remote migration is reconciled.

Once the Cycloside store is writable:

1. create the cars in `Cycloside\.beads`;
2. replace each `__PENDING_*__` token with the real `bd` issue ID;
3. rename `.beadtrain.template` to `.beadtrain`;
4. validate both files together so cross-train couplers resolve;
5. keep Windows 3.1 as the shared older-generation foundation and Windows 98 as an inheriting generation.

Current implementation frontier for Classic 9x is draft NewIdeas PR #407 at `8b1e884533fcd051de84de741d14c9d872164b20`.