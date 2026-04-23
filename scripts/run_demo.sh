#!/usr/bin/env bash
set -euo pipefail

ARTIFACTS_DIR="${1:-demo/artifacts}"
TASK="${2:-整理机器人赛道融资、产品发布与合作事件，输出客户可读简报}"

mkdir -p "$ARTIFACTS_DIR" demo

RUN_JSON="$(uv run dra run "$TASK" \
  --file examples/robotics_funding.txt \
  --artifacts-dir "$ARTIFACTS_DIR" \
  --json)"

RUN_ID="$(uv run python -c 'import json,sys; print(json.load(sys.stdin)["run_id"])' <<< "$RUN_JSON")"

uv run dra quality "$RUN_ID" --artifacts-dir "$ARTIFACTS_DIR" > "demo/quality.json"
uv run dra export "$RUN_ID" --artifacts-dir "$ARTIFACTS_DIR" --format bundle --output "demo/delivery_bundle.zip" >/dev/null

RUN_DIR="$ARTIFACTS_DIR/$RUN_ID"
echo "$RUN_JSON" > "demo/run.json"
QUALITY_SCORE="$(uv run python -c 'import json; print(json.load(open("demo/quality.json"))["score"])')"
EVENT_COUNT="$(uv run python -c 'import json; print(len(json.load(open("demo/run.json"))["events"]))')"
ENTITY_COUNT="$(uv run python -c 'import json; print(len(json.load(open("demo/run.json"))["entities"]))')"

cat > "demo/index.html" <<EOF
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>DeepResearch Agent Demo</title>
    <style>
      :root { --bg: #f6f2e8; --card: #fffdf8; --ink: #141312; --muted: #665f55; --accent: #0f766e; --line: #ddd4c5; }
      body { margin: 0; font-family: Georgia, 'Iowan Old Style', serif; background: var(--bg); color: var(--ink); }
      main { max-width: 980px; margin: 0 auto; padding: 48px 24px 80px; }
      .hero { background: linear-gradient(135deg, #fffefb, #efe5d2); border: 1px solid var(--line); border-radius: 22px; padding: 30px; }
      .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; margin-top: 22px; }
      .card { background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 20px; }
      a { color: var(--accent); font-weight: 700; }
      code { background: #f1ecdf; padding: 2px 6px; border-radius: 6px; }
      .metric { font-size: 34px; font-weight: 700; margin: 8px 0 0; }
      .muted { color: var(--muted); }
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <p class="muted">DeepResearch Agent packaged demo</p>
        <h1>Robotics Research Delivery Bundle</h1>
        <p>Run ID: <code>$RUN_ID</code></p>
        <p>This page links to the generated reports, structured artifacts, charts, and ZIP delivery bundle.</p>
      </section>
      <section class="grid">
        <article class="card"><p class="muted">Quality Score</p><p class="metric">$QUALITY_SCORE</p></article>
        <article class="card"><p class="muted">Events</p><p class="metric">$EVENT_COUNT</p></article>
        <article class="card"><p class="muted">Entities</p><p class="metric">$ENTITY_COUNT</p></article>
      </section>
      <section class="grid">
        <article class="card"><h2>Deliver</h2><p><a href="delivery_bundle.zip">Download delivery_bundle.zip</a></p><p><a href="quality.json">View quality.json</a></p><p><a href="run.json">View run.json</a></p></article>
        <article class="card"><h2>Reports</h2><p><a href="../$RUN_DIR/research_report.pdf">PDF report</a></p><p><a href="../$RUN_DIR/research_report.html">HTML report</a></p><p><a href="../$RUN_DIR/research_workbook.xlsx">Excel workbook</a></p></article>
        <article class="card"><h2>Charts</h2><p><a href="../$RUN_DIR/source_scores.svg">Source score chart</a></p><p><a href="../$RUN_DIR/event_timeline.svg">Event timeline</a></p></article>
      </section>
    </main>
  </body>
</html>
EOF

echo "run_id=$RUN_ID"
echo "artifacts_dir=$RUN_DIR"
echo "bundle=demo/delivery_bundle.zip"
echo "quality=demo/quality.json"
echo "index=demo/index.html"
