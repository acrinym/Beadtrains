# BeadTrain V3 engine

| Tool | Purpose |
| --- | --- |
| `engine.py` | Append-only state replay, ready-set, capability matching, leases, packets |
| `scripts/beadtrain_v3.py` | CLI: init, status, ready, claim, start, packet, complete, … |

```bash
python scripts/validate_beadtrain.py examples/example_primary_demo.beadtrain
python scripts/beadtrain_v3.py init examples/example_primary_demo.beadtrain --actor you
python scripts/beadtrain_v3.py ready examples/example_primary_demo.beadtrain
```

```bash
python -m pytest tests/test_beadtrain_v3.py -v --timeout=120
```
