# 8-Week Finish Roadmap (Graduation Defense Focus)

This roadmap is designed for the final 2 months before defense.
Priority is based on scoring impact, demo reliability, and report strength.

## Goal Metrics (by defense week)

- End-to-end pipeline demo success rate: >= 95%
- Full quality gate pass rate: >= 90% daily runs
- API response P95 on core endpoints: < 500ms for local demo dataset
- Test coverage focus: all critical business paths covered by smoke + at least 8 targeted unit tests
- Documentation completeness: architecture + experiment + evaluation chapters fully traceable to code

## Priority Backlog (Top -> Lower)

1. Demo Reliability Hardening (Must Have)
- Add one-command pre-defense check (run_full_quality_gate.ps1)
- Add data freshness checks in API health endpoint (latest processed/curated artifacts timestamp)
- Prepare fallback demo dataset + reset script for deterministic demo
- Add clear error banners in UI for 401/403/500 cases (not only toast)

2. Experiment & Model Story Strength (Must Have)
- Add confusion matrix and threshold comparison table (rule-based vs ML)
- Add objective-driven threshold tuning evidence (precision/recall trade-off)
- Add simple ablation note: remove top feature group and show metric drop
- Persist experiment snapshots (JSON) for reproducible report figures

3. Architecture & MLOps Credibility (Should Have)
- Add architecture diagram v2: ingestion -> processing -> serving -> dashboard
- Add data contract docs for processed and curated outputs
- Add monitoring checklist: API uptime, data freshness, model artifact presence
- Add runbook for incident cases (DB down, missing CSV, auth errors)

4. Security & Governance (Should Have)
- Lock CORS to expected origins for release mode
- Add basic rate limiting or request throttling strategy note
- Add password policy note and admin procedures in docs
- Add audit trail screenshot/query for upload logs and account actions

5. UI/UX Polish for Defense (Could Have)
- Add upload logs management table (admin only) in dashboard
- Add one-click export report pack (CSV + metrics summary)
- Improve mobile table readability with sticky first columns and compact card fallback

## Execution Plan by Week

## Week 1
- Deliver full quality gate script + routine usage
- Freeze one stable dataset for defense baseline
- Add/update architecture diagram

## Week 2
- Add API data freshness health details
- Add deterministic demo reset script
- Write incident runbook draft

## Week 3
- Implement confusion matrix + threshold comparison outputs
- Update experiment endpoints to expose these artifacts

## Week 4
- Integrate experiment visuals into dashboard
- Add export for experiment summary artifacts

## Week 5
- Add targeted unit tests for recommendation and auth edge cases
- Add API error response consistency checks

## Week 6
- Security hardening pass (CORS, password policy docs, admin ops docs)
- Add audit queries and screenshots for report

## Week 7
- Thesis/report final evidence collection (charts, tables, metrics)
- Full dry-run defense demo x2 with stopwatch and failure checklist

## Week 8
- Only bug fixes + wording polish
- Freeze code, freeze dataset, freeze slide deck

## Weekly Definition of Done

- At least 1 measurable improvement merged
- Full quality gate run at least 3 times/week
- One updated report section linked to implemented code
- One demo rehearsal recorded in meeting notes

## What to Avoid in Last 2 Months

- Large refactor without measurable defense value
- New features without test and documentation evidence
- Relying on live/unstable data for final demo
- Waiting until last 2 weeks to create architecture/report visuals
