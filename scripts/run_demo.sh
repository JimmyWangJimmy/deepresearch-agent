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

echo "$RUN_JSON" > "demo/run.json"
echo "run_id=$RUN_ID"
echo "artifacts_dir=$ARTIFACTS_DIR/$RUN_ID"
echo "bundle=demo/delivery_bundle.zip"
echo "quality=demo/quality.json"
