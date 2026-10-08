# CAI demo fixtures

| File | Purpose |
|------|---------|
| `ai_capital_graph.json` | Default Knowledge Explorer graph (loaded on startup unless `SEMANTICA_GRAPH_PATH` overrides) |
| `demo_resources.json` | Generated bibliography of primary sources (`GET /api/demo/resources`) |
| `seed_ai_capital_graph.py` | Regenerate graph + manifest: `python deploy/cloudera/inference-app/fixtures/seed_ai_capital_graph.py` |

Nodes and edges include **`source`** and **`source_url`** properties for the Explorer inspector, plus inline `Sources:` URLs in `content`.
