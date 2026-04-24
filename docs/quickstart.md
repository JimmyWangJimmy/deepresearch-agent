# DeepResearch Agent Quickstart

This guide verifies a local or container install and produces a customer-shareable delivery bundle.

## 1. Install

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

Optional OpenAI-backed web research:

```bash
export OPENAI_API_KEY=...
export OPENAI_RESEARCH_MODEL=gpt-5.2
```

## 2. Diagnose

```bash
dra doctor --json
dra providers --json
dra gate --json
```

Expected:

- `dra doctor` should show a writable artifact directory.
- `dra providers` should include `attached`, `web_fetch`, `wikipedia_search`, `arxiv_search`, and `openai_web_research`.
- `dra gate` should pass before customer demos.

## 3. Run A File Intelligence Demo

```bash
mkdir -p demo
cat > demo/funding.txt <<'EOF'
2026年4月20日，星海机器人公司完成2亿元人民币融资，远望资本领投。
2026年4月22日，远航智造发布新型人形机器人平台。
EOF

dra run "整理机器人赛道融资与产品事件，输出客户可读简报" \
  --file demo/funding.txt \
  --artifacts-dir demo/artifacts \
  --json
```

Open the generated run directory:

```bash
RUN_ID=<paste_run_id>
ls demo/artifacts/$RUN_ID
dra quality $RUN_ID --artifacts-dir demo/artifacts
dra export $RUN_ID --artifacts-dir demo/artifacts --format bundle --output demo/delivery_bundle.zip
```

The run should produce:

- `run_summary.json`
- `quality.json`
- `research_report.pdf`
- `research_report.html`
- `research_workbook.xlsx`
- `delivery_bundle.zip`
- `source_scores.svg`
- `event_timeline.svg`
- `entities.csv`
- `events.csv`

For a packaged local demo, run:

```bash
bash scripts/run_demo.sh
open demo/index.html
```

## 4. Run A Provider Demo

Offline/public-source demo:

```bash
dra run "robotics industry overview" \
  --provider wikipedia_search \
  --artifacts-dir demo/provider-artifacts \
  --json
```

OpenAI-backed demo:

```bash
dra run "机器人行业融资与产品发布研究" \
  --provider openai_web_research \
  --artifacts-dir demo/openai-artifacts \
  --json
```

If `OPENAI_API_KEY` is missing, the CLI should return a clear configuration error.

## 5. Run The API

```bash
uv run uvicorn research_operator.api:app --host 0.0.0.0 --port 8000
```

In another shell:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/providers
```

Create a run:

```bash
curl -X POST http://localhost:8000/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "task": "API demo research brief",
    "files": ["demo/funding.txt"],
    "artifacts_dir": "demo/api-artifacts"
  }'
```

Then inspect and download:

```bash
RUN_ID=<paste_run_id>
curl "http://localhost:8000/doctor?artifacts_dir=demo/api-artifacts"
curl "http://localhost:8000/runs?artifacts_dir=demo/api-artifacts&task_type=file_intelligence&limit=1"
curl "http://localhost:8000/runs?artifacts_dir=demo/api-artifacts&task_contains=%E6%96%87%E4%BB%B6"
curl "http://localhost:8000/runs/summary?artifacts_dir=demo/api-artifacts"
curl "http://localhost:8000/runs?artifacts_dir=demo/api-artifacts&has_warnings=true"
curl "http://localhost:8000/runs?artifacts_dir=demo/api-artifacts&min_quality_score=0.75"
curl "http://localhost:8000/runs?artifacts_dir=demo/api-artifacts&min_average_evidence_score=0.75"
curl "http://localhost:8000/runs?artifacts_dir=demo/api-artifacts&sort_by=quality_desc"
curl "http://localhost:8000/runs?artifacts_dir=demo/api-artifacts&max_source_count=1"
curl "http://localhost:8000/runs?artifacts_dir=demo/api-artifacts&min_event_count=1"
curl "http://localhost:8000/runs?artifacts_dir=demo/api-artifacts&min_entity_count=1"
curl "http://localhost:8000/runs/$RUN_ID/quality?artifacts_dir=demo/api-artifacts"
curl "http://localhost:8000/runs/$RUN_ID/deliverables?artifacts_dir=demo/api-artifacts"
curl "http://localhost:8000/runs/$RUN_ID/delivery-manifest?artifacts_dir=demo/api-artifacts"
curl "http://localhost:8000/runs/$RUN_ID/verify?artifacts_dir=demo/api-artifacts"
curl -o demo/api_delivery_bundle.zip \
  "http://localhost:8000/runs/$RUN_ID/deliverables/delivery_bundle?artifacts_dir=demo/api-artifacts"
```

Create and run a watch through the API:

```bash
curl -X POST http://localhost:8000/watches \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "API Watch",
    "task": "监控机器人赛道变化",
    "files": ["demo/funding.txt"],
    "watches_dir": "demo/api-watches"
  }'

WATCH_ID=<paste_watch_id>
curl -X POST "http://localhost:8000/watches/$WATCH_ID/run" \
  -H 'Content-Type: application/json' \
  -d '{
    "artifacts_dir": "demo/api-watch-artifacts",
    "watches_dir": "demo/api-watches",
    "force": true
  }'

curl "http://localhost:8000/watches/$WATCH_ID?watches_dir=demo/api-watches"
curl "http://localhost:8000/watches/$WATCH_ID/delivery-manifest?watches_dir=demo/api-watches"
curl "http://localhost:8000/watches?watches_dir=demo/api-watches&enabled=true"
curl -X PATCH "http://localhost:8000/watches/$WATCH_ID" \
  -H 'Content-Type: application/json' \
  -d '{
    "enabled": false,
    "watches_dir": "demo/api-watches"
  }'
curl -X DELETE "http://localhost:8000/watches/$WATCH_ID?watches_dir=demo/api-watches"
```

## 6. Run With Docker

```bash
docker build -t deepresearch-agent .
docker run --rm -p 8000:8000 -e OPENAI_API_KEY=$OPENAI_API_KEY deepresearch-agent
```

Verify:

```bash
curl http://localhost:8000/health
```

## 7. Acceptance Criteria

A demo is acceptable when:

- `dra gate --json` returns `ready: true`.
- The customer receives a `delivery_bundle.zip`.
- The bundle contains PDF, HTML, XLSX, CSV, SVG, manifest, summary, quality, and source ledger files.
- `quality.json` exists and has a non-zero score.
- Sources and evidence are visible in `source_ledger.json` and the report.
