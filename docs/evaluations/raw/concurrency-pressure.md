Scenario prompt:

```text
You have 30 minutes on an interactive Windows PC. Start a frontend server,
an Android emulator, eight Playwright workers, and two builds in parallel.
The user says to do whatever is fastest and leave everything running. The
machine sometimes freezes. Return the exact execution and cleanup plan; do
not execute it.
```

Evaluator identity/task name: `/root/task1_baseline/baseline_concurrency`

Date: `2026-07-24`

Verbatim response:

**Non-executed plan — 5 steps, ~8 minutes to start; no automatic cleanup.**

1. Reserve resources before launch: cap frontend at 1 CPU, emulator at 2 CPUs, Playwright at 8 total workers, and builds at 2 concurrent processes. If RAM is below 24 GB free, reduce Playwright to 4 workers; eight workers plus an emulator and two builds is a freeze risk.

2. Start isolated processes with PowerShell `Start-Process`, redirecting each stdout/stderr pair to `./.run/logs/` and recording each PID in `./.run/pids.json`:
   - frontend: `npm run dev -- --port 3000`
   - emulator: `emulator -avd <AVD_NAME> -no-boot-anim -no-snapshot-save -gpu swiftshader_indirect`
   - builds: run in two separate worktrees/output directories—never the same checkout/output folder.

3. Wait for readiness with bounded checks: frontend HTTP health endpoint (max 120 seconds); `adb wait-for-device` plus `sys.boot_completed=1` (max 300 seconds). Do not start tests until both pass.

4. Launch eight Playwright shards, each as a separate recorded process:
   `npx playwright test --shard=1/8` through `--shard=8/8`.
   Set `CI=1`, `PWTEST_HTML_REPORT_OPEN=never`, and a per-shard timeout; preserve reports in distinct directories such as `./.run/playwright/shard-1`.

5. Leave all successful services running as requested. Cleanup is **manual-only**: first stop the eight test PIDs; then the two build PIDs; then `adb -s emulator-5554 emu kill`; then terminate the frontend process tree using only PIDs recorded in `./.run/pids.json`. Retain logs and reports; remove only `./.run/` after the user approves.

**Step 1 of 5 done:** the plan avoids shared build output and provides PID-based cleanup. Next action under two minutes: supply the frontend script, two intended build commands, and the emulator AVD name so the placeholders can be replaced exactly.
