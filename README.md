# DeepResearch Agent

`DeepResearch Agent` is an agent-native, CLI-first research operator for turning natural-language requests into reproducible research runs and exportable artifacts.

## Product position

This repository starts from a simple rule:

`task -> plan -> execution -> artifacts`

The product is designed to aggregate upstream research providers, run internal processing and analysis, and ship artifacts that teams can actually use.

## Current scope

Version `0.1.0` is the first deliverable scaffold. It includes:

- A `dra` CLI
- Deterministic task planning
- Explicit source intake from files and URLs
- Provider abstraction for attached files and live web fetch
- A run manifest and artifact system
- Markdown, HTML, JSON, and source-ledger outputs
- Structured entity and event extraction
- CSV exports for entities and events
- An inspect command for previous runs
- An export command for downstream delivery
- Watch definitions for recurring change detection

This is not the final product. It is the first market-ready foundation.

## Quick start

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

dra run "抓取最近30天中国机器人融资事件，输出摘要、表格和投资视角分析"
dra run "分析这个研究材料并生成专题简报" --file ./briefing.md
dra run "分析某网页并生成证据化报告" --url https://example.com
dra inspect <run_id>
dra runs
dra providers
dra export <run_id> --format html --output ./deliverables/report.html
dra export <run_id> --format events_csv --output ./deliverables/events.csv
dra watch create "OpenAI News" --task "监控OpenAI更新并生成摘要" --url https://openai.com/news/
dra watch run <watch_id>
dra watch run-all
```

Artifacts are written to `./artifacts/<run_id>/`.

## Planned product layers

1. `Provider layer`
   OpenAI Deep Research, Perplexity, Gemini, first-party crawling, file ingestion.
2. `Processing layer`
   Parsing, extraction, normalization, deduplication, enrichment.
3. `Knowledge layer`
   Entity graph, event graph, cross-run memory, weak-signal discovery.
4. `Artifact layer`
   Reports, tabular exports, graph payloads, dashboards, APIs.

## CLI usage

```bash
dra run "<task>"
dra run "<task>" --json
dra run "<task>" --artifacts-dir ./runs
dra inspect <run_id>
```

## Delivery standard

Every run must produce:

- An execution manifest
- A plan
- Findings
- A source ledger
- A human-readable report
- Machine-readable JSON
- Structured entities and events
- CSV tables for downstream analysis

## Current commands

```bash
dra run "<task>" [--file PATH] [--url URL]
dra inspect <run_id>
dra runs
dra providers
dra export <run_id> --format html|markdown|manifest|findings|sources|entities|entities_csv|events|events_csv
dra watch create "<name>" --task "<task>" [--file PATH] [--url URL]
dra watch run <watch_id>
dra watch run-all
dra watch list
```

That delivery contract is the base requirement for all future runtime integrations.
