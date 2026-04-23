# Run 0cbdd9cb4394

## Objective

robotics industry overview

## Plan

- `scope` Scope task: Interpret the natural-language request and derive the execution scope.
- `collect` Collect evidence: Select providers and gather raw sources for the run.
- `process` Process and normalize: Clean, deduplicate, and organize source material into structured findings.
- `deliver` Deliver artifacts: Render report and machine-readable outputs for downstream workflows.

## Findings

- **Agent-native execution model** (high): The product should treat the request as a run with explicit planning, execution state, and exportable artifacts instead of a chat-only interaction.
- **Artifact-first delivery contract** (high): Every run should emit a manifest, report, structured findings, and a source ledger so results can be audited and reused by teams.
- **General workflow fit** (medium): This request does not yet map to a specialized flow. The runtime should fall back to generic planning and then route into collection, processing, and delivery.
- **Task captured** (high): The current run objective is: robotics industry overview
- **Evidence intake** (high): The run ingested 2 source(s) spanning 564 characters of raw content.
- **First-source preview** (medium): Robotics: Robotics is the interdisciplinary study and practice of the design, construction, operation, and use of robots. A roboticist is someone who specializes in robotics. Robotics usually combines four aspects of design work: a power source, mech

## Sources

- `search_result` Robotics: https://en.wikipedia.org/wiki/Robotics
- `search_result` Robotics engineering: https://en.wikipedia.org/wiki/Robotics_engineering

## Structured Outputs

- Entities: `artifacts_provider_demo3/0cbdd9cb4394/entities.json`
- Entities CSV: `artifacts_provider_demo3/0cbdd9cb4394/entities.csv`
- Events: `artifacts_provider_demo3/0cbdd9cb4394/events.json`
- Events CSV: `artifacts_provider_demo3/0cbdd9cb4394/events.csv`
