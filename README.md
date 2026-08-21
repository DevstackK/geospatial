# Geospatial A2A Data Cleansing Agent

This project is a geospatial data cleansing system built around an official
A2A-compatible agent interface. It helps inspect, clean, validate, and audit
messy geospatial datasets such as GeoJSON, GeoPackage, Shapefile, and FlatGeoBuf
files.

The core idea is simple: specialized agents analyze different parts of the data,
propose cleaning rules, deterministic GIS code applies the safe operations, and
the system writes an audit trail explaining what happened.

It can run in four ways:

- a Python CLI for local cleaning jobs
- a browser app for PostGIS to Oracle pipeline configuration
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

For large PostGIS-backed cleaning jobs:

```bash
pip install -e ".[postgis]"
```

For Oracle write-back:

```bash
pip install -e ".[oracle]"
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

For a PostGIS SQL-plan dry-run:

```bash
a2a-geo-clean config/postgis.example.yaml --run-mode dry_run
```

For an Oracle write-back dry-run:

```bash
a2a-geo-clean config/oracle-output.example.yaml --run-mode dry_run
```

## Frontend

Open `web/index.html` in a browser, or serve the `web/` folder locally. The
frontend is a static app, so it does not need Node, a database connection, or a
backend server just to run in the browser.

The app has two modes.

### Pipeline Mode

Pipeline mode is the production setup screen for a PostGIS to Oracle cleansing
job. It helps you build the YAML config that the Python backend will run.

Use it to enter:

- PostGIS source table, geometry column, ID column, and target CRS
- required columns and string-trim columns
- audit table and review confidence threshold
- Oracle staging table, target table, source/export table, key columns, and
  output columns

The app generates a YAML config. Download it as `oracle-output.yaml` and place
it under `config/`, then run a dry-run first:

```bash
a2a-geo-clean config/oracle-output.yaml --run-mode dry_run
```

Dry-run mode does not change PostGIS or Oracle. It writes an audit report and
SQL plan showing what would happen.

After reviewing the SQL plan and audit, run execute mode:

```bash
a2a-geo-clean config/oracle-output.yaml --run-mode execute
```

Execute mode needs database credentials in the environment:

```bash
export DATABASE_URL="postgresql://user:password@host:5432/geodata"
export ORACLE_DSN="host:1521/service"
export ORACLE_USER="gis_user"
export ORACLE_PASSWORD="your_password"
```

The intended production pattern is:

```text
PostGIS table
  -> generate cleansing SQL
  -> audit changed/flagged records
  -> stage clean rows for Oracle
  -> MERGE reviewed rows into Oracle target table
```

### GeoJSON Inspect Mode

GeoJSON inspect mode is for small samples and local review. It supports GeoJSON
FeatureCollections in the browser and shows:

- detected data issues
- affected feature/value counts
- recommended fixes
- proposed cleaning rules
- a spatial preview
- downloadable `audit.json`
- downloadable cleaned GeoJSON

Use the Python CLI for GeoPackage, Shapefile, FlatGeoBuf, large files, PostGIS,
and Oracle execution.

During local development you can serve the app with:

```bash
cd web
python3 -m http.server 8765 --bind 0.0.0.0
```

Then open:

```text
http://localhost:8765/
```

## Deploy The Frontend

The browser app is static. Deploying it does not deploy the Python CLI, A2A
server, PostGIS executor, or Oracle connector. It deploys the UI that generates
the config and lets users inspect small GeoJSON files.

This repo includes `web/vercel.json`, so the simplest deployment is Vercel.
From the project root:

```bash
vercel --prod web
```

If the Vercel CLI asks to link the project, choose the existing project if one
already exists, or create a new one. The deployment output will include the
public URL.

You can also deploy `web/` to any static host, including Netlify, Cloudflare
Pages, GitHub Pages, or an internal web server. The required files are:

```text
web/index.html
web/styles.css
web/app.js
web/vercel.json
```

For the backend execution path, deploy or run the Python service separately:

```bash
pip install -e ".[a2a,postgis,oracle]"
a2a-geo-agent --host 0.0.0.0 --port 8787
```

The frontend currently generates configs and local downloads. It does not send
credentials or run database jobs from the browser.

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

## Oracle Write-Back Connector

The project includes an Oracle output connector for returning approved cleaned
data to an Oracle source system. It is intentionally conservative: the default
pattern is to write to a staging table first, validate, then merge into the
source table.

Recommended flow:

```text
Oracle source
  -> extract/profile
  -> cleanse in PostGIS or file workflow
  -> validate and audit
  -> Oracle staging table
  -> reviewed MERGE into Oracle target table
```

Example output config:

```yaml
output:
  sink: oracle
  mode: merge
  stage_table: GIS.PARCELS_CLEANED_STAGE
  target_table: GIS.PARCELS
  source_table: PUBLIC.PARCELS_CLEANED_EXPORT
  key_columns:
    - PARCEL_ID
  columns:
    - PARCEL_ID
    - OWNER_NAME
    - LAND_USE
    - GEOM
  geometry:
    column: GEOM
    source_format: wkt
    srid: 4326
```

In `dry_run` mode, the connector writes an Oracle SQL plan into `audit.json`.
This includes staging-table creation, cleaned-row load SQL, and an Oracle
`MERGE` statement.

In `execute` mode, install the Oracle extra and provide credentials:

```bash
pip install -e ".[oracle]"
export ORACLE_DSN="host:1521/service"
export ORACLE_USER="gis_user"
export ORACLE_PASSWORD="your_password"
a2a-geo-clean config/oracle-output.example.yaml --run-mode execute
```

Geometry write-back depends on how Oracle stores spatial data. The connector can
generate Oracle geometry expressions for:

- `wkt` via `SDO_UTIL.FROM_WKTGEOMETRY(...)`
- `wkb` via `SDO_UTIL.FROM_WKBGEOMETRY(...)`
- existing `sdo_geometry`
- longitude/latitude columns via `SDO_GEOMETRY(...)`

Do not overwrite Oracle source tables blindly. Use staging tables, compare row
counts and changed fields, and only run merge mode after validation.

## Scaling To 8M Records

Use this framework as the control plane. For large datasets, use PostGIS as the
execution plane. Agents should exchange summaries and rule proposals, not raw
record payloads.

The project includes a PostGIS execution mode for this:

```yaml
dataset:
  source: postgis
  table: public.parcels
  geometry_column: geom
  id_column: parcel_id
  target_crs: EPSG:4326

execution:
  engine: postgis
  audit_table: public.cleaning_audit
  batch_size: 100000
```

In `dry_run` mode, the agent generates an auditable SQL plan without touching
the database. In `execute` mode, it runs the generated SQL against
`execution.database_url`, `DATABASE_URL`, or `POSTGIS_DATABASE_URL`.

Example:

```bash
export POSTGIS_DATABASE_URL="postgresql://user:password@localhost:5432/geodata"
a2a-geo-clean config/postgis.example.yaml --run-mode execute
```

The generated PostGIS plan uses database-native operations such as:

- `ST_Transform` for CRS normalization
- `ST_MakeValid` for invalid geometries
- `DELETE ... WHERE ST_IsEmpty(...)` for empty geometries
- SQL `btrim(...)` for string cleanup
- `CASE` expressions for category normalization
- `GROUP BY ... HAVING COUNT(*) > 1` for duplicate flags
- audit-table inserts for counts and review evidence

For 8M records, keep the browser out of the execution path. Use the browser only
for small samples and previews. Use the A2A server or CLI to plan the cleansing
job, and let PostGIS apply rules close to the data.
