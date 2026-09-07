# Classroom examples

Fictional `bead` ids (`classroom-demo-*`) are **not** live `bd` issues. They exist so the validator and coupler docs have a green sample pair.

- `example_primary_demo.beadtrain` — primary + `[[couplers]]`
- `example_secondary_demo.beadtrain` — secondary unlocked `after` primary `capstone`

```bash
python scripts/validate_beadtrain.py examples/
python scripts/beadtrain.py list --dir examples
python scripts/beadtrain.py couplers --dir examples
```
