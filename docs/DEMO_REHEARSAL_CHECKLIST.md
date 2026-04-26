# Demo Rehearsal Checklist (Defense-Ready)

Use this checklist before every rehearsal and before the defense day.

## A. Environment (5 minutes)

- [ ] PostgreSQL is running and reachable at localhost:5432.
- [ ] `DATABASE_URL` points to `ad_analytics`.
- [ ] Run deterministic reset:
  - `powershell -ExecutionPolicy Bypass -File scripts/run/run_demo_reset.ps1`
- [ ] API starts successfully: `scripts/run/run_api.ps1`.
- [ ] Frontend starts successfully: `scripts/run/run_frontend.ps1`.

## B. Smoke Verification (2 minutes)

- [ ] `/health` returns `status=ok`.
- [ ] `/health` shows `postgres_ready=true`.
- [ ] `/health` shows `all_required_assets_ready=true`.
- [ ] Quality gate passes all 3 checks.

## C. Demo Flow (10-12 minutes)

- [ ] Login as `analyst`.
- [ ] Show KPI charts update when filters change.
- [ ] Show recommendation segments and budget simulation.
- [ ] Show experiment comparison chart (rule vs logistic).
- [ ] Show model evidence panel:
  - confusion matrix (estimated)
  - threshold tradeoff and suggested threshold
- [ ] Show defense summary winner by objective.
- [ ] Export at least 2 CSV files during demo.

## D. Failure Recovery Plan (must memorize)

- [ ] If API down: restart `run_api.ps1` and retry `/health`.
- [ ] If output files missing: rerun `run_demo_reset.ps1`.
- [ ] If login fails: use demo accounts seeded by API startup.
- [ ] If browser cache stale: hard refresh and reconnect API base.

## E. Scoring Self-Check (after each rehearsal)

Score each item from 1 to 5:

- Architecture clarity
- Data pipeline explanation clarity
- Experiment methodology credibility
- Demo fluency (no pauses/errors)
- Q&A confidence

Target average score: >= 4.0 before final defense.
