# Geospatial A2A Data Cleansing Agent

This project is a geospatial data cleansing system built around an official
A2A-compatible agent interface. It helps inspect, clean, validate, and audit
messy geospatial datasets such as GeoJSON, GeoPackage, Shapefile, and FlatGeoBuf
files.

The core idea is simple: specialized agents analyze different parts of the data,
propose cleaning rules, deterministic GIS code applies the safe operations, and
the system writes an audit trail explaining what happened.

It can run in three ways:

- a Python CLI for local cleaning jobs
- a browser dashboard for quick GeoJSON inspection
- an official A2A JSON-RPC server so other agents or apps can call the cleaner

## What Problem It Solves

Geospatial datasets often fail because different issues are mixed together:

- missing required columns
- inconsistent category values such as `res`, `residential use`, and
  `residential`
- leading and trailing whitespace in attributes
- duplicate feature identifiers
- missing, empty, or invalid geometries
- wrong or unknown coordinate reference systems
- coordinates outside valid bounds
- unclear audit history after automated fixes

This project separates those concerns into focused agents, then records each
recommended and executed rule. That makes cleansing easier to debug, review, and
trust.

## How A2A Helps

A2A means agent-to-agent. In this project, the geospatial cleaner can be exposed
as an official A2A JSON-RPC agent with a public Agent Card at
`/.well-known/agent-card.json`.

That helps because another agent, workflow, or data platform can discover the
cleaner, send it a cleaning task, and receive structured task artifacts such as
`audit.json` and cleaned GeoJSON.

The A2A pattern also keeps the internal workflow clean:

- the schema agent handles required fields and column checks
- the CRS agent handles projection normalization
- the geometry agent handles empty, invalid, and out-of-bounds geometries
- the attribute agent handles text cleanup and category normalization
- the optional LLM planner explains risks and recommends review steps
- the validation and report agents produce the final audit

Agents propose and explain. Deterministic code executes. Validators check the
result. Risky changes stay visible for human review.

## Why This Helps Geospatial Cleansing

For small one-off files, a script may be enough. For production geospatial data,
cleansing usually needs repeatability and accountability. This project is useful
when you need to:

- standardize incoming datasets before loading them into PostGIS or a warehouse
- catch geometry and CRS problems before map rendering or spatial analysis
- produce an audit report for every cleaning run
- separate automatic fixes from issues that need review
- let another agent or app trigger cleansing through the official A2A protocol
- scale later by using this project as the control plane and PostGIS, DuckDB
  Spatial, or GeoParquet as the execution plane

The model or LLM is not trusted to directly edit millions of rows. It is used
for planning, explanation, and recommendations. The actual data operations stay
rule-based and testable.

## Workflow

```text
Input dataset
  -> IntakeAgent
  -> SchemaAgent
  -> CRSAgent
  -> GeometryAgent
  -> AttributeAgent
  -> LLMRulePlannerAgent
  -> ValidationAgent
  -> ReportAgent
```

The workflow output is an audit directory under `runs/`, usually containing:

- `audit.json`
- cleaned GeoJSON when execution mode and dependencies support writing it
- execution logs describing which rules were planned or applied

## Install

For orchestration-only development:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

For real geospatial file processing:

```bash
pip install -e ".[geo]"
```

For the official A2A server:

```bash
pip install -e ".[a2a]"
```

For development and tests:

```bash
pip install -e ".[a2a,dev]"
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

For a quick dry-run against the included sample:

```bash
a2a-geo-clean --input examples/sample-issues.geojson --run-mode dry_run
```

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

During local development you can serve the dashboard with:

```bash
cd web
python3 -m http.server 8765 --bind 0.0.0.0
```

Then open:

```text
http://localhost:8765/
```

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
Python SDK package. This is the best mode when another agent, orchestration
system, or external app needs to call the cleaner.

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

The A2A agent accepts either:

- a JSON object with an `input` path to a local dataset
- a JSON object with inline `geojson`
- optional `run_mode`, `config`, and `output_dir` fields

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

Example response artifacts:

- `audit.json`: the full cleaning report, accepted rules, agent summaries, and
  execution log
- `cleaned.geojson`: cleaned dataset output when available

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

## Recommended Use

Use the browser dashboard when you want to inspect a GeoJSON file quickly.

Use the CLI when you want a repeatable local cleansing job.

Use the A2A server when you want another agent, backend, or workflow engine to
trigger geospatial cleansing and consume structured artifacts.

For production, keep the same pattern:

- agents analyze and propose
- deterministic GIS code applies safe operations
- validation agents check the result
- humans review low-confidence or risky changes
- every run produces an audit report

## Scaling To 8M Records

Use this framework as the control plane. For large datasets, use PostGIS,
DuckDB Spatial, or partitioned GeoParquet as the execution plane. Agents should
exchange summaries and rule proposals, not raw record payloads.
