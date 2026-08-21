# Geospatial A2A Data Cleaning Framework

This project is a starter framework for an agent-to-agent geospatial data
cleaning workflow. Agents exchange typed task messages, propose deterministic
cleaning rules, execute GIS operations, validate results, and write an audit
report.

The design is intentionally conservative:

- agents reason over metadata, samples, profiles, and validation reports
- deterministic code applies cleaning operations
- every proposed and executed rule is recorded
- large datasets can be processed through file batches or PostGIS later

## Workflow

```text
Input dataset
  -> IntakeAgent
  -> SchemaAgent
  -> CRSAgent
  -> GeometryAgent
  -> AttributeAgent
  -> ValidationAgent
  -> ReportAgent
```

## Install

For orchestration-only development:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

For real geospatial file processing:

```bash
pip install -e ".[geo]"
```

## Run

Drop a sample geospatial file into `data/uploads`, then run:

```bash
a2a-geo-clean
```

The CLI picks the newest supported upload automatically and writes outputs to
`runs/<filename>-cleaning`.

You can also pass a file explicitly:

```bash
a2a-geo-clean --input data/uploads/sample.geojson
```

The optional config argument still works:

```bash
a2a-geo-clean config/example.yaml --input data/uploads/sample.geojson
```

Supported input extensions are GeoJSON, JSON, GeoPackage, Shapefile, and
FlatGeoBuf.

## Frontend

Open `web/index.html` in a browser to inspect sample GeoJSON files without a
server. The dashboard shows:

- detected data issues
- affected feature/value counts
- recommended fixes
- proposed cleaning rules
- a spatial preview
- downloadable `audit.json`
- downloadable cleaned GeoJSON

The browser dashboard currently supports GeoJSON FeatureCollections. Use the
Python CLI for GeoPackage, Shapefile, and FlatGeoBuf execution.

Deploy the frontend to Vercel from the project root with:

```bash
vercel --prod web
```

## Optional Claude Planner

The backend includes an optional Claude rule-planning stage. It is disabled by
default, and it never applies dataset edits directly. It reviews the
deterministic agent summaries and returns recommendations for the audit report.

Enable it in config:

```yaml
llm:
  enabled: true
  model: claude-sonnet-4-20250514
  max_tokens: 1200
```

Then run with an API key:

```bash
export ANTHROPIC_API_KEY="your_api_key"
a2a-geo-clean --input data/uploads/sample.geojson
```

The Claude stage is for explanation and planning. GeoPandas/Shapely still perform
the actual cleaning operations.

## Official A2A Server

The project can also run as an official A2A JSON-RPC agent using Google's A2A
Python SDK package.

Install the A2A server extra:

```bash
pip install -e ".[a2a]"
```

Start the agent:

```bash
a2a-geo-agent --host 0.0.0.0 --port 8787
```

The public Agent Card is available at:

```text
http://localhost:8787/.well-known/agent-card.json
```

The JSON-RPC endpoint is:

```text
http://localhost:8787/
```

Example A2A `message/send` request:

```bash
curl -X POST http://localhost:8787/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "clean-1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "messageId": "msg-1",
        "parts": [
          {
            "kind": "text",
            "text": "{\"input\":\"examples/sample-issues.geojson\",\"run_mode\":\"dry_run\"}"
          }
        ]
      },
      "configuration": { "returnImmediately": false }
    }
  }'
```

The agent returns a completed A2A task with `audit.json` and, when execution
writes one, a cleaned GeoJSON artifact.

## Current Operations

The framework includes rule contracts for:

- CRS normalization
- invalid geometry repair
- empty geometry filtering
- duplicate feature detection
- string trimming
- category normalization
- required-field checks
- bounds checks

The local executor implements the operations when GeoPandas/Shapely are
available. Without those dependencies, the workflow still validates configs and
writes a dry-run audit.

## Scaling To 8M Records

Use this framework as the control plane. For large datasets, use PostGIS,
DuckDB Spatial, or partitioned GeoParquet as the execution plane. Agents should
exchange summaries and rule proposals, not raw record payloads.
