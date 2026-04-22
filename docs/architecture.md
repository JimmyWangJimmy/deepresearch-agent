# Architecture

## Product thesis

DeepResearch Agent is not another chat UI for deep research. It is a `research operating system` with a CLI-first runtime and artifact-first delivery model.

## Runtime flow

```text
user task
  -> planner
  -> provider routing
  -> collection
  -> processing
  -> analysis
  -> artifact rendering
  -> inspect / export / downstream workflow
```

## Core layers

### 1. Entry surfaces

- CLI
- Web
- API

### 2. Agent runtime

- Task interpretation
- Planning
- Execution state
- Retry and failure accounting

### 3. Provider layer

- First-party web crawling
- File ingestion
- External deep research providers
- Private enterprise data connectors

### 4. Processing layer

- Cleaning
- Extraction
- Deduplication
- Normalization
- Entity resolution

### 5. Knowledge layer

- Entity registry
- Event timeline
- Knowledge graph
- Cross-run memory

### 6. Artifact layer

- Markdown report
- HTML report
- JSON payloads
- Tables and charts
- Graph payloads

## V1 boundaries

Current repository covers:

- CLI entrypoint
- Deterministic planner
- Run manifest generation
- Markdown and JSON artifacts
- Inspect command

The next implementation increments should add:

1. Real provider adapters
2. File ingestion
3. Source ledger with citations
4. HTML and XLSX exports
5. Monitoring jobs

