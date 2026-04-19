# Transcripts

This folder contains agent conversation records used to build the AI Companion Narrative Shift Tracker, submitted as a deliverable for Harvard Law School's Debates on Frontier AI Governance (Spring 2026 final project, Option B).

## Files

- **transcript_antigravity.md**: Build sessions in Google's Antigravity IDE. Covers initial codebase construction, data pipeline implementation, debugging and verification cycles, dashboard UI rebuilds, data integrity investigations, and public deployment. Sessions used Claude (Sonnet 4.x) and Gemini 1.5 Flash models interchangeably across the project.

- **transcript_claude.md** (to be added): Strategic consultation with Claude via claude.ai. Covers project scoping, methodology decisions, data source research, pre-build design critiques, verification checkpoints between build cycles, and final paper framing. This transcript was exported separately from Claude's web interface.

## How these transcripts were used

Different tools were used for different layers of the project:

- **Claude on claude.ai**: For design review, research questions, methodology decisions, and strategic direction. Functioned as a human-in-the-loop consultant rather than as a build agent.

- **Antigravity**: For agentic code execution — running scripts, pulling data, editing files, debugging, deploying. Used both Claude and Gemini models depending on the task.

Verification-heavy phases (data reconciliation, spike analysis, pipeline integrity checks) were run in Antigravity with Gemini 1.5 Flash after a switch from earlier Claude sessions. Strategic-design phases were run on claude.ai.

## Reproducibility notes

- All data processing scripts, pre-registered regex patterns, raw corpora, and dashboard source files are in this repository.
- The live dashboard is at: https://quaint-sudo.github.io/ai-companion-tracker/
- Paper: [to be added on submission]
