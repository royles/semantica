# CAI demo fixtures

| File | Purpose |
|------|---------|
| `ai_capital_graph.json` | Default Knowledge Explorer graph (loaded on startup unless `SEMANTICA_GRAPH_PATH` overrides) |
| `demo_resources.json` | Generated bibliography of primary sources (`GET /api/demo/resources`) |
| `seed_ai_capital_graph.py` | Regenerate graph + manifest: `python deploy/cloudera/inference-app/fixtures/seed_ai_capital_graph.py` |

Each node/edge uses structured attributes:

| Attribute | Role |
|-----------|------|
| **`name`** / **`title`** | Short graph label (also stored as `content` for the canvas) |
| **`description`** | Long-form text (no URLs embedded) |
| **`references`** | List of citation URLs; Explorer shows a **References** panel |
| **`source_url`** | Primary URL (legacy provenance field, first reference) |
